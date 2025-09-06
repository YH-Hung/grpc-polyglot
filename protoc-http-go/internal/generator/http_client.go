package generator

import (
	"fmt"
	"os"
	"strings"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

// Generator handles the generation of Go HTTP client code
type Generator struct {
	PackageOverride string
	BaseURL         string
}

// GenerateFile generates a complete Go file for the given proto file
func (g *Generator) GenerateFile(protoFile *types.ProtoFile, outputPath string) error {
	var sb strings.Builder
	
	// Determine package name
	packageName := g.determinePackageName(protoFile)
	
	// Write package declaration and imports
	sb.WriteString(fmt.Sprintf("package %s\n\n", packageName))
	sb.WriteString("import (\n")
	sb.WriteString("\t\"bytes\"\n")
	sb.WriteString("\t\"context\"\n")
	sb.WriteString("\t\"encoding/json\"\n")
	sb.WriteString("\t\"fmt\"\n")
	sb.WriteString("\t\"io\"\n")
	sb.WriteString("\t\"net/http\"\n")
	sb.WriteString(")\n\n")
	
	// Generate enums
	for _, enum := range protoFile.Enums {
		g.generateEnum(&sb, enum)
		sb.WriteString("\n")
	}
	
	// Generate messages (including nested)
	for _, message := range protoFile.Messages {
		g.generateMessage(&sb, message, "")
		sb.WriteString("\n")
	}
	
	// Generate service clients
	for _, service := range protoFile.Services {
		g.generateServiceClient(&sb, service, protoFile.BaseName)
		sb.WriteString("\n")
	}
	
	// Write to file
	return os.WriteFile(outputPath, []byte(sb.String()), 0644)
}

// determinePackageName determines the Go package name
func (g *Generator) determinePackageName(protoFile *types.ProtoFile) string {
	if g.PackageOverride != "" {
		return g.PackageOverride
	}
	
	if protoFile.Package != "" {
		// Convert package name to valid Go package name
		pkg := strings.ReplaceAll(protoFile.Package, ".", "_")
		pkg = strings.ReplaceAll(pkg, "-", "_")
		return strings.ToLower(pkg)
	}
	
	// Use base filename as package name
	pkg := strings.ReplaceAll(protoFile.BaseName, "-", "_")
	return strings.ToLower(pkg)
}

// generateEnum generates a Go enum (const block with iota)
func (g *Generator) generateEnum(sb *strings.Builder, enum *types.ProtoEnum) {
	sb.WriteString(fmt.Sprintf("// %s represents the %s enum from the proto definition\n", enum.Name, enum.Name))
	sb.WriteString(fmt.Sprintf("type %s int32\n\n", enum.Name))
	
	sb.WriteString("const (\n")
	for value, num := range enum.Values {
		sb.WriteString(fmt.Sprintf("\t%s_%s %s = %d\n", enum.Name, value, enum.Name, num))
	}
	sb.WriteString(")\n\n")
	
	// Generate string method
	sb.WriteString(fmt.Sprintf("func (e %s) String() string {\n", enum.Name))
	sb.WriteString("\tswitch e {\n")
	for value, num := range enum.Values {
		sb.WriteString(fmt.Sprintf("\tcase %d:\n\t\treturn \"%s\"\n", num, value))
	}
	sb.WriteString(fmt.Sprintf("\tdefault:\n\t\treturn fmt.Sprintf(\"Unknown_%s(%%d)\", int32(e))\n", enum.Name))
	sb.WriteString("\t}\n")
	sb.WriteString("}\n")
}

// generateMessage generates a Go struct for a proto message
func (g *Generator) generateMessage(sb *strings.Builder, message *types.ProtoMessage, parentName string) {
	structName := message.Name
	if parentName != "" {
		structName = fmt.Sprintf("%s_%s", parentName, message.Name)
	}
	
	sb.WriteString(fmt.Sprintf("// %s represents the %s message from the proto definition\n", structName, message.Name))
	sb.WriteString(fmt.Sprintf("type %s struct {\n", structName))
	
	// Generate fields
	for _, field := range message.Fields {
		goFieldName := types.GoFieldName(field.Name)
		goType := g.getGoType(field.Type)
		jsonTag := types.JSONTagName(field.Name)
		
		if field.Repeated {
			goType = fmt.Sprintf("[]%s", goType)
		}
		
		sb.WriteString(fmt.Sprintf("\t%s %s `json:\"%s\"`\n", goFieldName, goType, jsonTag))
	}
	
	sb.WriteString("}\n")
	
	// Generate nested enums
	for _, nestedEnum := range message.NestedEnums {
		sb.WriteString("\n")
		g.generateEnum(sb, nestedEnum)
	}
	
	// Generate nested messages recursively
	for _, nestedMessage := range message.NestedMessages {
		sb.WriteString("\n")
		g.generateMessage(sb, nestedMessage, structName)
	}
}

// getGoType maps proto types to Go types
func (g *Generator) getGoType(protoType string) string {
	// Check if it's a scalar type
	if goType, exists := types.GoTypeMappings[protoType]; exists {
		return goType
	}
	
	// For non-scalar types, assume they are message types in the same package
	// Handle dotted names (e.g., "common.Ticker" -> "Common_Ticker")
	if strings.Contains(protoType, ".") {
		parts := strings.Split(protoType, ".")
		for i, part := range parts {
			parts[i] = strings.Title(part)
		}
		return strings.Join(parts, "_")
	}
	
	// Simple message type reference
	return protoType
}

// generateServiceClient generates HTTP client for a proto service
func (g *Generator) generateServiceClient(sb *strings.Builder, service *types.ProtoService, protoBaseName string) {
	clientName := fmt.Sprintf("%sClient", service.Name)
	
	sb.WriteString(fmt.Sprintf("// %s is an HTTP client for the %s service\n", clientName, service.Name))
	sb.WriteString(fmt.Sprintf("type %s struct {\n", clientName))
	sb.WriteString("\tBaseURL    string\n")
	sb.WriteString("\tHTTPClient *http.Client\n")
	sb.WriteString("}\n\n")
	
	// Constructor
	sb.WriteString(fmt.Sprintf("// New%s creates a new %s with the given base URL\n", clientName, clientName))
	sb.WriteString(fmt.Sprintf("func New%s(baseURL string) *%s {\n", clientName, clientName))
	sb.WriteString(fmt.Sprintf("\treturn &%s{\n", clientName))
	sb.WriteString("\t\tBaseURL:    baseURL,\n")
	sb.WriteString("\t\tHTTPClient: &http.Client{},\n")
	sb.WriteString("\t}\n")
	sb.WriteString("}\n\n")
	
	// Constructor with custom HTTP client
	sb.WriteString(fmt.Sprintf("// New%sWithClient creates a new %s with a custom HTTP client\n", clientName, clientName))
	sb.WriteString(fmt.Sprintf("func New%sWithClient(baseURL string, httpClient *http.Client) *%s {\n", clientName, clientName))
	sb.WriteString(fmt.Sprintf("\treturn &%s{\n", clientName))
	sb.WriteString("\t\tBaseURL:    baseURL,\n")
	sb.WriteString("\t\tHTTPClient: httpClient,\n")
	sb.WriteString("\t}\n")
	sb.WriteString("}\n\n")
	
	// Generate methods for each RPC
	for _, rpc := range service.RPCs {
		if rpc.IsUnary {
			g.generateRPCMethod(sb, clientName, rpc, protoBaseName)
		}
	}
}

// generateRPCMethod generates an HTTP client method for a single RPC
func (g *Generator) generateRPCMethod(sb *strings.Builder, clientName string, rpc *types.ProtoRPC, protoBaseName string) {
	methodName := rpc.Name
	inputType := g.getGoType(rpc.InputType)
	outputType := g.getGoType(rpc.OutputType)
	urlPath := types.KebabCase(rpc.Name)
	
	sb.WriteString(fmt.Sprintf("// %s calls the %s RPC method\n", methodName, rpc.Name))
	sb.WriteString(fmt.Sprintf("func (c *%s) %s(ctx context.Context, req *%s) (*%s, error) {\n", clientName, methodName, inputType, outputType))
	
	// Serialize request
	sb.WriteString("\t// Serialize request to JSON\n")
	sb.WriteString("\treqJSON, err := json.Marshal(req)\n")
	sb.WriteString("\tif err != nil {\n")
	sb.WriteString("\t\treturn nil, fmt.Errorf(\"failed to marshal request: %w\", err)\n")
	sb.WriteString("\t}\n\n")
	
	// Create HTTP request
	sb.WriteString("\t// Create HTTP request\n")
	sb.WriteString(fmt.Sprintf("\turl := c.BaseURL + \"/%s/%s\"\n", protoBaseName, urlPath))
	sb.WriteString("\thttpReq, err := http.NewRequestWithContext(ctx, \"POST\", url, bytes.NewReader(reqJSON))\n")
	sb.WriteString("\tif err != nil {\n")
	sb.WriteString("\t\treturn nil, fmt.Errorf(\"failed to create HTTP request: %w\", err)\n")
	sb.WriteString("\t}\n\n")
	
	// Set headers
	sb.WriteString("\t// Set headers\n")
	sb.WriteString("\thttpReq.Header.Set(\"Content-Type\", \"application/json\")\n")
	sb.WriteString("\thttpReq.Header.Set(\"Accept\", \"application/json\")\n\n")
	
	// Make HTTP request
	sb.WriteString("\t// Make HTTP request\n")
	sb.WriteString("\tresp, err := c.HTTPClient.Do(httpReq)\n")
	sb.WriteString("\tif err != nil {\n")
	sb.WriteString("\t\treturn nil, fmt.Errorf(\"HTTP request failed: %w\", err)\n")
	sb.WriteString("\t}\n")
	sb.WriteString("\tdefer resp.Body.Close()\n\n")
	
	// Read response
	sb.WriteString("\t// Read response body\n")
	sb.WriteString("\trespBody, err := io.ReadAll(resp.Body)\n")
	sb.WriteString("\tif err != nil {\n")
	sb.WriteString("\t\treturn nil, fmt.Errorf(\"failed to read response body: %w\", err)\n")
	sb.WriteString("\t}\n\n")
	
	// Check status code
	sb.WriteString("\t// Check status code\n")
	sb.WriteString("\tif resp.StatusCode != http.StatusOK {\n")
	sb.WriteString("\t\treturn nil, fmt.Errorf(\"HTTP request failed with status %d: %s\", resp.StatusCode, string(respBody))\n")
	sb.WriteString("\t}\n\n")
	
	// Deserialize response
	sb.WriteString("\t// Deserialize response\n")
	sb.WriteString(fmt.Sprintf("\tvar response %s\n", outputType))
	sb.WriteString("\tif err := json.Unmarshal(respBody, &response); err != nil {\n")
	sb.WriteString("\t\treturn nil, fmt.Errorf(\"failed to unmarshal response: %w\", err)\n")
	sb.WriteString("\t}\n\n")
	
	sb.WriteString("\treturn &response, nil\n")
	sb.WriteString("}\n\n")
}