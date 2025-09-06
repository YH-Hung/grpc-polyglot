.PHONY: build test clean install generate-simple generate-complex

# Build the binary
build:
	go build -o protoc-http-go cmd/protoc-http-go/main.go

# Install dependencies
install:
	go mod tidy

# Test the tool
test: build
	@echo "Testing simple proto generation..."
	./protoc-http-go --proto proto/simple/helloworld.proto --out test_output_simple_makefile
	@echo "Testing complex proto generation..."
	./protoc-http-go --proto proto/complex --out test_output_complex_makefile
	@echo "Running compilation test..."
	go run test_compilation.go
	@echo "✅ All tests passed!"

# Generate examples
generate-simple: build
	./protoc-http-go --proto proto/simple --out generated/simple

generate-complex: build
	./protoc-http-go --proto proto/complex --out generated/complex

# Clean generated files
clean:
	rm -rf protoc-http-go test_output* generated/
	go clean

# Show help
help:
	@echo "Available targets:"
	@echo "  build            - Build the protoc-http-go binary"
	@echo "  install          - Install/update Go dependencies"  
	@echo "  test             - Run tests to verify functionality"
	@echo "  generate-simple  - Generate Go code from simple proto files"
	@echo "  generate-complex - Generate Go code from complex proto files"
	@echo "  clean            - Clean generated files"
	@echo "  help             - Show this help message"