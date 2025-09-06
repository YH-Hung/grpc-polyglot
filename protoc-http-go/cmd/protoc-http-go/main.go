package main

import (
	"flag"
	"fmt"
	"os"
	"path/filepath"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/generator"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/parser"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

func main() {
	var (
		protoPath = flag.String("proto", "", "Path to a single .proto file or a directory containing .proto files")
		outDir    = flag.String("out", "", "Directory where generated .go files are written")
		pkg       = flag.String("package", "", "Override Go package name for generated code (optional)")
		baseURL   = flag.String("baseurl", "", "Base URL for HTTP requests (optional, defaults to empty)")
	)
	flag.Parse()

	if *protoPath == "" || *outDir == "" {
		fmt.Fprintf(os.Stderr, "Usage: %s --proto <path> --out <dir> [--package <name>] [--baseurl <url>]\n", os.Args[0])
		fmt.Fprintf(os.Stderr, "\nArguments:\n")
		fmt.Fprintf(os.Stderr, "  --proto     Path to a single .proto file or directory containing .proto files\n")
		fmt.Fprintf(os.Stderr, "  --out       Directory where generated .go files are written\n")
		fmt.Fprintf(os.Stderr, "  --package   Override Go package name for generated code (optional)\n")
		fmt.Fprintf(os.Stderr, "  --baseurl   Base URL for HTTP requests (optional)\n")
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

	// Generate Go code for all files
	gen := &generator.Generator{
		PackageOverride: *pkg,
		BaseURL:         *baseURL,
	}

	for _, protoFile := range allFiles {
		outputPath := filepath.Join(*outDir, protoFile.BaseName+".go")
		if err := gen.GenerateFile(protoFile, outputPath); err != nil {
			fmt.Fprintf(os.Stderr, "Error generating %s: %v\n", outputPath, err)
			os.Exit(1)
		}
		fmt.Printf("Generated: %s\n", outputPath)
	}

	fmt.Printf("Successfully generated %d Go files from %d proto files\n", len(allFiles), len(protoFiles))
}