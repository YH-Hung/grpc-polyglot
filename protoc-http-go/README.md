# protoc-http-vb (refactored from protoc-http-go)

Generate VB.NET HTTP client stubs and DTOs from Protobuf (.proto) files for unary gRPC calls through an HTTP proxy.

What this tool generates:
- VB.NET classes for messages with Newtonsoft.Json attributes using camelCase JSON property names
- Async HTTP client implementations with **HttpClient constructor injection** following .NET Framework best practices
- Unary RPC support (non-streaming) that call a proxy which forwards to gRPC
- Support for enums and nested message types (flattened with underscores like Outer_Inner)
- Works with a single .proto file or recursively with directories

The generated clients communicate with gRPC servers through an HTTP proxy (e.g., grpc-http1-proxy) that converts HTTP POST requests to gRPC calls and returns JSON responses.

---

## Requirements
- Go 1.19+ (to run this generator)
- .NET Framework 4.7.2+ (or compatible) to consume the generated VB code
- Newtonsoft.Json (Json.NET) package referenced by your VB project

## Installation

### Option 1: Build the generator
```bash
git clone <repository>
cd protoc-http-go
go build -o protoc-http-go cmd/protoc-http-go/main.go
```

### Option 2: Run directly
```bash
go run cmd/protoc-http-go/main.go --proto <path> --out <dir> [options]
```

## Usage

### Command Line
```bash
protoc-http-go --proto <path> --out <dir> [--package <namespace>] [--baseurl <url>]
```

Arguments:
- --proto (required): Path to a single .proto file or a directory containing .proto files
- --out   (required): Directory where generated .vb files will be written (created if absent)
- --package (optional): Override VB.NET namespace for generated code
- --baseurl (optional): Base URL for HTTP requests; can also be set in code when constructing clients

### Examples

Generate from a single file:
```bash
# Build first
go build -o protoc-http-go cmd/protoc-http-go/main.go

# Generate from single proto file
./protoc-http-go --proto proto/simple/helloworld.proto --out demo_output

# Or run directly
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out demo_output
```

Generate recursively for a directory:
```bash
./protoc-http-go --proto proto/complex --out generated --package MyCompany.Services
```

Expected output:
- For proto/simple → demo_output/helloworld.vb
- For proto/complex → generated/stock-service.vb, generated/user-service.vb, generated/nested.vb

## HTTP Route Convention (proxy URL)
The HTTP route for each RPC is:
```
{base_url}/{proto file name}/{rpc method name}/{version}
```
Rules:
- RPC method name segment is the version-independent method name in kebab-case.
  - Example: SayHello → say-hello; SayHelloV2 → say-hello
- Version segment must always be present and lowercase.
  - If the RPC name ends with Vx (e.g., V2, V3), that x is the version: v2, v3, ...
  - If no Vx suffix, version defaults to v1.

Example generated call for proto file helloworld.proto and RPC SayHello:
```
POST {BaseUrl}/helloworld/say-hello/v1
Content-Type: application/json
```

## Generated VB.NET Code (example)
Given proto/simple/helloworld.proto, this tool produces a VB file similar to:
```vb
Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization

Namespace Helloworld

' HelloRequest DTO
Public Class HelloRequest
    <JsonProperty("name")>
    Public Property Name As String
End Class

' HelloReply DTO
Public Class HelloReply
    <JsonProperty("message")>
    Public Property Message As String
End Class

' Greeter HTTP client with HttpClient injection
Public Class GreeterClient
    Public Property BaseUrl As String
    Private ReadOnly _httpClient As HttpClient

    Public Sub New(baseUrl As String, httpClient As HttpClient)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        Me.BaseUrl = baseUrl
        Me._httpClient = httpClient
    End Sub

    ' SayHelloAsync calls POST {BaseUrl}/helloworld/say-hello/v1
    Public Async Function SayHelloAsync(request As HelloRequest, Optional cancellationToken As CancellationToken = Nothing) As Task(Of HelloReply)
        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }
        Dim reqJson As String = JsonConvert.SerializeObject(request, settings)
        Dim url As String = Me.BaseUrl & "/helloworld/say-hello/" & "v1"
        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)
            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, "application/json")
            httpRequest.Headers.Accept.Clear()
            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue("application/json"))
            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)
            Dim respBody As String = Await response.Content.ReadAsStringAsync()
            If Not response.IsSuccessStatusCode Then
                Throw New HttpRequestException(String.Format("HTTP request failed with status {0}: {1}", CInt(response.StatusCode), respBody))
            End If
            Dim result As HelloReply = JsonConvert.DeserializeObject(Of HelloReply)(respBody, settings)
            Return result
        End Using
    End Function
End Class

End Namespace
```

## Namespaces and Type Mapping
- Namespace resolution:
  - If --package is provided, it is used verbatim.
  - Else, if the proto declares a package (e.g., foo.bar), each segment is PascalCased and joined with dots: Foo.Bar
  - Else, the file base name is PascalCased and used as the namespace.
- Proto → VB type mapping:
  - string → String; bool → Boolean; bytes → Byte()
  - int32/sint32/sfixed32 → Integer; int64/sint64/sfixed64 → Long
  - uint32/fixed32 → UInteger; uint64/fixed64 → ULong
  - double → Double; float → Single
  - repeated T → List(Of T)

## HTTP proxy assumptions (per requirements)
- There is an HTTP proxy between client and gRPC server that converts HTTP POST with JSON body into gRPC and returns JSON.
- This tool only supports unary RPCs.
- All routes must include a lowercase version segment as described above.

## HttpClient Injection Requirement
The generated VB.NET client classes require HttpClient to be injected through the constructor, following .NET Framework best practices:

```vb
' Create a shared HttpClient instance for the same base URL
Dim sharedHttpClient As New HttpClient()

' Inject it into your client
Dim client As New GreeterClient("https://api.example.com", sharedHttpClient)

' Use the client
Dim request As New HelloRequest() With {.Name = "World"}
Dim response As HelloReply = Await client.SayHelloAsync(request)
```

This pattern allows for proper HttpClient instance sharing and connection pooling, which is crucial for performance in .NET applications.

## Notes on parsing approach (non-functional requirement)
The current implementation uses a lightweight regex-based parser suitable for the subset of proto3 used in the provided samples. For production-grade parsing, a better approach is to:
- Implement a protoc plugin and consume the protobuf descriptor set, or
- Use an existing protobuf AST library to parse .proto files reliably.

This refactor keeps the minimal change surface but documents the recommended direction for robustness.

## Verifying generation
We verified the refactor by generating VB code for the sample proto:
```bash
go run cmd/protoc-http-go/main.go --proto proto/simple/helloworld.proto --out demo_output
# → demo_output/helloworld.vb
```
Open the file to confirm DTOs and client methods are present and the URL ends with /v1 as required.

## Troubleshooting
- Ensure your VB project references Newtonsoft.Json.
- Confirm your HTTP proxy follows the required route format and returns JSON.
- If your proto contains advanced features (oneof, maps, options), they may not be supported yet.

## License
This repository follows the project's license terms.