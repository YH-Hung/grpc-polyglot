package types

import "strings"

// ProtoField represents a field in a protobuf message
type ProtoField struct {
	Name     string
	Type     string
	Number   int
	Repeated bool
}

// ProtoMessage represents a protobuf message definition
type ProtoMessage struct {
	Name            string
	Fields          []*ProtoField
	NestedMessages  map[string]*ProtoMessage
	NestedEnums     map[string]*ProtoEnum
}

// ProtoEnum represents a protobuf enum definition
type ProtoEnum struct {
	Name   string
	Values map[string]int
}

// ProtoRPC represents a single RPC method in a service
type ProtoRPC struct {
	Name       string
	InputType  string
	OutputType string
	IsUnary    bool // Only unary RPCs are supported
}

// ProtoService represents a protobuf service definition
type ProtoService struct {
	Name string
	RPCs []*ProtoRPC
}

// ProtoFile represents a complete parsed .proto file
type ProtoFile struct {
	FileName          string          // Original file path
	BaseName          string          // File name without .proto extension
	Package           string          // Proto package name
	Imports           []string        // Import statements
	Messages          map[string]*ProtoMessage
	Enums             map[string]*ProtoEnum
	Services          []*ProtoService
	UseSharedUtility  bool            // Whether to use shared HTTP utility
	SharedUtilityName string          // Name of shared HTTP utility class
}

// GoTypeMappings maps protobuf scalar types to Go types
var GoTypeMappings = map[string]string{
	"string":   "string",
	"int32":    "int32",
	"int64":    "int64",
	"uint32":   "uint32",
	"uint64":   "uint64",
	"sint32":   "int32",
	"sint64":   "int64",
	"fixed32":  "uint32",
	"fixed64":  "uint64",
	"sfixed32": "int32",
	"sfixed64": "int64",
	"bool":     "bool",
	"bytes":    "[]byte",
	"double":   "float64",
	"float":    "float32",
}

// VBTypeMappings maps protobuf scalar types to VB.NET types
var VBTypeMappings = map[string]string{
	"string":   "String",
	"int32":    "Integer",
	"int64":    "Long",
	"uint32":   "UInteger",
	"uint64":   "ULong",
	"sint32":   "Integer",
	"sint64":   "Long",
	"fixed32":  "UInteger",
	"fixed64":  "ULong",
	"sfixed32": "Integer",
	"sfixed64": "Long",
	"bool":     "Boolean",
	"bytes":    "Byte()",
	"double":   "Double",
	"float":    "Single",
}

// JSONTagMappings provides the JSON tag names for fields (camelCase)
func JSONTagName(protoFieldName string) string {
	if len(protoFieldName) == 0 {
		return protoFieldName
	}
	
	// Convert snake_case to camelCase
	result := make([]rune, 0, len(protoFieldName))
	capitalizeNext := false
	
	for i, r := range protoFieldName {
		if r == '_' {
			capitalizeNext = true
		} else if capitalizeNext {
			result = append(result, toUpper(r))
			capitalizeNext = false
		} else if i == 0 {
			result = append(result, toLower(r))
		} else {
			result = append(result, r)
		}
	}
	
	return string(result)
}

func toUpper(r rune) rune {
	if r >= 'a' && r <= 'z' {
		return r - 'a' + 'A'
	}
	return r
}

func toLower(r rune) rune {
	if r >= 'A' && r <= 'Z' {
		return r - 'A' + 'a'
	}
	return r
}

// GoFieldName converts proto field names to Go field names (PascalCase)
func GoFieldName(protoFieldName string) string {
	if len(protoFieldName) == 0 {
		return protoFieldName
	}
	
	// Convert snake_case to PascalCase
	result := make([]rune, 0, len(protoFieldName))
	capitalizeNext := true
	
	for _, r := range protoFieldName {
		if r == '_' {
			capitalizeNext = true
		} else if capitalizeNext {
			result = append(result, toUpper(r))
			capitalizeNext = false
		} else {
			result = append(result, r)
		}
	}
	
	return string(result)
}

// KebabCase converts PascalCase/camelCase to kebab-case for URLs
func KebabCase(s string) string {
	if len(s) == 0 {
		return s
	}
	
	result := make([]rune, 0, len(s)*2)
	
	for i, r := range s {
		if i > 0 && r >= 'A' && r <= 'Z' {
			result = append(result, '-')
		}
		result = append(result, toLower(r))
	}
	
	return string(result)
}

// ParseRPCNameAndVersion splits an RPC name into a base method name and URL version suffix (v1, v2, ...)
// Examples: SayHello -> ("SayHello", "v1"), SayHelloV2 -> ("SayHello", "v2")
func ParseRPCNameAndVersion(name string) (baseName string, version string) {
	if name == "" {
		return name, "v1"
	}
	// Scan from the end for trailing digits
	i := len(name) - 1
	for i >= 0 {
		c := name[i]
		if c < '0' || c > '9' {
			break
		}
		i--
	}
	// i now points to the character before the digits (or end if no digits)
	if i >= 0 && i < len(name)-1 {
		// There are trailing digits; check for preceding V/v
		if name[i] == 'V' || name[i] == 'v' {
			base := name[:i]
			digits := name[i+1:]
			if base != "" && digits != "" {
				return base, "v" + strings.ToLower(digits)
			}
		}
	}
	return name, "v1"
}