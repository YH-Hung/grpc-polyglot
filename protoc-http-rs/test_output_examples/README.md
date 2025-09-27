# Test Output Examples

This directory contains comprehensive examples of generated VB.NET code demonstrating all features and compatibility modes of protoc-http-rs.

## 📁 Directory Structure

```
test_output_examples/
├── net45/                          # .NET Framework 4.5+ examples
│   ├── helloworld.vb              # Simple service (HttpClient + async/await)
│   └── complex/                    # Complex examples with cross-package types
│       ├── common.vb              # Common types and enums
│       ├── stock-service.vb       # Stock trading service
│       └── user-service.vb        # User management service
├── net40hwr/                       # .NET Framework 4.0 examples  
│   ├── helloworld.vb              # Simple service (HttpWebRequest + synchronous)
│   └── complex/                    # Complex examples with minimal dependencies
│       ├── common.vb              # Common types and enums
│       ├── stock-service.vb       # Stock trading service
│       └── user-service.vb        # User management service
└── versioning/
    └── test_versioned_demo.vb      # RPC versioning demonstration
```

## 🚀 **NET45 Mode Features Demonstrated**

### File: `net45/helloworld.vb`
- **HttpClient Constructor Injection**: `Public Sub New(http As HttpClient, baseUrl As String)`
- **Multiple Method Overloads**:
  - `SayHelloAsync(request)` - Simple overload
  - `SayHelloAsync(request, cancellationToken)` - With cancellation
  - `SayHelloAsync(request, cancellationToken, timeoutMs)` - With timeout
- **Async/Await Patterns**: All methods return `Task(Of T)`
- **CancellationToken Support**: Proper cancellation token handling
- **Timeout Implementation**: Using `CancellationTokenSource` with linked tokens
- **Error Handling**: `HttpRequestException` with detailed error messages
- **Response Validation**: Empty response detection

### File: `net45/complex/user-service.vb`
- **Cross-Package Type References**: `Common.Ticker` type usage
- **Enum Support**: `TradeAction` enum generation
- **Complex Message Types**: Nested properties and lists
- **Multiple Services**: Complete service client generation

## 🔧 **NET40HWR Mode Features Demonstrated**

### File: `net40hwr/helloworld.vb`
- **Simple Constructor**: `Public Sub New(baseUrl As String)` - no dependencies
- **Synchronous Methods**: No async/await, compatible with .NET 4.0
- **Timeout Support**: Using `HttpWebRequest.Timeout` property
- **Method Overloads**:
  - `SayHello(request)` - Simple overload
  - `SayHello(request, timeoutMs)` - With timeout
- **WebException Handling**: Comprehensive error extraction from HTTP responses
- **Resource Disposal**: Nested `Using` statements for proper cleanup
- **Response Validation**: Empty response detection

### File: `net40hwr/complex/user-service.vb`
- **Minimal Dependencies**: Only requires `System.Net` and `Newtonsoft.Json`
- **Synchronous Patterns**: All operations are synchronous
- **Error Handling**: WebException with error response body extraction

## 🏷️ **Versioning Features Demonstrated**

### File: `versioning/test_versioned_demo.vb`
- **Version Extraction**: Automatic extraction from method names
- **URL Generation Examples**:
  - `GetUser` → `/test_versioned_demo/get-user/v1`
  - `GetUserV2` → `/test_versioned_demo/get-user/v2`
  - `GetUserV3` → `/test_versioned_demo/get-user/v3`
  - `ProcessPaymentV10` → `/test_versioned_demo/process-payment/v10`
- **Kebab-Case Conversion**: PascalCase to kebab-case URL transformation
- **Default Versioning**: Methods without explicit version default to v1

## 🎯 **Key Improvements Highlighted**

### **Error Handling**
- **NET45**: `HttpRequestException` with status codes and response bodies
- **NET40HWR**: `WebException` with extracted error details from HTTP responses

### **Timeout Support**
- **NET45**: Optional `timeoutMs` parameter using `CancellationTokenSource`
- **NET40HWR**: Optional `timeoutMs` parameter using `HttpWebRequest.Timeout`

### **Resource Management**
- **NET45**: Proper `Using` statements for `StringContent` and responses
- **NET40HWR**: Comprehensive `Using` blocks for all disposable resources

### **Response Validation**
- Both modes check for empty responses and throw `InvalidOperationException`
- Proper JSON deserialization error handling

## 📋 **Usage Examples**

### NET45 Mode Usage
```vb
' Constructor with HttpClient injection
Dim httpClient As New HttpClient()
Dim client As New GreeterClient(httpClient, "https://api.example.com")

' Simple call
Dim response1 = Await client.SayHelloAsync(request)

' With cancellation token
Dim response2 = Await client.SayHelloAsync(request, cancellationToken)

' With timeout (30 seconds)
Dim response3 = Await client.SayHelloAsync(request, cancellationToken, 30000)
```

### NET40HWR Mode Usage
```vb
' Simple constructor
Dim client As New GreeterClient("https://api.example.com")

' Simple call
Dim response1 = client.SayHello(request)

' With timeout (30 seconds)
Dim response2 = client.SayHello(request, 30000)
```

## 🔍 **Compare Before/After**

These examples demonstrate the significant improvements over previous versions:
- ✅ **Proper HttpClient injection** (vs. shared static HttpClient)
- ✅ **Comprehensive error handling** (vs. basic exceptions)
- ✅ **Optional timeout support** (vs. no timeout control)
- ✅ **Response validation** (vs. no empty response handling)
- ✅ **Resource disposal** (vs. potential leaks)
- ✅ **Multiple method overloads** (vs. single method signature)
- ✅ **RPC versioning support** (vs. basic URL generation)

These examples serve as both documentation and validation that the generated code follows VB.NET and .NET Framework best practices.