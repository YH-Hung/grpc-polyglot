package generator

import (
	"fmt"
	"os"
	"strings"
	"unicode"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

// toTitle converts a string to title case, replacing deprecated strings.Title
func toTitle(s string) string {
	if s == "" {
		return s
	}
	runes := []rune(s)
	runes[0] = unicode.ToUpper(runes[0])
	return string(runes)
}

// Generator handles the generation of VB.NET HTTP client code
type Generator struct {
	PackageOverride string
	BaseURL         string
	FrameworkMode   string // "net45" or "net40hwr"
}

// GenerateFile generates a complete VB.NET file for the given proto file
func (g *Generator) GenerateFile(protoFile *types.ProtoFile, outputPath string) error {
	var sb strings.Builder

	// Determine namespace name
	namespace := g.determinePackageName(protoFile)

	// VB file header and imports
	sb.WriteString("Option Strict On\n")
	sb.WriteString("Option Explicit On\n")
	sb.WriteString("Option Infer On\n\n")
	g.generateImports(&sb)

	sb.WriteString(fmt.Sprintf("Namespace %s\n\n", namespace))

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
		if g.FrameworkMode == "net40hwr" {
			g.generateServiceClientNet40HWR(&sb, service, protoFile.BaseName)
		} else {
			g.generateServiceClientNet45(&sb, service, protoFile.BaseName)
		}
		sb.WriteString("\n")
	}

	sb.WriteString("End Namespace\n")

	// Write to file
	return os.WriteFile(outputPath, []byte(sb.String()), 0644)
}

// determinePackageName determines the VB.NET namespace name based on the proto package or file name
func (g *Generator) determinePackageName(protoFile *types.ProtoFile) string {
	if g.PackageOverride != "" {
		return g.PackageOverride
	}
	// If proto package exists, convert to PascalCase segments joined by dots
	if protoFile.Package != "" {
		parts := strings.Split(protoFile.Package, ".")
		for i, p := range parts {
			p = strings.ReplaceAll(p, "-", "_")
			parts[i] = toTitle(p)
		}
		return strings.Join(parts, ".")
	}
	// Fallback to base filename in PascalCase
	name := strings.ReplaceAll(protoFile.BaseName, "-", "_")
	return toTitle(name)
}

// generateEnum generates a VB.NET Enum
func (g *Generator) generateEnum(sb *strings.Builder, enum *types.ProtoEnum) {
	fmt.Fprintf(sb, "' %s represents the %s enum from the proto definition\n", enum.Name, enum.Name)
	fmt.Fprintf(sb, "Public Enum %s As Integer\n", enum.Name)
	for value, num := range enum.Values {
		fmt.Fprintf(sb, "    %s_%s = %d\n", enum.Name, value, num)
	}
	sb.WriteString("End Enum\n")
}

// generateMessage generates a VB.NET Class for a proto message
func (g *Generator) generateMessage(sb *strings.Builder, message *types.ProtoMessage, parentName string) {
	className := message.Name
	if parentName != "" {
		className = fmt.Sprintf("%s_%s", parentName, message.Name)
	}

	fmt.Fprintf(sb, "' %s represents the %s message from the proto definition\n", className, message.Name)
	fmt.Fprintf(sb, "Public Class %s\n", className)

	// Generate properties
	for _, field := range message.Fields {
		vbFieldName := types.GoFieldName(field.Name)
		vbType := g.getGoType(field.Type)
		jsonTag := types.JSONTagName(field.Name)
		if field.Repeated {
			vbType = fmt.Sprintf("List(Of %s)", vbType)
		}
		fmt.Fprintf(sb, "    <JsonProperty(\"%s\")>\n", jsonTag)
		fmt.Fprintf(sb, "    Public Property %s As %s\n", vbFieldName, vbType)
	}

	sb.WriteString("End Class\n")

	// Generate nested enums
	for _, nestedEnum := range message.NestedEnums {
		sb.WriteString("\n")
		g.generateEnum(sb, nestedEnum)
	}

	// Generate nested messages recursively
	for _, nestedMessage := range message.NestedMessages {
		sb.WriteString("\n")
		g.generateMessage(sb, nestedMessage, className)
	}
}

// getGoType maps proto types to VB.NET types
func (g *Generator) getGoType(protoType string) string {
	// Check if it's a scalar type
	if vbType, exists := types.VBTypeMappings[protoType]; exists {
		return vbType
	}
	// For non-scalar types, assume they are message types in the same namespace
	// Handle dotted names (e.g., "common.Ticker" -> "Common_Ticker")
	if strings.Contains(protoType, ".") {
		parts := strings.Split(protoType, ".")
		for i, part := range parts {
			parts[i] = toTitle(part)
		}
		return strings.Join(parts, "_")
	}
	// Simple message type reference
	return protoType
}

// generateImports generates framework-specific imports
func (g *Generator) generateImports(sb *strings.Builder) {
	sb.WriteString("Imports System\n")
	sb.WriteString("Imports System.Text\n")
	sb.WriteString("Imports System.Collections.Generic\n")
	sb.WriteString("Imports Newtonsoft.Json\n")
	sb.WriteString("Imports Newtonsoft.Json.Serialization\n")

	if g.FrameworkMode == "net40hwr" {
		// .NET 4.0 with HttpWebRequest
		sb.WriteString("Imports System.Net\n")
		sb.WriteString("Imports System.IO\n")
	} else {
		// .NET 4.5+ or .NET 4.0 with NuGet packages
		sb.WriteString("Imports System.Net.Http\n")
		sb.WriteString("Imports System.Net.Http.Headers\n")
		sb.WriteString("Imports System.Threading\n")
		sb.WriteString("Imports System.Threading.Tasks\n")
	}
	sb.WriteString("\n")
}

// generateServiceClientNet45 generates VB.NET HTTP client for .NET 4.5+ mode
func (g *Generator) generateServiceClientNet45(sb *strings.Builder, service *types.ProtoService, protoBaseName string) {
	clientName := fmt.Sprintf("%sClient", service.Name)

	fmt.Fprintf(sb, "' %s is an HTTP client for the %s service\n", clientName, service.Name)
	fmt.Fprintf(sb, "Public Class %s\n", clientName)
	sb.WriteString("    Public Property BaseUrl As String\n")
	sb.WriteString("    Private ReadOnly _httpClient As HttpClient\n")
	sb.WriteString("\n")
	// Constructor with HttpClient injection
	fmt.Fprintf(sb, "    Public Sub New(baseUrl As String, httpClient As HttpClient)\n")
	sb.WriteString("        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	sb.WriteString("        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))\n")
	sb.WriteString("        Me.BaseUrl = baseUrl\n")
	sb.WriteString("        Me._httpClient = httpClient\n")
	sb.WriteString("    End Sub\n\n")

	// Shared helper to reduce duplicated HTTP request/response code
	sb.WriteString("    Private Async Function PostJsonAsync(Of TResponse)(url As String, requestBody As Object, cancellationToken As CancellationToken) As Task(Of TResponse)\n")
	sb.WriteString("        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }\n")
	sb.WriteString("        Dim reqJson As String = JsonConvert.SerializeObject(requestBody, settings)\n")
	sb.WriteString("        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)\n")
	sb.WriteString("            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, \"application/json\")\n")
	sb.WriteString("            httpRequest.Headers.Accept.Clear()\n")
	sb.WriteString("            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue(\"application/json\"))\n")
	sb.WriteString("            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)\n")
	sb.WriteString("            Dim respBody As String = Await response.Content.ReadAsStringAsync()\n")
	sb.WriteString("            If Not response.IsSuccessStatusCode Then\n")
	sb.WriteString("                Throw New HttpRequestException(String.Format(\"HTTP request failed with status {0}: {1}\", CInt(response.StatusCode), respBody))\n")
	sb.WriteString("            End If\n")
	sb.WriteString("            Dim result As TResponse = JsonConvert.DeserializeObject(Of TResponse)(respBody, settings)\n")
	sb.WriteString("            Return result\n")
	sb.WriteString("        End Using\n")
	sb.WriteString("    End Function\n\n")

	// Generate methods for each RPC
	for _, rpc := range service.RPCs {
		if rpc.IsUnary {
			g.generateRPCMethodNet45(sb, clientName, rpc, protoBaseName)
		}
	}

	sb.WriteString("End Class\n")
}

// generateRPCMethodNet45 generates a VB.NET Async HTTP client method for .NET 4.5+ mode
func (g *Generator) generateRPCMethodNet45(sb *strings.Builder, _ string, rpc *types.ProtoRPC, protoBaseName string) {
	methodName := rpc.Name
	inputType := g.getGoType(rpc.InputType)
	outputType := g.getGoType(rpc.OutputType)
	baseName, version := types.ParseRPCNameAndVersion(rpc.Name)
	urlPath := types.KebabCase(baseName)

	fmt.Fprintf(sb, "    ' %s calls the %s RPC method\n", methodName+"Async", rpc.Name)
	fmt.Fprintf(sb, "    Public Async Function %sAsync(request As %s, Optional cancellationToken As CancellationToken = Nothing) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Dim url As String = Me.BaseUrl & \"/%s/%s/\" & \"%s\"\n", protoBaseName, urlPath, version)
	fmt.Fprintf(sb, "        Return Await PostJsonAsync(Of %s)(url, request, cancellationToken)\n", outputType)
	sb.WriteString("    End Function\n\n")
}

// generateServiceClientNet40HWR generates VB.NET HTTP client for .NET 4.0 with HttpWebRequest
func (g *Generator) generateServiceClientNet40HWR(sb *strings.Builder, service *types.ProtoService, protoBaseName string) {
	clientName := fmt.Sprintf("%sClient", service.Name)

	fmt.Fprintf(sb, "' %s is an HTTP client for the %s service\n", clientName, service.Name)
	fmt.Fprintf(sb, "Public Class %s\n", clientName)
	sb.WriteString("    Public Property BaseUrl As String\n")
	sb.WriteString("\n")

	// Constructor (no HttpClient injection for net40hwr mode)
	sb.WriteString("    Public Sub New(baseUrl As String)\n")
	sb.WriteString("        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	sb.WriteString("        Me.BaseUrl = baseUrl\n")
	sb.WriteString("    End Sub\n\n")

	// Shared helper method for HttpWebRequest
	sb.WriteString("    Private Function PostJson(Of TResponse)(url As String, requestBody As Object, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResponse\n")
	sb.WriteString("        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }\n")
	sb.WriteString("        Dim reqJson As String = JsonConvert.SerializeObject(requestBody, settings)\n")
	sb.WriteString("        \n")
	sb.WriteString("        Dim request As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)\n")
	sb.WriteString("        request.Method = \"POST\"\n")
	sb.WriteString("        request.ContentType = \"application/json\"\n")
	sb.WriteString("        request.Accept = \"application/json\"\n")
	sb.WriteString("        \n")
	sb.WriteString("        ' Add authorization headers if provided\n")
	sb.WriteString("        If authHeaders IsNot Nothing Then\n")
	sb.WriteString("            For Each kvp In authHeaders\n")
	sb.WriteString("                request.Headers.Add(kvp.Key, kvp.Value)\n")
	sb.WriteString("            Next\n")
	sb.WriteString("        End If\n")
	sb.WriteString("        \n")
	sb.WriteString("        ' Write request body\n")
	sb.WriteString("        Dim requestBytes As Byte() = Encoding.UTF8.GetBytes(reqJson)\n")
	sb.WriteString("        request.ContentLength = requestBytes.Length\n")
	sb.WriteString("        Using requestStream As Stream = request.GetRequestStream()\n")
	sb.WriteString("            requestStream.Write(requestBytes, 0, requestBytes.Length)\n")
	sb.WriteString("        End Using\n")
	sb.WriteString("        \n")
	sb.WriteString("        ' Get response\n")
	sb.WriteString("        Using response As HttpWebResponse = CType(request.GetResponse(), HttpWebResponse)\n")
	sb.WriteString("            Using responseStream As Stream = response.GetResponseStream()\n")
	sb.WriteString("                Using reader As New StreamReader(responseStream)\n")
	sb.WriteString("                    Dim respBody As String = reader.ReadToEnd()\n")
	sb.WriteString("                    If response.StatusCode <> HttpStatusCode.OK Then\n")
	sb.WriteString("                        Throw New WebException(String.Format(\"HTTP request failed with status {0}: {1}\", CInt(response.StatusCode), respBody))\n")
	sb.WriteString("                    End If\n")
	sb.WriteString("                    Dim result As TResponse = JsonConvert.DeserializeObject(Of TResponse)(respBody, settings)\n")
	sb.WriteString("                    Return result\n")
	sb.WriteString("                End Using\n")
	sb.WriteString("            End Using\n")
	sb.WriteString("        End Using\n")
	sb.WriteString("    End Function\n\n")

	// Generate methods for each RPC
	for _, rpc := range service.RPCs {
		if rpc.IsUnary {
			g.generateRPCMethodNet40HWR(sb, clientName, rpc, protoBaseName)
		}
	}

	sb.WriteString("End Class\n")
}

// generateRPCMethodNet40HWR generates a VB.NET synchronous HTTP client method for .NET 4.0 mode
func (g *Generator) generateRPCMethodNet40HWR(sb *strings.Builder, _ string, rpc *types.ProtoRPC, protoBaseName string) {
	methodName := rpc.Name
	inputType := g.getGoType(rpc.InputType)
	outputType := g.getGoType(rpc.OutputType)
	baseName, version := types.ParseRPCNameAndVersion(rpc.Name)
	urlPath := types.KebabCase(baseName)

	fmt.Fprintf(sb, "    ' %s calls the %s RPC method\n", methodName, rpc.Name)
	fmt.Fprintf(sb, "    Public Function %s(request As %s, Optional authHeaders As Dictionary(Of String, String) = Nothing) As %s\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Dim url As String = Me.BaseUrl & \"/%s/%s/\" & \"%s\"\n", protoBaseName, urlPath, version)
	fmt.Fprintf(sb, "        Return PostJson(Of %s)(url, request, authHeaders)\n", outputType)
	sb.WriteString("    End Function\n\n")
}
