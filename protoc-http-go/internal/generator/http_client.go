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
		if protoFile.UseSharedUtility {
			// Use shared utility
			if g.FrameworkMode == "net40hwr" {
				g.generateServiceClientNet40HWRWithSharedUtility(&sb, service, protoFile.BaseName, protoFile.SharedUtilityName)
			} else {
				g.generateServiceClientNet45WithSharedUtility(&sb, service, protoFile.BaseName, protoFile.SharedUtilityName)
			}
		} else {
			// Use embedded PostJson
			if g.FrameworkMode == "net40hwr" {
				g.generateServiceClientNet40HWR(&sb, service, protoFile.BaseName)
			} else {
				g.generateServiceClientNet45(&sb, service, protoFile.BaseName)
			}
		}
		sb.WriteString("\n")
	}

	sb.WriteString("End Namespace\n")

	// Write to file
	return os.WriteFile(outputPath, []byte(sb.String()), 0644)
}

// determinePackageName determines the VB.NET namespace name based on the proto package or file name
// Priority: 1) proto package declaration, 2) CLI --package override, 3) file base name
func (g *Generator) determinePackageName(protoFile *types.ProtoFile) string {
	// Priority 1: If proto package exists, use it (ignore CLI override)
	if protoFile.Package != "" {
		parts := strings.Split(protoFile.Package, ".")
		for i, p := range parts {
			p = strings.ReplaceAll(p, "-", "_")
			parts[i] = toTitle(p)
		}
		return strings.Join(parts, ".")
	}
	// Priority 2: Use CLI package override as fallback
	if g.PackageOverride != "" {
		return g.PackageOverride
	}
	// Priority 3: Fallback to base filename in PascalCase
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
		vbFieldName := types.EscapeVBIdentifier(types.GoFieldName(field.Name))
		vbType := g.getGoType(field.Type)
		// Pass message name for msgHdr special handling
		jsonTag := types.JSONTagName(field.Name, message.Name)
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
	fmt.Fprintf(sb, "    Public Sub New(httpClient As HttpClient, baseUrl As String)\n")
	sb.WriteString("        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))\n")
	sb.WriteString("        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	sb.WriteString("        Me._httpClient = httpClient\n")
	sb.WriteString("        Me.BaseUrl = baseUrl.TrimEnd(\"/\"c)\n")
	sb.WriteString("    End Sub\n\n")

	// Shared helper to reduce duplicated HTTP request/response code
	sb.WriteString("    Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)\n")
	sb.WriteString("        If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))\n")
	sb.WriteString("        Dim url As String = String.Format(\"{0}/{1}\", Me.BaseUrl, relativePath.TrimStart(\"/\"c))\n")
	sb.WriteString("        Dim json As String = JsonConvert.SerializeObject(request)\n")
	sb.WriteString("        Dim effectiveToken As CancellationToken = cancellationToken\n")
	sb.WriteString("        If timeoutMs.HasValue Then\n")
	sb.WriteString("            Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)\n")
	sb.WriteString("                Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)\n")
	sb.WriteString("                    effectiveToken = combined.Token\n")
	sb.WriteString("                    Using content As New StringContent(json, Encoding.UTF8, \"application/json\")\n")
	sb.WriteString("                        Dim response As HttpResponseMessage = Await Me._httpClient.PostAsync(url, content, effectiveToken).ConfigureAwait(False)\n")
	sb.WriteString("                        If Not response.IsSuccessStatusCode Then\n")
	sb.WriteString("                            Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                            Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")\n")
	sb.WriteString("                        End If\n")
	sb.WriteString("                        Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                        If String.IsNullOrWhiteSpace(respJson) Then\n")
	sb.WriteString("                            Throw New InvalidOperationException(\"Received empty response from server\")\n")
	sb.WriteString("                        End If\n")
	sb.WriteString("                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)\n")
	sb.WriteString("                    End Using\n")
	sb.WriteString("                End Using\n")
	sb.WriteString("            End Using\n")
	sb.WriteString("        Else\n")
	sb.WriteString("            Using content As New StringContent(json, Encoding.UTF8, \"application/json\")\n")
	sb.WriteString("                Dim response As HttpResponseMessage = Await Me._httpClient.PostAsync(url, content, cancellationToken).ConfigureAwait(False)\n")
	sb.WriteString("                If Not response.IsSuccessStatusCode Then\n")
	sb.WriteString("                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                    Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")\n")
	sb.WriteString("                End If\n")
	sb.WriteString("                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                If String.IsNullOrWhiteSpace(respJson) Then\n")
	sb.WriteString("                    Throw New InvalidOperationException(\"Received empty response from server\")\n")
	sb.WriteString("                End If\n")
	sb.WriteString("                Return JsonConvert.DeserializeObject(Of TResp)(respJson)\n")
	sb.WriteString("            End Using\n")
	sb.WriteString("        End If\n")
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
	methodName := rpc.Name + "Async"
	inputType := g.getGoType(rpc.InputType)
	outputType := g.getGoType(rpc.OutputType)
	baseName, version := types.ParseRPCNameAndVersion(rpc.Name)
	urlPath := types.KebabCase(baseName)
	relativePath := fmt.Sprintf("\"/%s/%s/%s\"", protoBaseName, urlPath, version)

	// Overload 1: Simple overload without cancellation token or timeout
	fmt.Fprintf(sb, "    Public Function %s(request As %s) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return %s(request, CancellationToken.None)\n", methodName)
	sb.WriteString("    End Function\n\n")

	// Overload 2: With cancellation token but no timeout
	fmt.Fprintf(sb, "    Public Function %s(request As %s, cancellationToken As CancellationToken) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return %s(request, cancellationToken, Nothing)\n", methodName)
	sb.WriteString("    End Function\n\n")

	// Overload 3: Main implementation with cancellation token and optional timeout
	fmt.Fprintf(sb, "    Public Async Function %s(request As %s, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return Await PostJsonAsync(Of %s, %s)(%s, request, cancellationToken, timeoutMs).ConfigureAwait(False)\n", inputType, outputType, relativePath)
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
	sb.WriteString("        Me.BaseUrl = baseUrl.TrimEnd(\"/\"c)\n")
	sb.WriteString("    End Sub\n\n")

	// Shared helper method for HttpWebRequest (synchronous) to reduce duplication
	sb.WriteString("    Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp\n")
	sb.WriteString("        If request Is Nothing Then Throw New ArgumentNullException(\"request\")\n")
	sb.WriteString("        Dim url As String = String.Format(\"{0}/{1}\", Me.BaseUrl, relativePath.TrimStart(\"/\"c))\n")
	sb.WriteString("        Dim json As String = JsonConvert.SerializeObject(request)\n")
	sb.WriteString("        Dim data As Byte() = Encoding.UTF8.GetBytes(json)\n")
	sb.WriteString("        Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)\n")
	sb.WriteString("        req.Method = \"POST\"\n")
	sb.WriteString("        req.ContentType = \"application/json\"\n")
	sb.WriteString("        req.ContentLength = data.Length\n")
	sb.WriteString("        If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value\n")
	sb.WriteString("        \n")
	sb.WriteString("        ' Add authorization headers if provided\n")
	sb.WriteString("        If authHeaders IsNot Nothing Then\n")
	sb.WriteString("            For Each kvp In authHeaders\n")
	sb.WriteString("                req.Headers.Add(kvp.Key, kvp.Value)\n")
	sb.WriteString("            Next\n")
	sb.WriteString("        End If\n")
	sb.WriteString("        \n")
	sb.WriteString("        Using reqStream As Stream = req.GetRequestStream()\n")
	sb.WriteString("            reqStream.Write(data, 0, data.Length)\n")
	sb.WriteString("        End Using\n")
	sb.WriteString("        Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)\n")
	sb.WriteString("            Using respStream As Stream = resp.GetResponseStream()\n")
	sb.WriteString("                Using reader As New StreamReader(respStream, Encoding.UTF8)\n")
	sb.WriteString("                    Dim respJson As String = reader.ReadToEnd()\n")
	sb.WriteString("                    If String.IsNullOrWhiteSpace(respJson) Then\n")
	sb.WriteString("                        Throw New InvalidOperationException(\"Received empty response from server\")\n")
	sb.WriteString("                    End If\n")
	sb.WriteString("                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)\n")
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
	relativePath := fmt.Sprintf("\"/%s/%s/%s\"", protoBaseName, urlPath, version)

	// Overload 1: Simple overload without timeout or auth headers
	fmt.Fprintf(sb, "    Public Function %s(request As %s) As %s\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return %s(request, Nothing, Nothing)\n", methodName)
	sb.WriteString("    End Function\n\n")

	// Overload 2: Main implementation with optional timeout and auth headers
	fmt.Fprintf(sb, "    Public Function %s(request As %s, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As %s\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return PostJson(Of %s, %s)(%s, request, timeoutMs, authHeaders)\n", inputType, outputType, relativePath)
	sb.WriteString("    End Function\n\n")
}

// GenerateSharedUtility generates a standalone HTTP utility class for multiple proto files
func (g *Generator) GenerateSharedUtility(utilityName, namespace, outputPath string) error {
	var sb strings.Builder

	// File header
	sb.WriteString("Option Strict On\n")
	sb.WriteString("Option Explicit On\n")
	sb.WriteString("Option Infer On\n\n")
	g.generateImports(&sb)

	sb.WriteString(fmt.Sprintf("Namespace %s\n\n", namespace))
	sb.WriteString(fmt.Sprintf("    Public Class %s\n", utilityName))

	if g.FrameworkMode == "net40hwr" {
		g.generateSharedUtilityNet40HWR(&sb)
	} else {
		g.generateSharedUtilityNet45(&sb)
	}

	sb.WriteString("    End Class\n\n")
	sb.WriteString("End Namespace\n")

	return os.WriteFile(outputPath, []byte(sb.String()), 0644)
}

// generateSharedUtilityNet45 generates the shared utility class body for NET45 mode
func (g *Generator) generateSharedUtilityNet45(sb *strings.Builder) {
	// Fields
	sb.WriteString("        Private ReadOnly _http As HttpClient\n")
	sb.WriteString("        Private ReadOnly _baseUrl As String\n\n")

	// Constructor
	sb.WriteString("        Public Sub New(http As HttpClient, baseUrl As String)\n")
	sb.WriteString("            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))\n")
	sb.WriteString("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	sb.WriteString("            _http = http\n")
	sb.WriteString("            _baseUrl = baseUrl.TrimEnd(\"/\"c)\n")
	sb.WriteString("        End Sub\n\n")

	// Public PostJsonAsync method (copied from embedded version but made public)
	sb.WriteString("        Public Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)\n")
	sb.WriteString("            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))\n")
	sb.WriteString("            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))\n")
	sb.WriteString("            Dim json As String = JsonConvert.SerializeObject(request)\n")
	sb.WriteString("            Dim effectiveToken As CancellationToken = cancellationToken\n")
	sb.WriteString("            If timeoutMs.HasValue Then\n")
	sb.WriteString("                Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)\n")
	sb.WriteString("                    Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)\n")
	sb.WriteString("                        effectiveToken = combined.Token\n")
	sb.WriteString("                        Using content As New StringContent(json, Encoding.UTF8, \"application/json\")\n")
	sb.WriteString("                            Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, effectiveToken).ConfigureAwait(False)\n")
	sb.WriteString("                            If Not response.IsSuccessStatusCode Then\n")
	sb.WriteString("                                Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                                Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")\n")
	sb.WriteString("                            End If\n")
	sb.WriteString("                            Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                            If String.IsNullOrWhiteSpace(respJson) Then\n")
	sb.WriteString("                                Throw New InvalidOperationException(\"Received empty response from server\")\n")
	sb.WriteString("                            End If\n")
	sb.WriteString("                            Return JsonConvert.DeserializeObject(Of TResp)(respJson)\n")
	sb.WriteString("                        End Using\n")
	sb.WriteString("                    End Using\n")
	sb.WriteString("                End Using\n")
	sb.WriteString("            Else\n")
	sb.WriteString("                Using content As New StringContent(json, Encoding.UTF8, \"application/json\")\n")
	sb.WriteString("                    Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)\n")
	sb.WriteString("                    If Not response.IsSuccessStatusCode Then\n")
	sb.WriteString("                        Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                        Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")\n")
	sb.WriteString("                    End If\n")
	sb.WriteString("                    Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)\n")
	sb.WriteString("                    If String.IsNullOrWhiteSpace(respJson) Then\n")
	sb.WriteString("                        Throw New InvalidOperationException(\"Received empty response from server\")\n")
	sb.WriteString("                    End If\n")
	sb.WriteString("                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)\n")
	sb.WriteString("                End Using\n")
	sb.WriteString("            End If\n")
	sb.WriteString("        End Function\n")
}

// generateSharedUtilityNet40HWR generates the shared utility class body for NET40HWR mode
func (g *Generator) generateSharedUtilityNet40HWR(sb *strings.Builder) {
	// Fields
	sb.WriteString("        Private ReadOnly _baseUrl As String\n\n")

	// Constructor
	sb.WriteString("        Public Sub New(baseUrl As String)\n")
	sb.WriteString("            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	sb.WriteString("            _baseUrl = baseUrl.TrimEnd(\"/\"c)\n")
	sb.WriteString("        End Sub\n\n")

	// Public PostJson method (copied from embedded version but made public)
	sb.WriteString("        Public Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp\n")
	sb.WriteString("            If request Is Nothing Then Throw New ArgumentNullException(\"request\")\n")
	sb.WriteString("            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))\n")
	sb.WriteString("            Dim json As String = JsonConvert.SerializeObject(request)\n")
	sb.WriteString("            Dim data As Byte() = Encoding.UTF8.GetBytes(json)\n")
	sb.WriteString("            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)\n")
	sb.WriteString("            req.Method = \"POST\"\n")
	sb.WriteString("            req.ContentType = \"application/json\"\n")
	sb.WriteString("            req.ContentLength = data.Length\n")
	sb.WriteString("            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value\n")
	sb.WriteString("            \n")
	sb.WriteString("            ' Add authorization headers if provided\n")
	sb.WriteString("            If authHeaders IsNot Nothing Then\n")
	sb.WriteString("                For Each kvp In authHeaders\n")
	sb.WriteString("                    req.Headers.Add(kvp.Key, kvp.Value)\n")
	sb.WriteString("                Next\n")
	sb.WriteString("            End If\n")
	sb.WriteString("            \n")
	sb.WriteString("            Using reqStream As Stream = req.GetRequestStream()\n")
	sb.WriteString("                reqStream.Write(data, 0, data.Length)\n")
	sb.WriteString("            End Using\n")
	sb.WriteString("            Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)\n")
	sb.WriteString("                Using respStream As Stream = resp.GetResponseStream()\n")
	sb.WriteString("                    Using reader As New StreamReader(respStream, Encoding.UTF8)\n")
	sb.WriteString("                        Dim respJson As String = reader.ReadToEnd()\n")
	sb.WriteString("                        If String.IsNullOrWhiteSpace(respJson) Then\n")
	sb.WriteString("                            Throw New InvalidOperationException(\"Received empty response from server\")\n")
	sb.WriteString("                        End If\n")
	sb.WriteString("                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)\n")
	sb.WriteString("                    End Using\n")
	sb.WriteString("                End Using\n")
	sb.WriteString("            End Using\n")
	sb.WriteString("        End Function\n")
}

// generateServiceClientNet45WithSharedUtility generates service client using shared utility for NET45 mode
func (g *Generator) generateServiceClientNet45WithSharedUtility(sb *strings.Builder, service *types.ProtoService, protoBaseName, sharedUtilityName string) {
	clientName := fmt.Sprintf("%sClient", service.Name)

	fmt.Fprintf(sb, "' %s is an HTTP client for the %s service\n", clientName, service.Name)
	fmt.Fprintf(sb, "Public Class %s\n", clientName)
	fmt.Fprintf(sb, "    Private ReadOnly _httpUtility As %s\n", sharedUtilityName)
	sb.WriteString("\n")

	// Constructor with HttpClient injection
	sb.WriteString("    Public Sub New(httpClient As HttpClient, baseUrl As String)\n")
	sb.WriteString("        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))\n")
	sb.WriteString("        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	fmt.Fprintf(sb, "        _httpUtility = New %s(httpClient, baseUrl)\n", sharedUtilityName)
	sb.WriteString("    End Sub\n\n")

	// Generate methods for each RPC
	for _, rpc := range service.RPCs {
		if rpc.IsUnary {
			g.generateRPCMethodNet45WithSharedUtility(sb, rpc, protoBaseName)
		}
	}

	sb.WriteString("End Class\n")
}

// generateRPCMethodNet45WithSharedUtility generates RPC method that delegates to shared utility
func (g *Generator) generateRPCMethodNet45WithSharedUtility(sb *strings.Builder, rpc *types.ProtoRPC, protoBaseName string) {
	methodName := rpc.Name + "Async"
	inputType := g.getGoType(rpc.InputType)
	outputType := g.getGoType(rpc.OutputType)
	baseName, version := types.ParseRPCNameAndVersion(rpc.Name)
	urlPath := types.KebabCase(baseName)
	relativePath := fmt.Sprintf("\"/%s/%s/%s\"", protoBaseName, urlPath, version)

	// Overload 1: Simple overload without cancellation token or timeout
	fmt.Fprintf(sb, "    Public Function %s(request As %s) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return %s(request, CancellationToken.None)\n", methodName)
	sb.WriteString("    End Function\n\n")

	// Overload 2: With cancellation token but no timeout
	fmt.Fprintf(sb, "    Public Function %s(request As %s, cancellationToken As CancellationToken) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return %s(request, cancellationToken, Nothing)\n", methodName)
	sb.WriteString("    End Function\n\n")

	// Overload 3: Main implementation with cancellation token and optional timeout - delegates to shared utility
	fmt.Fprintf(sb, "    Public Async Function %s(request As %s, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of %s)\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return Await _httpUtility.PostJsonAsync(Of %s, %s)(%s, request, cancellationToken, timeoutMs).ConfigureAwait(False)\n", inputType, outputType, relativePath)
	sb.WriteString("    End Function\n\n")
}

// generateServiceClientNet40HWRWithSharedUtility generates service client using shared utility for NET40HWR mode
func (g *Generator) generateServiceClientNet40HWRWithSharedUtility(sb *strings.Builder, service *types.ProtoService, protoBaseName, sharedUtilityName string) {
	clientName := fmt.Sprintf("%sClient", service.Name)

	fmt.Fprintf(sb, "' %s is an HTTP client for the %s service\n", clientName, service.Name)
	fmt.Fprintf(sb, "Public Class %s\n", clientName)
	fmt.Fprintf(sb, "    Private ReadOnly _httpUtility As %s\n", sharedUtilityName)
	sb.WriteString("\n")

	// Constructor (no HttpClient injection for net40hwr mode)
	sb.WriteString("    Public Sub New(baseUrl As String)\n")
	sb.WriteString("        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")\n")
	fmt.Fprintf(sb, "        _httpUtility = New %s(baseUrl)\n", sharedUtilityName)
	sb.WriteString("    End Sub\n\n")

	// Generate methods for each RPC
	for _, rpc := range service.RPCs {
		if rpc.IsUnary {
			g.generateRPCMethodNet40HWRWithSharedUtility(sb, rpc, protoBaseName)
		}
	}

	sb.WriteString("End Class\n")
}

// generateRPCMethodNet40HWRWithSharedUtility generates RPC method that delegates to shared utility
func (g *Generator) generateRPCMethodNet40HWRWithSharedUtility(sb *strings.Builder, rpc *types.ProtoRPC, protoBaseName string) {
	methodName := rpc.Name
	inputType := g.getGoType(rpc.InputType)
	outputType := g.getGoType(rpc.OutputType)
	baseName, version := types.ParseRPCNameAndVersion(rpc.Name)
	urlPath := types.KebabCase(baseName)
	relativePath := fmt.Sprintf("\"/%s/%s/%s\"", protoBaseName, urlPath, version)

	// Overload 1: Simple overload without timeout or auth headers
	fmt.Fprintf(sb, "    Public Function %s(request As %s) As %s\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return %s(request, Nothing, Nothing)\n", methodName)
	sb.WriteString("    End Function\n\n")

	// Overload 2: Main implementation with optional timeout and auth headers - delegates to shared utility
	fmt.Fprintf(sb, "    Public Function %s(request As %s, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As %s\n", methodName, inputType, outputType)
	fmt.Fprintf(sb, "        Return _httpUtility.PostJson(Of %s, %s)(%s, request, timeoutMs, authHeaders)\n", inputType, outputType, relativePath)
	sb.WriteString("    End Function\n\n")
}
