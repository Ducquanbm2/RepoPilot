"""
runner/validators/patch_validator.py
Deterministic Unified Diff Safety Validation
Owner: Person B (Runtime & Platform Lead)
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple


@dataclass(frozen=True)
class ValidationResult:
    is_valid: bool
    error_message: str | None = None
    modified_files: Tuple[str, ...] = ()
    lines_added: int = 0
    lines_removed: int = 0

    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "error_message": self.error_message,
            "modified_files": list(self.modified_files),
            "lines_added": self.lines_added,
            "lines_removed": self.lines_removed,
        }


class PatchValidator:
    """Deterministic validator for unified diff safety.
    
    Safety constraints:
    1. Text diff only (reject binary diffs, reject null bytes).
    2. Block path traversal attacks ('../../', absolute paths).
    3. Enforce budget limits on modified files and changed lines to prevent scope violations.
    """

    def __init__(self, max_files: int = 20, max_lines_changed: int = 1500):
        self.max_files = max_files
        self.max_lines_changed = max_lines_changed

    def validate_content(self, patch_content: str) -> ValidationResult:
        """Validates the text content of a unified diff patch."""
        if not patch_content or not patch_content.strip():
            return ValidationResult(is_valid=False, error_message="Patch content is empty.")

        # 1. Reject null bytes (100% indicator of binary payload in text diff)
        if "\x00" in patch_content:
            return ValidationResult(
                is_valid=False,
                error_message="Rejected: Patch contains null bytes (binary payload)."
            )

        # 2. Reject git binary diff headers
        if "GIT binary patch" in patch_content or "Binary files " in patch_content:
            return ValidationResult(
                is_valid=False,
                error_message="Rejected: Patch contains binary data (Binary Patch)."
            )

        lines = patch_content.splitlines()
        modified_files: list[str] = []
        lines_added = 0
        lines_removed = 0

        for line in lines:
            # 3. Extract file paths from git diff headers
            if line.startswith("diff --git "):
                parts = line.split()
                if len(parts) >= 4:
                    raw_b_path = parts[3]
                    # Strip leading b/ prefix if present
                    target_file = raw_b_path[2:] if raw_b_path.startswith("b/") else raw_b_path

                    # Check for path traversal attacks
                    if ".." in target_file or target_file.startswith("/") or target_file.startswith("\\"):
                        return ValidationResult(
                            is_valid=False,
                            error_message=f"Rejected: Dangerous path traversal detected ({target_file})."
                        )

                    if target_file not in modified_files:
                        modified_files.append(target_file)

            # 4. Count added and removed lines (excluding diff headers)
            elif line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_removed += 1

        total_changed = lines_added + lines_removed

        # 5. Enforce modified files budget
        if len(modified_files) > self.max_files:
            return ValidationResult(
                is_valid=False,
                error_message=f"Exceeded maximum allowed files ({len(modified_files)} > {self.max_files}).",
                modified_files=tuple(modified_files),
                lines_added=lines_added,
                lines_removed=lines_removed,
            )

        # 6. Enforce changed lines budget
        if total_changed > self.max_lines_changed:
            return ValidationResult(
                is_valid=False,
                error_message=f"Exceeded maximum allowed changed lines ({total_changed} > {self.max_lines_changed}).",
                modified_files=tuple(modified_files),
                lines_added=lines_added,
                lines_removed=lines_removed,
            )

        return ValidationResult(
            is_valid=True,
            error_message=None,
            modified_files=tuple(modified_files),
            lines_added=lines_added,
            lines_removed=lines_removed,
        )

    def validate_file(self, patch_path: Path | str) -> ValidationResult:
        """Reads and validates a patch file from disk."""
        path = Path(patch_path)
        if not path.is_file():
            return ValidationResult(is_valid=False, error_message=f"Patch file does not exist: {path}")

        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            return ValidationResult(
                is_valid=False,
                error_message="Patch file is not valid UTF-8 text or contains binary characters."
            )
        except Exception as e:
            return ValidationResult(is_valid=False, error_message=f"Error reading patch file: {str(e)}")

        return self.validate_content(content)
