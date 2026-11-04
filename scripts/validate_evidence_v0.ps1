[CmdletBinding()]
param (
    [Parameter(Mandatory = $true)]
    [string]$JsonlPath,

    [Parameter(Mandatory = $true)]
    [string]$RepoRoot
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $JsonlPath)) {
    Write-Error "JSONL file not found: $JsonlPath"
}
if (-not (Test-Path $RepoRoot)) {
    Write-Error "Repo root directory not found: $RepoRoot"
}

$repoRootClean = [System.IO.Path]::GetFullPath($RepoRoot)

$lines = Get-Content $JsonlPath
$totalRecords = $lines.Count
Write-Host "Validating $totalRecords records from $JsonlPath against $repoRootClean..."

$evIdRegex = '^ev_[a-f0-9]{64}$'
$commitShaRegex = '^[a-f0-9]{40}$'
$allowedRelations = @('DECLARES', 'DEFINED_IN', 'IMPORTS')

$seenEvidenceIDs = [System.Collections.Generic.HashSet[string]]::new()
$expectedCommitSHA = $null
$fileCache = @{} # path -> @{ totalLines = int; hash = string }

$recordIndex = 0
$errors = [System.Collections.Generic.List[string]]::new()

function Get-FileMeta($relPath) {
    if ($fileCache.ContainsKey($relPath)) {
        return $fileCache[$relPath]
    }
    $abs = [System.IO.Path]::Combine($repoRootClean, $relPath.Replace('/', [System.IO.Path]::DirectorySeparatorChar))
    if (-not (Test-Path $abs)) {
        return $null
    }
    $bytes = [System.IO.File]::ReadAllBytes($abs)
    
    # Compute total lines
    $lineCount = 0
    if ($bytes.Length -gt 0) {
        for ($i = 0; $i -lt $bytes.Length; $i++) {
            if ($bytes[$i] -eq 10) { # '\n'
                $lineCount++
            }
        }
        if ($bytes[$bytes.Length - 1] -ne 10) {
            $lineCount++
        }
    }
    
    # Compute SHA-256
    $sha256 = [System.Security.Cryptography.SHA256]::Create()
    $hashBytes = $sha256.ComputeHash($bytes)
    $hashHex = "sha256:" + ([System.BitConverter]::ToString($hashBytes).Replace('-', '').ToLowerInvariant())
    
    $meta = @{
        totalLines = $lineCount
        hash = $hashHex
    }
    $fileCache[$relPath] = $meta
    return $meta
}

foreach ($rawLine in $lines) {
    $recordIndex++
    if ([string]::IsNullOrWhiteSpace($rawLine)) {
        continue
    }

    try {
        $rec = $rawLine | ConvertFrom-Json
    } catch {
        $errors.Add("Line ${recordIndex} - Failed to parse JSON: $_")
        continue
    }

    # 1. Required fields presence
    $reqFields = @('evidence_id', 'repo_id', 'commit_sha', 'path', 'start_line', 'end_line', 'subject_id', 'object_id', 'relation', 'analysis_method', 'evidence_class', 'artifact_hash', 'schema_version')
    foreach ($f in $reqFields) {
        if ($null -eq $rec.$f -or ($rec.$f -is [string] -and [string]::IsNullOrWhiteSpace($rec.$f))) {
            $errors.Add("Line ${recordIndex} - Missing required field '$f'")
        }
    }

    # 2. evidence_id format and uniqueness
    if ($rec.evidence_id -notmatch $evIdRegex) {
        $errors.Add("Line ${recordIndex} - Invalid evidence_id format: '$($rec.evidence_id)'")
    }
    if ($seenEvidenceIDs.Contains($rec.evidence_id)) {
        $errors.Add("Line ${recordIndex} - Duplicate evidence_id: '$($rec.evidence_id)'")
    } else {
        $seenEvidenceIDs.Add($rec.evidence_id) | Out-Null
    }

    # 3. commit_sha validation
    if ($rec.commit_sha -notmatch $commitShaRegex) {
        $errors.Add("Line ${recordIndex} - Invalid commit_sha format: '$($rec.commit_sha)'")
    }
    if ($null -eq $expectedCommitSHA) {
        $expectedCommitSHA = $rec.commit_sha
    } elseif ($rec.commit_sha -ne $expectedCommitSHA) {
        $errors.Add("Line ${recordIndex} - Inconsistent commit_sha: '$($rec.commit_sha)' != '$expectedCommitSHA'")
    }

    # 4. path normalization & test file exclusion
    if ($rec.path.Contains('\') -or $rec.path.StartsWith('./') -or $rec.path.StartsWith('/') -or $rec.path.Contains('..') -or $rec.path -match '^[a-zA-Z]:') {
        $errors.Add("Line ${recordIndex} - Unnormalized path: '$($rec.path)'")
    }
    if ($rec.path.EndsWith('_test.go')) {
        $errors.Add("Line ${recordIndex} - Test file contamination: '$($rec.path)'")
    }

    # 5. Coordinate checks against recomputed file metadata
    $fileMeta = Get-FileMeta $rec.path
    if ($null -eq $fileMeta) {
        $errors.Add("Line ${recordIndex} - Cited path does not exist in repo: '$($rec.path)'")
    } else {
        if ($rec.start_line -lt 1) {
            $errors.Add("Line ${recordIndex} - start_line < 1 ($($rec.start_line))")
        }
        if ($rec.end_line -lt $rec.start_line) {
            $errors.Add("Line ${recordIndex} - end_line < start_line ($($rec.end_line) < $($rec.start_line))")
        }
        if ($rec.end_line -gt $fileMeta.totalLines) {
            $errors.Add("Line ${recordIndex} - end_line exceeds total lines ($($rec.end_line) > $($fileMeta.totalLines)) for '$($rec.path)'")
        }
        if ($rec.artifact_hash -ne $fileMeta.hash) {
            $errors.Add("Line ${recordIndex} - artifact_hash mismatch for '$($rec.path)': '$($rec.artifact_hash)' != '$($fileMeta.hash)'")
        }
    }

    # 6. Enum & constant invariants
    if ($allowedRelations -notcontains $rec.relation) {
        $errors.Add("Line ${recordIndex} - Unknown relation: '$($rec.relation)'")
    }
    if ($rec.evidence_class -ne 'EXACT_STATIC') {
        $errors.Add("Line ${recordIndex} - Invalid evidence_class: '$($rec.evidence_class)' (expected EXACT_STATIC)")
    }
    if ($rec.analysis_method -ne 'go.types') {
        $errors.Add("Line ${recordIndex} - Invalid analysis_method: '$($rec.analysis_method)' (expected go.types)")
    }
    if ($rec.schema_version -ne '0.1-draft') {
        $errors.Add("Line ${recordIndex} - Invalid schema_version: '$($rec.schema_version)' (expected 0.1-draft)")
    }
}

if ($errors.Count -gt 0) {
    Write-Host "FAILED: $($errors.Count) validation errors found!" -ForegroundColor Red
    $errors | Select-Object -First 20 | ForEach-Object { Write-Host " - $_" -ForegroundColor Red }
    if ($errors.Count -gt 20) {
        Write-Host " ... and $($errors.Count - 20) more errors" -ForegroundColor Red
    }
    exit 1
}

Write-Host "SUCCESS: All $totalRecords records passed validation cleanly!" -ForegroundColor Green
Write-Host "Unique Evidence IDs: $($seenEvidenceIDs.Count)"
Write-Host "Distinct Files Validated: $($fileCache.Count)"
Write-Host "Commit SHA Verified: $expectedCommitSHA"
