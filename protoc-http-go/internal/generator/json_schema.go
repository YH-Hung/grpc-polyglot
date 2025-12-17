package generator

import (
	"encoding/json"
	"fmt"
	"os"
	"path/filepath"
	"sort"
	"strings"
	"unicode"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

// ScalarTypeMapJSON maps protobuf scalar types to JSON Schema type definitions
var ScalarTypeMapJSON = map[string]map[string]interface{}{
	"string":   {"type": "string"},
	"int32":    {"type": "integer", "format": "int32"},
	"int64":    {"type": "integer", "format": "int64"},
	"uint32":   {"type": "integer", "format": "uint32", "minimum": 0},
	"uint64":   {"type": "integer", "format": "uint64", "minimum": 0},
	"sint32":   {"type": "integer", "format": "int32"},
	"sint64":   {"type": "integer", "format": "int64"},
	"fixed32":  {"type": "integer", "format": "uint32", "minimum": 0},
	"fixed64":  {"type": "integer", "format": "uint64", "minimum": 0},
	"sfixed32": {"type": "integer", "format": "int32"},
	"sfixed64": {"type": "integer", "format": "int64"},
	"bool":     {"type": "boolean"},
	"float":    {"type": "number", "format": "float"},
	"double":   {"type": "number", "format": "double"},
	"bytes":    {"type": "string", "contentEncoding": "base64"},
}

// buildEnumSchema creates a JSON Schema for a proto enum
func buildEnumSchema(enum *types.ProtoEnum) map[string]interface{} {
	// Extract enum value names
	enumValues := make([]string, 0, len(enum.Values))
	for name := range enum.Values {
		enumValues = append(enumValues, name)
	}

	// Sort for deterministic output
	sort.Strings(enumValues)

	// Build description with value→number mappings
	descriptions := make([]string, 0, len(enum.Values))
	for _, name := range enumValues {
		descriptions = append(descriptions, fmt.Sprintf("%s=%d", name, enum.Values[name]))
	}

	return map[string]interface{}{
		"type":        "string",
		"enum":        enumValues,
		"description": fmt.Sprintf("Enum values: %s", strings.Join(descriptions, ", ")),
	}
}

// qualifyJSONSchemaRef generates a JSON Schema $ref for a proto type.
//
// Handles:
//   - Nested types: Outer.Inner → "#/$defs/Outer.Inner"
//   - Same package: Foo → "#/$defs/Foo"
//   - Cross-package: common.Ticker → "common.json#/$defs/Ticker"
func qualifyJSONSchemaRef(protoType string, currentPkg string) string {
	// Handle nested types and cross-package refs
	if !strings.Contains(protoType, ".") {
		// Simple type in same file
		return "#/$defs/" + protoType
	}

	parts := strings.Split(protoType, ".")

	// Check if starts with uppercase (type name, not package)
	if len(parts[0]) > 0 && unicode.IsUpper(rune(parts[0][0])) {
		// Nested type in current file
		return "#/$defs/" + protoType
	}

	// Find where package ends and type begins (types start with uppercase)
	typeStart := -1
	for i, part := range parts {
		if len(part) > 0 && unicode.IsUpper(rune(part[0])) {
			typeStart = i
			break
		}
	}

	if typeStart <= 0 {
		// All lowercase or starts with type - same file
		return "#/$defs/" + protoType
	}

	// Cross-package reference
	pkg := strings.Join(parts[:typeStart], ".")
	typeName := strings.Join(parts[typeStart:], ".")

	if pkg == currentPkg {
		return "#/$defs/" + typeName
	}

	// Different package - use external file reference
	pkgFile := parts[typeStart-1] // Last segment of package as filename
	return pkgFile + ".json#/$defs/" + typeName
}

// getJSONSchemaType converts a proto field type to JSON Schema type definition.
//
// Returns a JSON Schema type dict (may be {'type': 'array', 'items': {...}} for repeated fields)
func getJSONSchemaType(fieldType string, isRepeated bool, currentPkg string) map[string]interface{} {
	// Handle repeated fields
	if isRepeated {
		baseSchema := getJSONSchemaType(fieldType, false, currentPkg)
		return map[string]interface{}{
			"type":  "array",
			"items": baseSchema,
		}
	}

	// Check if it's a scalar type
	if scalarSchema, exists := ScalarTypeMapJSON[fieldType]; exists {
		// Return a copy to avoid modifying the constant
		result := make(map[string]interface{})
		for k, v := range scalarSchema {
			result[k] = v
		}
		return result
	}

	// Complex type - use $ref
	return map[string]interface{}{
		"$ref": qualifyJSONSchemaRef(fieldType, currentPkg),
	}
}

// collectMessageSchemas recursively collects schemas for a message and its nested types.
//
// It builds qualified names for nested messages (e.g., "Outer.Inner") and adds them
// to the schemas map along with any nested enums.
func collectMessageSchemas(
	msg *types.ProtoMessage,
	parentPath []string,
	schemas map[string]interface{},
	currentPkg string,
) error {
	// Build qualified name
	currentPath := append(parentPath, msg.Name)
	qualifiedName := strings.Join(currentPath, ".")

	// Build properties map
	properties := make(map[string]interface{})
	for _, field := range msg.Fields {
		fieldName := types.JSONTagName(field.Name) // Convert to camelCase
		fieldSchema := getJSONSchemaType(field.Type, field.Repeated, currentPkg)
		properties[fieldName] = fieldSchema
	}

	// Create message schema
	schemas[qualifiedName] = map[string]interface{}{
		"type":                 "object",
		"properties":           properties,
		"additionalProperties": false,
	}

	// Process nested enums
	for _, nestedEnum := range msg.NestedEnums {
		enumQualifiedName := strings.Join(append(currentPath, nestedEnum.Name), ".")
		schemas[enumQualifiedName] = buildEnumSchema(nestedEnum)
	}

	// Recursively process nested messages
	for _, nestedMsg := range msg.NestedMessages {
		if err := collectMessageSchemas(nestedMsg, currentPath, schemas, currentPkg); err != nil {
			return err
		}
	}

	return nil
}

// GenerateJSONSchema generates a JSON Schema file for a proto file.
//
// It creates a json/ subdirectory under outputDir and writes a .json file
// containing schemas for all messages and enums defined in the proto file.
//
// The generated schema follows JSON Schema Draft 2020-12 specification.
//
// Returns the path to the generated JSON schema file or an error.
func GenerateJSONSchema(protoFile *types.ProtoFile, outputDir string) (string, error) {
	// Create json/ subdirectory
	jsonDir := filepath.Join(outputDir, "json")
	if err := os.MkdirAll(jsonDir, 0755); err != nil {
		return "", fmt.Errorf("failed to create json directory: %w", err)
	}

	// Build base schema structure
	baseName := protoFile.BaseName
	description := fmt.Sprintf("JSON Schema definitions for all messages and enums in %s", protoFile.FileName)
	if protoFile.Package != "" {
		description += fmt.Sprintf(" (package: %s)", protoFile.Package)
	}

	schemaDoc := map[string]interface{}{
		"$schema":     "https://json-schema.org/draft/2020-12/schema",
		"$id":         fmt.Sprintf("https://example.com/schemas/%s.json", baseName),
		"title":       fmt.Sprintf("Schemas for %s", protoFile.FileName),
		"description": description,
		"$defs":       make(map[string]interface{}),
	}

	defs := schemaDoc["$defs"].(map[string]interface{})

	// Add enum schemas
	for _, enum := range protoFile.Enums {
		defs[enum.Name] = buildEnumSchema(enum)
	}

	// Collect all message schemas (including nested)
	for _, msg := range protoFile.Messages {
		if err := collectMessageSchemas(msg, []string{}, defs, protoFile.Package); err != nil {
			return "", fmt.Errorf("failed to collect message schemas: %w", err)
		}
	}

	// Marshal to JSON with indentation
	jsonBytes, err := json.MarshalIndent(schemaDoc, "", "  ")
	if err != nil {
		return "", fmt.Errorf("failed to marshal JSON schema: %w", err)
	}

	// Write to file
	outputPath := filepath.Join(jsonDir, baseName+".json")
	if err := os.WriteFile(outputPath, jsonBytes, 0644); err != nil {
		return "", fmt.Errorf("failed to write JSON schema file: %w", err)
	}

	return outputPath, nil
}
