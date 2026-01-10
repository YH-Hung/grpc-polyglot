package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"
	"strings"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/generator"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/parser"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

func main() {
	var (
		protoPath = flag.String("proto", "", "Path to a single .proto file or a directory containing .proto files")
		outDir    = flag.String("out", "", "Directory where generated .vb files are written")
		pkg       = flag.String("package", "", "Override VB.NET namespace name for generated code (optional)")
		baseURL   = flag.String("baseurl", "", "Base URL for HTTP requests (optional, defaults to empty)")
		framework = flag.String("framework", "net45", "Target .NET Framework mode: net45 (HttpClient+async/await) or net40hwr (HttpWebRequest+sync)")
	)
	flag.Parse()

	if *protoPath == "" || *outDir == "" {
		fmt.Fprintf(os.Stderr, "Usage: %s --proto <path> --out <dir> [--package <name>] [--baseurl <url>] [--framework <mode>]\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "\nArguments:\n")
		fmt.Fprintf(os.Stderr, "  --proto     Path to a single .proto file or directory containing .proto files\n")
		fmt.Fprintf(os.Stderr, "  --out       Directory where generated .vb files are written\n")
		fmt.Fprintf(os.Stderr, "  --package   Override VB.NET namespace name for generated code (optional)\n")
		fmt.Fprintf(os.Stderr, "  --baseurl   Base URL for HTTP requests (optional)\n")
		fmt.Fprintf(os.Stderr, "  --framework Target .NET Framework mode: net45 or net40hwr (default: net45)\n")
		os.Exit(1)
	}

	// Validate framework mode
	if *framework != "net45" && *framework != "net40hwr" {
		fmt.Fprintf(os.Stderr, "Error: --framework must be either 'net45' or 'net40hwr', got: %s\n", *framework)
		os.Exit(1)
	}

	// Ensure output directory exists
	if err := os.MkdirAll(*outDir, 0755); err != nil {
		fmt.Fprintf(os.Stderr, "Error creating output directory: %v\n", err)
		os.Exit(1)
	}

	// Check if protoPath is a file or directory
	info, err := os.Stat(*protoPath)
	if err != nil {
		fmt.Fprintf(os.Stderr, "Error accessing proto path: %v\n", err)
		os.Exit(1)
	}

	var protoFiles []string
	if info.IsDir() {
		// Find all .proto files in directory recursively
		err := filepath.Walk(*protoPath, func(path string, info os.FileInfo, err error) error {
			if err != nil {
				return err
			}
			if filepath.Ext(path) == ".proto" {
				protoFiles = append(protoFiles, path)
			}
			return nil
		})
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error scanning directory: %v\n", err)
			os.Exit(1)
		}
		if len(protoFiles) == 0 {
			fmt.Fprintf(os.Stderr, "No .proto files found in directory: %s\n", *protoPath)
			os.Exit(1)
		}
	} else {
		if filepath.Ext(*protoPath) != ".proto" {
			fmt.Fprintf(os.Stderr, "File must have .proto extension: %s\n", *protoPath)
			os.Exit(1)
		}
		protoFiles = append(protoFiles, *protoPath)
	}

	// Parse all proto files
	var allFiles []*types.ProtoFile
	for _, protoFile := range protoFiles {
		parsedFile, err := parser.ParseProtoFile(protoFile)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Error parsing %s: %v\n", protoFile, err)
			os.Exit(1)
		}
		allFiles = append(allFiles, parsedFile)
	}

	// Group proto files by directory
	filesByDir := make(map[string][]*types.ProtoFile)
	for _, protoFile := range allFiles {
		dir := filepath.Dir(protoFile.FileName)
		filesByDir[dir] = append(filesByDir[dir], protoFile)
	}

	// Generate VB.NET code
	gen := &generator.Generator{
		PackageOverride: *pkg,
		BaseURL:         *baseURL,
		FrameworkMode:   *framework,
	}

	generatedCount := 0

	// For each directory with multiple proto files with services, generate shared utility
	for dir, files := range filesByDir {
		// Count files with services
		filesWithServices := 0
		for _, f := range files {
			if len(f.Services) > 0 {
				filesWithServices++
			}
		}

		if filesWithServices > 1 {
			// Multiple files with services - generate shared utility
			utilityName := deriveUtilityName(dir)
			namespace := determineCommonNamespace(files, gen.PackageOverride)

			utilityPath := filepath.Join(*outDir, utilityName+".vb")
			if err := gen.GenerateSharedUtility(utilityName, namespace, utilityPath); err != nil {
				fmt.Fprintf(os.Stderr, "Error generating shared utility %s: %v\n", utilityPath, err)
				os.Exit(1)
			}
			fmt.Printf("Generated: %s\n", utilityPath)
			generatedCount++

			// Mark files to use shared utility
			for _, f := range files {
				if len(f.Services) > 0 {
					f.UseSharedUtility = true
					f.SharedUtilityName = utilityName
				}
			}
		}
	}

	// Generate individual proto files
	for _, protoFile := range allFiles {
		outputPath := filepath.Join(*outDir, protoFile.BaseName+".vb")
		if err := gen.GenerateFile(protoFile, outputPath); err != nil {
			fmt.Fprintf(os.Stderr, "Error generating %s: %v\n", outputPath, err)
			os.Exit(1)
		}
		fmt.Printf("Generated: %s\n", outputPath)
		generatedCount++
	}

	// Generate JSON schemas for all proto files
	fmt.Println("\nGenerating JSON schemas...")
	generatedSchemas := 0

	for _, protoFile := range allFiles {
		schemaPath, err := generator.GenerateJSONSchema(protoFile, *outDir)
		if err != nil {
			fmt.Fprintf(os.Stderr, "Warning: Failed to generate JSON schema for %s: %v\n",
				protoFile.FileName, err)
			continue
		}
		fmt.Printf("Generated JSON Schema: %s\n", schemaPath)
		generatedSchemas++
	}

	fmt.Printf("\nSuccessfully generated %d VB files and %d JSON schema files from %d proto files\n",
		generatedCount, generatedSchemas, len(protoFiles))
}

// deriveUtilityName derives the shared utility class name from directory path
func deriveUtilityName(dir string) string {
	baseName := filepath.Base(dir)
	// Convert to PascalCase and append HttpUtility
	parts := strings.Split(baseName, "-")
	for i, part := range parts {
		if len(part) > 0 {
			parts[i] = strings.ToUpper(part[:1]) + part[1:]
		}
	}
	return strings.Join(parts, "") + "HttpUtility"
}

// determineCommonNamespace determines the common namespace for shared utility
// Priority: 1) proto package declaration, 2) CLI --package override, 3) directory name
func determineCommonNamespace(files []*types.ProtoFile, packageOverride string) string {
	// Priority 1: Use the package from the first file with a package
	for _, f := range files {
		if f.Package != "" {
			parts := strings.Split(f.Package, ".")
			for i, p := range parts {
				p = strings.ReplaceAll(p, "-", "_")
				parts[i] = strings.ToUpper(p[:1]) + p[1:]
			}
			return strings.Join(parts, ".")
		}
	}

	// Priority 2: Use CLI package override as fallback
	if packageOverride != "" {
		return packageOverride
	}

	// Priority 3: Fallback to directory name
	if len(files) > 0 {
		dir := filepath.Dir(files[0].FileName)
		baseName := filepath.Base(dir)
		name := strings.ReplaceAll(baseName, "-", "_")
		return strings.ToUpper(name[:1]) + name[1:]
	}

	return "Generated"
}