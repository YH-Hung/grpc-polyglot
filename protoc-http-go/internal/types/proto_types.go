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
	ParentName      string // Parent message name for nested messages (used for msgHdr detection)
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

// JSONTagName provides the JSON tag names for fields (camelCase)
// Special case: fields in messages named "msgHdr" preserve exact casing from proto
func JSONTagName(protoFieldName string, messageName string) string {
	if len(protoFieldName) == 0 {
		return protoFieldName
	}

	// Special case: msgHdr messages preserve exact field names
	if messageName == "msgHdr" {
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
// Special case: "N2" pattern converts to "-n2-" not "-n-2-"
func KebabCase(s string) string {
	if len(s) == 0 {
		return s
	}

	result := make([]rune, 0, len(s)*2)
	runes := []rune(s)

	for i := 0; i < len(runes); i++ {
		r := runes[i]

		// Check for N2 pattern (special case: only N2, not N3, N4, etc.)
		if i+1 < len(runes) && r == 'N' && runes[i+1] == '2' {
			// Check if we need a dash before N2
			if len(result) > 0 {
				result = append(result, '-')
			}
			result = append(result, 'n', '2')
			i++ // Skip the '2'
			continue
		}

		// Insert dash before uppercase letters or digits (except at position 0)
		if i > 0 && (r >= 'A' && r <= 'Z' || r >= '0' && r <= '9') {
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

// VBReservedKeywords contains all 148 VB.NET reserved keywords that must be escaped with square brackets
// Source: https://learn.microsoft.com/en-us/dotnet/visual-basic/language-reference/keywords/
var VBReservedKeywords = map[string]bool{
	"AddHandler": true, "AddressOf": true, "Alias": true, "And": true, "AndAlso": true, "As": true, "Boolean": true,
	"ByRef": true, "Byte": true, "ByVal": true, "Call": true, "Case": true, "Catch": true, "CBool": true,
	"CByte": true, "CChar": true, "CDate": true, "CDbl": true, "CDec": true, "Char": true, "CInt": true,
	"Class": true, "CLng": true, "CObj": true, "Const": true, "Continue": true, "CSByte": true, "CShort": true,
	"CSng": true, "CStr": true, "CType": true, "CUInt": true, "CULng": true, "CUShort": true, "Date": true,
	"Decimal": true, "Declare": true, "Default": true, "Delegate": true, "Dim": true, "DirectCast": true,
	"Do": true, "Double": true, "Each": true, "Else": true, "ElseIf": true, "End": true, "EndIf": true,
	"Enum": true, "Erase": true, "Error": true, "Event": true, "Exit": true, "False": true, "Finally": true,
	"For": true, "Friend": true, "Function": true, "Get": true, "GetType": true, "GetXMLNamespace": true,
	"Global": true, "GoTo": true, "Handles": true, "If": true, "Implements": true, "Imports": true, "In": true,
	"Inherits": true, "Integer": true, "Interface": true, "Is": true, "IsNot": true, "Lib": true, "Like": true,
	"Long": true, "Loop": true, "Me": true, "Mod": true, "Module": true, "MustInherit": true, "MustOverride": true,
	"MyBase": true, "MyClass": true, "NameOf": true, "Namespace": true, "Narrowing": true, "New": true,
	"Next": true, "Not": true, "Nothing": true, "NotInheritable": true, "NotOverridable": true, "Object": true,
	"Of": true, "Operator": true, "Option": true, "Optional": true, "Or": true, "OrElse": true, "Overloads": true,
	"Overridable": true, "Overrides": true, "ParamArray": true, "Partial": true, "Private": true, "Property": true,
	"Protected": true, "Public": true, "RaiseEvent": true, "ReadOnly": true, "ReDim": true, "REM": true,
	"RemoveHandler": true, "Resume": true, "Return": true, "SByte": true, "Select": true, "Set": true,
	"Shadows": true, "Shared": true, "Short": true, "Single": true, "Static": true, "Step": true, "Stop": true,
	"String": true, "Structure": true, "Sub": true, "SyncLock": true, "Then": true, "Throw": true, "To": true,
	"True": true, "Try": true, "TryCast": true, "TypeOf": true, "UInteger": true, "ULong": true, "UShort": true,
	"Using": true, "When": true, "While": true, "Widening": true, "With": true, "WithEvents": true,
	"WriteOnly": true, "Xor": true,
}

// EscapeVBIdentifier escapes VB.NET reserved keywords by wrapping them in square brackets
func EscapeVBIdentifier(name string) string {
	if VBReservedKeywords[name] {
		return "[" + name + "]"
	}
	return name
}