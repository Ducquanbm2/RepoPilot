package main

import (
	"bytes"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/token"
	"go/types"
	"os"
	"os/exec"
	"path/filepath"
	"sort"
	"strconv"
	"strings"

	"golang.org/x/tools/go/packages"
)

type EvidenceRecord struct {
	EvidenceID     string `json:"evidence_id"`
	RepoID         string `json:"repo_id"`
	CommitSHA      string `json:"commit_sha"`
	Path           string `json:"path"`
	StartLine      int    `json:"start_line"`
	EndLine        int    `json:"end_line"`
	SubjectID      string `json:"subject_id"`
	ObjectID       string `json:"object_id"`
	Relation       string `json:"relation"`
	AnalysisMethod string `json:"analysis_method"`
	EvidenceClass  string `json:"evidence_class"`
	ArtifactHash   string `json:"artifact_hash"`
	SchemaVersion  string `json:"schema_version"`
}

type DiagnosticItem struct {
	Stage    string  `json:"stage"`
	Package  *string `json:"package"`
	Path     *string `json:"path"`
	Line     *int    `json:"line"`
	Column   *int    `json:"column"`
	Severity string  `json:"severity"`
	Message  string  `json:"message"`
}

type DiagnosticsEnvelope struct {
	RepoID        string           `json:"repo_id"`
	CommitSHA     string           `json:"commit_sha"`
	Status        string           `json:"status"`
	Diagnostics   []DiagnosticItem `json:"diagnostics"`
	SchemaVersion string           `json:"schema_version"`
}

func countTotalLines(content []byte) int {
	if len(content) == 0 {
		return 0
	}
	lines := bytes.Count(content, []byte{'\n'})
	if content[len(content)-1] != '\n' {
		lines++
	}
	return lines
}

func normalizeRepoPath(absPath, repoDir string) (string, error) {
	rel, err := filepath.Rel(repoDir, absPath)
	if err != nil || strings.HasPrefix(rel, "..") {
		return "", fmt.Errorf("path %s is not within repo %s: %w", absPath, repoDir, err)
	}
	slash := filepath.ToSlash(rel)
	if strings.HasPrefix(slash, "./") {
		slash = slash[2:]
	}
	return slash, nil
}

func computeArtifactHash(content []byte) string {
	sum := sha256.Sum256(content)
	return "sha256:" + hex.EncodeToString(sum[:])
}

func computeEvidenceID(repoID, commitSHA, relation, subjectID, objectID, path string, startLine, endLine int) string {
	core := fmt.Sprintf("%s\n%s\n%s\n%s\n%s\n%s\n%d\n%d",
		repoID, commitSHA, relation, subjectID, objectID, path, startLine, endLine)
	sum := sha256.Sum256([]byte(core))
	return "ev_" + hex.EncodeToString(sum[:])
}

func mapStage(k packages.ErrorKind) string {
	switch k {
	case packages.ListError:
		return "load"
	case packages.ParseError:
		return "parse"
	case packages.TypeError:
		return "typecheck"
	default:
		return "analysis"
	}
}

func parsePositionString(posStr, repoDir string) (*string, *int, *int) {
	if posStr == "" || posStr == "-" {
		return nil, nil, nil
	}
	parts := strings.Split(posStr, ":")
	if len(parts) >= 2 {
		filePath := parts[0]
		lineIdx := 1
		if len(filePath) == 1 && len(parts) >= 3 && filepath.VolumeName(parts[0]+":"+parts[1]) != "" {
			filePath = parts[0] + ":" + parts[1]
			lineIdx = 2
		}
		var relPath *string
		if filepath.IsAbs(filePath) {
			rel, err := filepath.Rel(repoDir, filePath)
			if err == nil && !strings.HasPrefix(rel, "..") {
				norm := filepath.ToSlash(rel)
				relPath = &norm
			} else {
				norm := filepath.ToSlash(filePath)
				relPath = &norm
			}
		} else {
			clean := filepath.ToSlash(filepath.Clean(filePath))
			relPath = &clean
		}

		var lineNum *int
		var colNum *int
		if len(parts) > lineIdx {
			if l, err := strconv.Atoi(parts[lineIdx]); err == nil {
				lineNum = &l
			}
		}
		if len(parts) > lineIdx+1 {
			if c, err := strconv.Atoi(parts[lineIdx+1]); err == nil {
				colNum = &c
			}
		}
		return relPath, lineNum, colNum
	}
	clean := filepath.ToSlash(filepath.Clean(posStr))
	return &clean, nil, nil
}

func resolveReceiverBaseName(expr ast.Expr) string {
	switch t := expr.(type) {
	case *ast.Ident:
		return t.Name
	case *ast.StarExpr:
		return resolveReceiverBaseName(t.X)
	case *ast.IndexExpr:
		return resolveReceiverBaseName(t.X)
	case *ast.IndexListExpr:
		return resolveReceiverBaseName(t.X)
	case *ast.ParenExpr:
		return resolveReceiverBaseName(t.X)
	default:
		return ""
	}
}

func writeDiagnosticsAndExit(diagPath string, env DiagnosticsEnvelope, exitCode int) {
	if diagPath != "" {
		if err := os.MkdirAll(filepath.Dir(diagPath), 0755); err == nil {
			if f, err := os.Create(diagPath); err == nil {
				enc := json.NewEncoder(f)
				enc.SetIndent("", "  ")
				_ = enc.Encode(env)
				_ = f.Close()
			}
		}
	}
	os.Exit(exitCode)
}

func main() {
	repoFlag := flag.String("repo", "", "Path to target Go repository root (required)")
	repoIDFlag := flag.String("repo-id", "", "Canonical repository identity, e.g. uber-go/zap (required)")
	commitFlag := flag.String("commit", "", "Full expected commit SHA (required)")
	diagOutFlag := flag.String("diag-out", "", "Output file path for diagnostics envelope JSON (required)")
	patternFlag := flag.String("pattern", "./...", "Package pattern to load (default: ./...)")
	flag.Parse()

	if *repoFlag == "" || *repoIDFlag == "" || *commitFlag == "" || *diagOutFlag == "" {
		fmt.Fprintln(os.Stderr, "error: -repo, -repo-id, -commit, and -diag-out flags are all required")
		os.Exit(2)
	}

	cleanRepoPath, err := filepath.Abs(filepath.Clean(*repoFlag))
	if err != nil {
		fmt.Fprintf(os.Stderr, "error resolving repo path: %v\n", err)
		os.Exit(2)
	}

	fi, err := os.Stat(cleanRepoPath)
	if err != nil || !fi.IsDir() {
		fmt.Fprintf(os.Stderr, "error: repo path does not exist or is not a directory: %s\n", cleanRepoPath)
		os.Exit(2)
	}

	// 1. Commit provenance enforcement (fail closed)
	gitCheck := exec.Command("git", "-C", cleanRepoPath, "rev-parse", "--is-inside-work-tree")
	if out, err := gitCheck.CombinedOutput(); err != nil || strings.TrimSpace(string(out)) != "true" {
		diag := DiagnosticItem{
			Stage:    "load",
			Severity: "error",
			Message:  fmt.Sprintf("target directory is not a git work tree: %s", cleanRepoPath),
		}
		env := DiagnosticsEnvelope{
			RepoID:        *repoIDFlag,
			CommitSHA:     *commitFlag,
			Status:        "failed",
			Diagnostics:   []DiagnosticItem{diag},
			SchemaVersion: "0.1-draft",
		}
		writeDiagnosticsAndExit(*diagOutFlag, env, 2)
	}

	gitStatus := exec.Command("git", "-C", cleanRepoPath, "status", "--porcelain")
	if out, err := gitStatus.CombinedOutput(); err != nil || len(strings.TrimSpace(string(out))) > 0 {
		diag := DiagnosticItem{
			Stage:    "load",
			Severity: "error",
			Message:  fmt.Sprintf("git work tree is not clean: %s", strings.TrimSpace(string(out))),
		}
		env := DiagnosticsEnvelope{
			RepoID:        *repoIDFlag,
			CommitSHA:     *commitFlag,
			Status:        "failed",
			Diagnostics:   []DiagnosticItem{diag},
			SchemaVersion: "0.1-draft",
		}
		writeDiagnosticsAndExit(*diagOutFlag, env, 2)
	}

	gitHead := exec.Command("git", "-C", cleanRepoPath, "rev-parse", "HEAD")
	headOut, err := gitHead.CombinedOutput()
	if err != nil {
		diag := DiagnosticItem{
			Stage:    "load",
			Severity: "error",
			Message:  fmt.Sprintf("failed to resolve HEAD commit: %v", err),
		}
		env := DiagnosticsEnvelope{
			RepoID:        *repoIDFlag,
			CommitSHA:     *commitFlag,
			Status:        "failed",
			Diagnostics:   []DiagnosticItem{diag},
			SchemaVersion: "0.1-draft",
		}
		writeDiagnosticsAndExit(*diagOutFlag, env, 2)
	}

	resolvedHead := strings.TrimSpace(string(headOut))
	if resolvedHead != *commitFlag {
		diag := DiagnosticItem{
			Stage:    "load",
			Severity: "error",
			Message:  fmt.Sprintf("commit SHA mismatch: expected %s, found HEAD %s", *commitFlag, resolvedHead),
		}
		env := DiagnosticsEnvelope{
			RepoID:        *repoIDFlag,
			CommitSHA:     *commitFlag,
			Status:        "failed",
			Diagnostics:   []DiagnosticItem{diag},
			SchemaVersion: "0.1-draft",
		}
		writeDiagnosticsAndExit(*diagOutFlag, env, 2)
	}

	// 2. Load packages using go/packages
	cfg := &packages.Config{
		Mode:  packages.LoadSyntax | packages.NeedModule,
		Dir:   cleanRepoPath,
		Tests: false,
	}

	pkgs, loadErr := packages.Load(cfg, *patternFlag)
	if loadErr != nil {
		diag := DiagnosticItem{
			Stage:    "load",
			Severity: "error",
			Message:  fmt.Sprintf("packages.Load top-level failure: %v", loadErr),
		}
		env := DiagnosticsEnvelope{
			RepoID:        *repoIDFlag,
			CommitSHA:     *commitFlag,
			Status:        "failed",
			Diagnostics:   []DiagnosticItem{diag},
			SchemaVersion: "0.1-draft",
		}
		writeDiagnosticsAndExit(*diagOutFlag, env, 2)
	}

	var diagnostics []DiagnosticItem
	isPartial := false

	// File caches
	fileLinesCache := make(map[string]int)
	fileHashCache := make(map[string]string)

	readFileMetadata := func(relPath string) (int, string, error) {
		if lines, ok := fileLinesCache[relPath]; ok {
			return lines, fileHashCache[relPath], nil
		}
		abs := filepath.Join(cleanRepoPath, filepath.FromSlash(relPath))
		content, err := os.ReadFile(abs)
		if err != nil {
			return 0, "", err
		}
		lines := countTotalLines(content)
		hash := computeArtifactHash(content)
		fileLinesCache[relPath] = lines
		fileHashCache[relPath] = hash
		return lines, hash, nil
	}

	var records []EvidenceRecord

	// Collect diagnostics from packages
	for _, pkg := range pkgs {
		if pkg.IllTyped {
			isPartial = true
		}
		for _, pkgErr := range pkg.Errors {
			isPartial = true
			stage := mapStage(pkgErr.Kind)
			posPath, line, col := parsePositionString(pkgErr.Pos, cleanRepoPath)
			pkgPath := pkg.PkgPath
			diag := DiagnosticItem{
				Stage:    stage,
				Package:  &pkgPath,
				Path:     posPath,
				Line:     line,
				Column:   col,
				Severity: "error",
				Message:  pkgErr.Msg,
			}
			diagnostics = append(diagnostics, diag)
		}
	}

	// Extract evidence records for initial packages
	for _, pkg := range pkgs {
		if len(pkg.CompiledGoFiles) == 0 && len(pkg.Syntax) == 0 {
			continue
		}

		packageID := fmt.Sprintf("package:%s@%s:%s", *repoIDFlag, *commitFlag, pkg.PkgPath)

		// Pair syntax with relative file paths
		type FileSyntax struct {
			relPath string
			file    *ast.File
		}
		var fileSyntaxes []FileSyntax

		for i, f := range pkg.Syntax {
			var absPath string
			if i < len(pkg.CompiledGoFiles) {
				absPath = pkg.CompiledGoFiles[i]
			} else if i < len(pkg.GoFiles) {
				absPath = pkg.GoFiles[i]
			} else {
				continue
			}

			relPath, err := normalizeRepoPath(absPath, cleanRepoPath)
			if err != nil {
				isPartial = true
				pkgPath := pkg.PkgPath
				diagnostics = append(diagnostics, DiagnosticItem{
					Stage:    "analysis",
					Package:  &pkgPath,
					Severity: "error",
					Message:  fmt.Sprintf("failed to normalize file path: %v", err),
				})
				continue
			}

			// Exclude _test.go files
			if strings.HasSuffix(relPath, "_test.go") {
				continue
			}

			fileSyntaxes = append(fileSyntaxes, FileSyntax{relPath: relPath, file: f})
		}

		// Sort syntax files lexicographically by relative path for deterministic init ordering
		sort.Slice(fileSyntaxes, func(i, j int) bool {
			return fileSyntaxes[i].relPath < fileSyntaxes[j].relPath
		})

		initOrdinal := 0

		for _, fs := range fileSyntaxes {
			relPath := fs.relPath
			astFile := fs.file

			totalLines, artHash, err := readFileMetadata(relPath)
			if err != nil {
				isPartial = true
				pkgPath := pkg.PkgPath
				diagnostics = append(diagnostics, DiagnosticItem{
					Stage:    "analysis",
					Package:  &pkgPath,
					Path:     &relPath,
					Severity: "error",
					Message:  fmt.Sprintf("failed to read file %s: %v", relPath, err),
				})
				continue
			}

			fileID := fmt.Sprintf("file:%s@%s:%s", *repoIDFlag, *commitFlag, relPath)

			// 1. IMPORTS
			for _, imp := range astFile.Imports {
				if imp.Path == nil {
					continue
				}
				importPathVal, err := strconv.Unquote(imp.Path.Value)
				if err != nil {
					importPathVal = strings.Trim(imp.Path.Value, `"`)
				}

				startLine := pkg.Fset.Position(imp.Pos()).Line
				endLine := pkg.Fset.Position(imp.End() - 1).Line
				if endLine < startLine {
					endLine = startLine
				}

				if startLine < 1 || endLine < startLine || endLine > totalLines {
					isPartial = true
					pkgPath := pkg.PkgPath
					diagnostics = append(diagnostics, DiagnosticItem{
						Stage:    "analysis",
						Package:  &pkgPath,
						Path:     &relPath,
						Line:     &startLine,
						Severity: "error",
						Message:  fmt.Sprintf("invalid import source range [%d, %d] in file %s (total lines: %d)", startLine, endLine, relPath, totalLines),
					})
					continue
				}

				importedPkgID := fmt.Sprintf("package:%s", importPathVal)
				evID := computeEvidenceID(*repoIDFlag, *commitFlag, "IMPORTS", packageID, importedPkgID, relPath, startLine, endLine)

				records = append(records, EvidenceRecord{
					EvidenceID:     evID,
					RepoID:         *repoIDFlag,
					CommitSHA:      *commitFlag,
					Path:           relPath,
					StartLine:      startLine,
					EndLine:        endLine,
					SubjectID:      packageID,
					ObjectID:       importedPkgID,
					Relation:       "IMPORTS",
					AnalysisMethod: "go.types",
					EvidenceClass:  "EXACT_STATIC",
					ArtifactHash:   artHash,
					SchemaVersion:  "0.1-draft",
				})
			}

			// 2. Symbols (DECLARES + DEFINED_IN)
			for _, decl := range astFile.Decls {
				switch d := decl.(type) {
				case *ast.FuncDecl:
					startLine := pkg.Fset.Position(d.Pos()).Line
					endLine := pkg.Fset.Position(d.End() - 1).Line
					if endLine < startLine {
						endLine = startLine
					}

					if startLine < 1 || endLine < startLine || endLine > totalLines {
						isPartial = true
						pkgPath := pkg.PkgPath
						diagnostics = append(diagnostics, DiagnosticItem{
							Stage:    "analysis",
							Package:  &pkgPath,
							Path:     &relPath,
							Line:     &startLine,
							Severity: "error",
							Message:  fmt.Sprintf("invalid func source range [%d, %d] in file %s (total lines: %d)", startLine, endLine, relPath, totalLines),
						})
						continue
					}

					var symbolID string
					if d.Recv == nil {
						funcName := d.Name.Name
						if funcName == "init" {
							funcName = fmt.Sprintf("init#%d", initOrdinal)
							initOrdinal++
						}
						symbolID = fmt.Sprintf("symbol:%s@%s/%s/function/%s", *repoIDFlag, *commitFlag, pkg.PkgPath, funcName)
					} else {
						if len(d.Recv.List) == 0 {
							continue
						}
						owner := resolveReceiverBaseName(d.Recv.List[0].Type)
						if owner == "" {
							isPartial = true
							pkgPath := pkg.PkgPath
							diagnostics = append(diagnostics, DiagnosticItem{
								Stage:    "analysis",
								Package:  &pkgPath,
								Path:     &relPath,
								Line:     &startLine,
								Severity: "error",
								Message:  fmt.Sprintf("cannot resolve receiver base name for method %s", d.Name.Name),
							})
							continue
						}
						symbolID = fmt.Sprintf("symbol:%s@%s/%s/method/%s.%s", *repoIDFlag, *commitFlag, pkg.PkgPath, owner, d.Name.Name)
					}

					declEvID := computeEvidenceID(*repoIDFlag, *commitFlag, "DECLARES", packageID, symbolID, relPath, startLine, endLine)
					records = append(records, EvidenceRecord{
						EvidenceID:     declEvID,
						RepoID:         *repoIDFlag,
						CommitSHA:      *commitFlag,
						Path:           relPath,
						StartLine:      startLine,
						EndLine:        endLine,
						SubjectID:      packageID,
						ObjectID:       symbolID,
						Relation:       "DECLARES",
						AnalysisMethod: "go.types",
						EvidenceClass:  "EXACT_STATIC",
						ArtifactHash:   artHash,
						SchemaVersion:  "0.1-draft",
					})

					defEvID := computeEvidenceID(*repoIDFlag, *commitFlag, "DEFINED_IN", symbolID, fileID, relPath, startLine, endLine)
					records = append(records, EvidenceRecord{
						EvidenceID:     defEvID,
						RepoID:         *repoIDFlag,
						CommitSHA:      *commitFlag,
						Path:           relPath,
						StartLine:      startLine,
						EndLine:        endLine,
						SubjectID:      symbolID,
						ObjectID:       fileID,
						Relation:       "DEFINED_IN",
						AnalysisMethod: "go.types",
						EvidenceClass:  "EXACT_STATIC",
						ArtifactHash:   artHash,
						SchemaVersion:  "0.1-draft",
					})

				case *ast.GenDecl:
					if d.Tok == token.TYPE {
						for _, spec := range d.Specs {
							typeSpec, ok := spec.(*ast.TypeSpec)
							if !ok {
								continue
							}

							startLine := pkg.Fset.Position(typeSpec.Pos()).Line
							endLine := pkg.Fset.Position(typeSpec.End() - 1).Line
							if endLine < startLine {
								endLine = startLine
							}

							if startLine < 1 || endLine < startLine || endLine > totalLines {
								isPartial = true
								pkgPath := pkg.PkgPath
								diagnostics = append(diagnostics, DiagnosticItem{
									Stage:    "analysis",
									Package:  &pkgPath,
									Path:     &relPath,
									Line:     &startLine,
									Severity: "error",
									Message:  fmt.Sprintf("invalid type source range [%d, %d] in file %s (total lines: %d)", startLine, endLine, relPath, totalLines),
								})
								continue
							}

							var kind string
							if pkg.TypesInfo != nil {
								if obj := pkg.TypesInfo.Defs[typeSpec.Name]; obj != nil && obj.Type() != nil {
									if _, isIface := obj.Type().Underlying().(*types.Interface); isIface {
										kind = "interface"
									} else {
										kind = "type"
									}
								}
							}

							if kind == "" {
								isPartial = true
								pkgPath := pkg.PkgPath
								diagnostics = append(diagnostics, DiagnosticItem{
									Stage:    "typecheck",
									Package:  &pkgPath,
									Path:     &relPath,
									Line:     &startLine,
									Severity: "error",
									Message:  fmt.Sprintf("missing types object for type %s", typeSpec.Name.Name),
								})
								continue
							}

							symbolID := fmt.Sprintf("symbol:%s@%s/%s/%s/%s", *repoIDFlag, *commitFlag, pkg.PkgPath, kind, typeSpec.Name.Name)

							declEvID := computeEvidenceID(*repoIDFlag, *commitFlag, "DECLARES", packageID, symbolID, relPath, startLine, endLine)
							records = append(records, EvidenceRecord{
								EvidenceID:     declEvID,
								RepoID:         *repoIDFlag,
								CommitSHA:      *commitFlag,
								Path:           relPath,
								StartLine:      startLine,
								EndLine:        endLine,
								SubjectID:      packageID,
								ObjectID:       symbolID,
								Relation:       "DECLARES",
								AnalysisMethod: "go.types",
								EvidenceClass:  "EXACT_STATIC",
								ArtifactHash:   artHash,
								SchemaVersion:  "0.1-draft",
							})

							defEvID := computeEvidenceID(*repoIDFlag, *commitFlag, "DEFINED_IN", symbolID, fileID, relPath, startLine, endLine)
							records = append(records, EvidenceRecord{
								EvidenceID:     defEvID,
								RepoID:         *repoIDFlag,
								CommitSHA:      *commitFlag,
								Path:           relPath,
								StartLine:      startLine,
								EndLine:        endLine,
								SubjectID:      symbolID,
								ObjectID:       fileID,
								Relation:       "DEFINED_IN",
								AnalysisMethod: "go.types",
								EvidenceClass:  "EXACT_STATIC",
								ArtifactHash:   artHash,
								SchemaVersion:  "0.1-draft",
							})
						}
					}
				}
			}
		}
	}

	// Deduplicate diagnostics
	diagMap := make(map[string]DiagnosticItem)
	for _, d := range diagnostics {
		pkgStr := ""
		if d.Package != nil {
			pkgStr = *d.Package
		}
		pathStr := ""
		if d.Path != nil {
			pathStr = *d.Path
		}
		lineNum := -1
		if d.Line != nil {
			lineNum = *d.Line
		}
		colNum := -1
		if d.Column != nil {
			colNum = *d.Column
		}
		key := fmt.Sprintf("%s|%s|%s|%d|%d|%s|%s", d.Stage, pkgStr, pathStr, lineNum, colNum, d.Severity, d.Message)
		diagMap[key] = d
	}

	var dedupDiagnostics []DiagnosticItem
	for _, d := range diagMap {
		dedupDiagnostics = append(dedupDiagnostics, d)
	}

	sort.Slice(dedupDiagnostics, func(i, j int) bool {
		d1, d2 := dedupDiagnostics[i], dedupDiagnostics[j]
		if d1.Stage != d2.Stage {
			return d1.Stage < d2.Stage
		}
		p1, p2 := "", ""
		if d1.Package != nil {
			p1 = *d1.Package
		}
		if d2.Package != nil {
			p2 = *d2.Package
		}
		if p1 != p2 {
			return p1 < p2
		}
		path1, path2 := "", ""
		if d1.Path != nil {
			path1 = *d1.Path
		}
		if d2.Path != nil {
			path2 = *d2.Path
		}
		if path1 != path2 {
			return path1 < path2
		}
		l1, l2 := -1, -1
		if d1.Line != nil {
			l1 = *d1.Line
		}
		if d2.Line != nil {
			l2 = *d2.Line
		}
		if l1 != l2 {
			return l1 < l2
		}
		c1, c2 := -1, -1
		if d1.Column != nil {
			c1 = *d1.Column
		}
		if d2.Column != nil {
			c2 = *d2.Column
		}
		if c1 != c2 {
			return c1 < c2
		}
		return d1.Message < d2.Message
	})

	if dedupDiagnostics == nil {
		dedupDiagnostics = []DiagnosticItem{}
	}

	status := "complete"
	exitCode := 0
	if isPartial || len(dedupDiagnostics) > 0 {
		status = "partial"
		exitCode = 1
	}

	envelope := DiagnosticsEnvelope{
		RepoID:        *repoIDFlag,
		CommitSHA:     *commitFlag,
		Status:        status,
		Diagnostics:   dedupDiagnostics,
		SchemaVersion: "0.1-draft",
	}

	// Serialize records to single-line JSON strings
	var jsonLines []string
	for _, rec := range records {
		b, err := json.Marshal(rec)
		if err != nil {
			fmt.Fprintf(os.Stderr, "error encoding record: %v\n", err)
			continue
		}
		jsonLines = append(jsonLines, string(b))
	}

	// Sort records byte-lexicographically for determinism
	sort.Strings(jsonLines)

	for _, line := range jsonLines {
		fmt.Println(line)
	}

	writeDiagnosticsAndExit(*diagOutFlag, envelope, exitCode)
}
