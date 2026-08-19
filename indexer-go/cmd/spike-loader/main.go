package main

import (
	"encoding/json"
	"flag"
	"fmt"
	"go/ast"
	"go/parser"
	"go/token"
	"go/types"
	"io/fs"
	"os"
	"path/filepath"
	"sort"
	"strings"

	"golang.org/x/tools/go/packages"
)

type Diagnostic struct {
	Package  string `json:"package"`
	Kind     string `json:"kind"`
	Position string `json:"position"`
	Message  string `json:"message"`
}

type PackageSummary struct {
	ID             string   `json:"id"`
	Path           string   `json:"path"`
	Name           string   `json:"name"`
	Files          []string `json:"files"`
	Imports        []string `json:"imports"`
	Functions      int      `json:"functions"`
	Methods        int      `json:"methods"`
	Types          int      `json:"types"`
	Interfaces     int      `json:"interfaces"`
	InterfaceNames []string `json:"interface_names"`
}

type SourceTestInventory struct {
	TestFiles         int `json:"test_files"`
	TestLikeFunctions int `json:"test_like_functions"`
}

type SpikeReport struct {
	Status              string              `json:"status"`
	ModulePath          string              `json:"module_path"`
	Packages            []PackageSummary    `json:"packages"`
	SourceTestInventory SourceTestInventory `json:"source_test_inventory"`
	Diagnostics         []Diagnostic        `json:"diagnostics"`
}

func mapErrorKind(k packages.ErrorKind) string {
	switch k {
	case packages.ListError:
		return "list"
	case packages.ParseError:
		return "parse"
	case packages.TypeError:
		return "type"
	default:
		return "unknown"
	}
}

func normalizePath(p, repoDir string) string {
	if p == "" || p == "-" {
		return p
	}
	var absPath string
	if filepath.IsAbs(p) {
		absPath = p
	} else {
		absPath = filepath.Join(repoDir, p)
	}
	rel, err := filepath.Rel(repoDir, absPath)
	if err != nil || strings.HasPrefix(rel, "..") {
		return filepath.ToSlash(p)
	}
	return filepath.ToSlash(rel)
}

func normalizePosition(posStr, repoDir string) string {
	if posStr == "" || posStr == "-" {
		return posStr
	}
	// Positions are usually path:line:col or path:line
	parts := strings.Split(posStr, ":")
	if len(parts) >= 2 {
		filePath := parts[0]
		lineColStart := 1
		// On Windows, drive letters cause C:\... so check if parts[0] is drive letter
		if len(filePath) == 1 && len(parts) >= 3 && filepath.VolumeName(parts[0]+":"+parts[1]) != "" {
			filePath = parts[0] + ":" + parts[1]
			lineColStart = 2
		}
		normFile := normalizePath(filePath, repoDir)
		remaining := strings.Join(parts[lineColStart:], ":")
		return normFile + ":" + remaining
	}
	return normalizePath(posStr, repoDir)
}

func collectSourceTestInventory(repoDir string) (SourceTestInventory, error) {
	var inv SourceTestInventory
	fset := token.NewFileSet()

	err := filepath.WalkDir(repoDir, func(path string, d fs.DirEntry, err error) error {
		if err != nil {
			return err
		}
		if d.IsDir() {
			name := d.Name()
			if name == ".git" || name == "vendor" || name == "testdata" {
				return filepath.SkipDir
			}
			return nil
		}

		if !strings.HasSuffix(d.Name(), "_test.go") {
			return nil
		}

		inv.TestFiles++

		fileAST, parseErr := parser.ParseFile(fset, path, nil, parser.SkipObjectResolution)
		if parseErr != nil {
			return nil
		}

		for _, decl := range fileAST.Decls {
			funcDecl, ok := decl.(*ast.FuncDecl)
			if !ok || funcDecl.Recv != nil {
				continue
			}
			name := funcDecl.Name.Name
			if strings.HasPrefix(name, "Test") ||
				strings.HasPrefix(name, "Benchmark") ||
				strings.HasPrefix(name, "Example") ||
				strings.HasPrefix(name, "Fuzz") {
				inv.TestLikeFunctions++
			}
		}
		return nil
	})

	return inv, err
}

func main() {
	repoFlag := flag.String("repo", "", "Path to the target Go repository root (required)")
	patternFlag := flag.String("pattern", "./...", "Package pattern to load (default: ./...)")
	flag.Parse()

	if *repoFlag == "" {
		fmt.Fprintln(os.Stderr, "error: -repo flag is required")
		os.Exit(2)
	}

	cleanRepoPath, err := filepath.Abs(filepath.Clean(*repoFlag))
	if err != nil {
		fmt.Fprintf(os.Stderr, "error resolving repo path: %v\n", err)
		os.Exit(2)
	}

	fi, err := os.Stat(cleanRepoPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "error: repo path does not exist: %v\n", err)
		os.Exit(2)
	}
	if !fi.IsDir() {
		fmt.Fprintf(os.Stderr, "error: repo path is not a directory: %s\n", cleanRepoPath)
		os.Exit(2)
	}

	cfg := &packages.Config{
		Mode: packages.LoadSyntax | packages.NeedModule,
		Dir:  cleanRepoPath,
	}

	pkgs, loadErr := packages.Load(cfg, *patternFlag)
	if loadErr != nil {
		fmt.Fprintf(os.Stderr, "error executing packages.Load: %v\n", loadErr)
		os.Exit(1)
	}

	var diagnostics []Diagnostic
	var modulePath string
	isPartial := false

	var pkgSummaries []PackageSummary

	for _, pkg := range pkgs {
		if pkg.Module != nil && modulePath == "" {
			modulePath = pkg.Module.Path
		}

		if pkg.IllTyped {
			isPartial = true
		}

		// Collect package diagnostics
		for _, pkgErr := range pkg.Errors {
			isPartial = true
			diag := Diagnostic{
				Package:  pkg.PkgPath,
				Kind:     mapErrorKind(pkgErr.Kind),
				Position: normalizePosition(pkgErr.Pos, cleanRepoPath),
				Message:  pkgErr.Msg,
			}
			diagnostics = append(diagnostics, diag)
		}

		// Collect compiled files
		var files []string
		sourceFiles := pkg.CompiledGoFiles
		if len(sourceFiles) == 0 {
			sourceFiles = pkg.GoFiles
		}
		for _, f := range sourceFiles {
			files = append(files, normalizePath(f, cleanRepoPath))
		}
		sort.Strings(files)

		// Collect imports
		var imports []string
		for impPath := range pkg.Imports {
			imports = append(imports, impPath)
		}
		sort.Strings(imports)

		// Collect functions, methods, types, interfaces
		functionsCount := 0
		methodsCount := 0
		typesCount := 0
		interfacesCount := 0
		var interfaceNames []string

		for _, file := range pkg.Syntax {
			for _, decl := range file.Decls {
				switch d := decl.(type) {
				case *ast.FuncDecl:
					if d.Recv == nil {
						functionsCount++
					} else {
						methodsCount++
					}
				case *ast.GenDecl:
					if d.Tok == token.TYPE {
						for _, spec := range d.Specs {
							typeSpec, ok := spec.(*ast.TypeSpec)
							if !ok {
								continue
							}
							typesCount++

							isInterface := false
							if pkg.TypesInfo != nil {
								if obj := pkg.TypesInfo.Defs[typeSpec.Name]; obj != nil {
									if obj.Type() != nil {
										if _, ok := obj.Type().Underlying().(*types.Interface); ok {
											isInterface = true
										}
									}
								}
							}

							if isInterface {
								interfacesCount++
								interfaceNames = append(interfaceNames, typeSpec.Name.Name)
							}
						}
					}
				}
			}
		}

		sort.Strings(interfaceNames)
		if interfaceNames == nil {
			interfaceNames = []string{}
		}
		if files == nil {
			files = []string{}
		}
		if imports == nil {
			imports = []string{}
		}

		pkgSummaries = append(pkgSummaries, PackageSummary{
			ID:             pkg.ID,
			Path:           pkg.PkgPath,
			Name:           pkg.Name,
			Files:          files,
			Imports:        imports,
			Functions:      functionsCount,
			Methods:        methodsCount,
			Types:          typesCount,
			Interfaces:     interfacesCount,
			InterfaceNames: interfaceNames,
		})
	}

	// Sort packages deterministically primarily by Path, tie-break by ID
	sort.Slice(pkgSummaries, func(i, j int) bool {
		if pkgSummaries[i].Path != pkgSummaries[j].Path {
			return pkgSummaries[i].Path < pkgSummaries[j].Path
		}
		return pkgSummaries[i].ID < pkgSummaries[j].ID
	})

	// Deduplicate and sort diagnostics deterministically
	diagMap := make(map[string]Diagnostic)
	for _, d := range diagnostics {
		key := fmt.Sprintf("%s|%s|%s|%s", d.Package, d.Kind, d.Position, d.Message)
		diagMap[key] = d
	}
	var dedupDiagnostics []Diagnostic
	for _, d := range diagMap {
		dedupDiagnostics = append(dedupDiagnostics, d)
	}
	sort.Slice(dedupDiagnostics, func(i, j int) bool {
		if dedupDiagnostics[i].Package != dedupDiagnostics[j].Package {
			return dedupDiagnostics[i].Package < dedupDiagnostics[j].Package
		}
		if dedupDiagnostics[i].Kind != dedupDiagnostics[j].Kind {
			return dedupDiagnostics[i].Kind < dedupDiagnostics[j].Kind
		}
		if dedupDiagnostics[i].Position != dedupDiagnostics[j].Position {
			return dedupDiagnostics[i].Position < dedupDiagnostics[j].Position
		}
		return dedupDiagnostics[i].Message < dedupDiagnostics[j].Message
	})
	if dedupDiagnostics == nil {
		dedupDiagnostics = []Diagnostic{}
	}
	if pkgSummaries == nil {
		pkgSummaries = []PackageSummary{}
	}

	// Scan source test inventory
	testInv, err := collectSourceTestInventory(cleanRepoPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "warning: error scanning source test inventory: %v\n", err)
	}

	status := "complete"
	if isPartial || len(dedupDiagnostics) > 0 {
		status = "partial"
	}

	report := SpikeReport{
		Status:              status,
		ModulePath:          modulePath,
		Packages:            pkgSummaries,
		SourceTestInventory: testInv,
		Diagnostics:         dedupDiagnostics,
	}

	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	if err := encoder.Encode(report); err != nil {
		fmt.Fprintf(os.Stderr, "error encoding json output: %v\n", err)
		os.Exit(1)
	}

	if status == "partial" {
		os.Exit(1)
	}
}
