use crate::codegen::CodeGenerator;
use crate::error::Result;
use crate::types::*;
use std::fs;
use std::path::{Path, PathBuf};

/// VB.NET code generator with functional and declarative approach
pub struct VbNetGenerator {
    namespace: Option<String>,
    compat_mode: CompatibilityMode,
}

impl VbNetGenerator {
    /// Create a new VB.NET generator with optional custom namespace and compatibility mode
    pub fn new(namespace: Option<String>, compat_mode: CompatibilityMode) -> Self {
        Self { namespace, compat_mode }
    }

    /// Generate VB.NET imports section based on compatibility mode
    fn generate_imports(&self) -> String {
        let mut imports = vec!["Imports System"];
        
        match self.compat_mode {
            CompatibilityMode::Net45 => {
                imports.extend([
                    "Imports System.Net.Http",
                    "Imports System.Text",
                    "Imports System.Threading",
                    "Imports System.Threading.Tasks",
                    "Imports System.Collections.Generic",
                    "Imports Newtonsoft.Json",
                ]);
            }
            CompatibilityMode::Net40Hwr => {
                imports.extend([
                    "Imports System.Net",
                    "Imports System.IO",
                    "Imports System.Text",
                    "Imports System.Collections.Generic",
                    "Imports Newtonsoft.Json",
                ]);
            }
        }
        
        imports.join("\n") + "\n"
    }

    /// Generate namespace declaration
    fn generate_namespace(&self, proto: &ProtoFile) -> String {
        let default_ns = proto.default_namespace();
        let ns = self.namespace.as_ref().unwrap_or(&default_ns);
        format!("Namespace {}", ns)
    }

    /// Generate enum definitions using functional approach
    fn generate_enums(&self, proto: &ProtoFile) -> String {
        proto
            .enums()
            .values()
            .map(|proto_enum| self.generate_enum(proto_enum))
            .collect::<Vec<_>>()
            .join("\n\n")
    }

    /// Generate a single enum
    fn generate_enum(&self, proto_enum: &ProtoEnum) -> String {
        let enum_name = proto_enum.name();
        let values = proto_enum
            .values()
            .iter()
            .map(|(key, value)| format!("        {} = {}", key, value))
            .collect::<Vec<_>>()
            .join("\n");

        format!("    Public Enum {}\n{}\n    End Enum", enum_name, values)
    }

    /// Generate message definitions using functional approach
    fn generate_messages(&self, proto: &ProtoFile) -> String {
        proto
            .messages()
            .values()
            .map(|message| self.generate_message(message, proto, 1))
            .collect::<Vec<_>>()
            .join("\n\n")
    }

    /// Generate a single message with nested messages
    fn generate_message(
        &self,
        message: &ProtoMessage,
        proto: &ProtoFile,
        indent_level: usize,
    ) -> String {
        let indent = "    ".repeat(indent_level);
        let mut lines = Vec::new();

        // Class declaration
        lines.push(format!("{}Public Class {}", indent, message.name()));

        // Fields as properties
        for field in message.fields() {
            let prop_type = field.field_type().to_vb_type(proto.package());
            let json_name = to_camel_case(field.name().as_str());
            let prop_name = to_pascal_case(field.name().as_str());

            lines.push(format!("{}    <JsonProperty(\"{}\")>", indent, json_name));
            lines.push(format!(
                "{}    Public Property {} As {}",
                indent, prop_name, prop_type
            ));
            lines.push("".to_string());
        }

        // Nested messages
        for nested in message.nested_messages().values() {
            lines.push(self.generate_message(nested, proto, indent_level + 1));
        }

        // End class
        lines.push(format!("{}End Class", indent));

        lines.join("\n")
    }

    /// Generate service client definitions using functional approach
    fn generate_services(&self, proto: &ProtoFile) -> String {
        proto
            .services()
            .iter()
            .map(|service| self.generate_service(service, proto))
            .collect::<Vec<_>>()
            .join("\n\n")
    }

    /// Generate a single service client
    fn generate_service(&self, service: &ProtoService, proto: &ProtoFile) -> String {
        match self.compat_mode {
            CompatibilityMode::Net45 => self.generate_service_net45(service, proto),
            CompatibilityMode::Net40Hwr => self.generate_service_net40hwr(service, proto),
        }
    }

    /// Generate service client for .NET 4.5 mode (HttpClient + async/await)
    fn generate_service_net45(&self, service: &ProtoService, proto: &ProtoFile) -> String {
        let mut lines = Vec::new();
        let client_name = format!("{}Client", service.name());

        // Class declaration and fields
        lines.extend([
            format!("    Public Class {}", client_name),
            "        Private ReadOnly _http As HttpClient".to_string(),
            "        Private ReadOnly _baseUrl As String".to_string(),
            "".to_string(),
        ]);

        // Constructor
        lines.extend([
            "        Public Sub New(http As HttpClient, baseUrl As String)".to_string(),
            "            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))".to_string(),
            "            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")".to_string(),
            "            _http = http".to_string(),
            "            _baseUrl = baseUrl.TrimEnd(\"/\"c)".to_string(),
            "        End Sub".to_string(),
            "".to_string(),
        ]);

        // Shared HTTP helper to reduce duplication
        lines.extend([
            "        Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)".to_string(),
            "            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))".to_string(),
            "            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))".to_string(),
            "            Dim json As String = JsonConvert.SerializeObject(request)".to_string(),
            "            Using content As New StringContent(json, Encoding.UTF8, \"application/json\")".to_string(),
            "                If timeoutMs.HasValue Then".to_string(),
            "                    Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)".to_string(),
            "                        Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)".to_string(),
            "                            Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, combined.Token).ConfigureAwait(False)".to_string(),
            "                            If Not response.IsSuccessStatusCode Then".to_string(),
            "                                Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)".to_string(),
            "                                Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")".to_string(),
            "                            End If".to_string(),
            "                            Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)".to_string(),
            "                            If String.IsNullOrWhiteSpace(respJson) Then".to_string(),
            "                                Throw New InvalidOperationException(\"Received empty response from server\")".to_string(),
            "                            End If".to_string(),
            "                            Return JsonConvert.DeserializeObject(Of TResp)(respJson)".to_string(),
            "                        End Using".to_string(),
            "                    End Using".to_string(),
            "                Else".to_string(),
            "                    Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)".to_string(),
            "                    If Not response.IsSuccessStatusCode Then".to_string(),
            "                        Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)".to_string(),
            "                        Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")".to_string(),
            "                    End If".to_string(),
            "                    Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)".to_string(),
            "                    If String.IsNullOrWhiteSpace(respJson) Then".to_string(),
            "                        Throw New InvalidOperationException(\"Received empty response from server\")".to_string(),
            "                    End If".to_string(),
            "                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)".to_string(),
            "                End If".to_string(),
            "            End Using".to_string(),
            "        End Function".to_string(),
            "".to_string(),
        ]);

        for rpc in service.unary_rpcs() {
            lines.extend(self.generate_rpc_methods_net45(rpc, proto));
            lines.push("".to_string());
        }

        lines.push("    End Class".to_string());
        lines.join("\n")
    }

    /// Generate service client for .NET 4.0 HttpWebRequest mode (synchronous)
    fn generate_service_net40hwr(&self, service: &ProtoService, proto: &ProtoFile) -> String {
        let mut lines = Vec::new();
        let client_name = format!("{}Client", service.name());

        // Class declaration and fields
        lines.extend([
            format!("    Public Class {}", client_name),
            "        Private ReadOnly _baseUrl As String".to_string(),
            "".to_string(),
        ]);

        // Constructor
        lines.extend([
            "        Public Sub New(baseUrl As String)".to_string(),
            "            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")".to_string(),
            "            _baseUrl = baseUrl.TrimEnd(\"/\"c)".to_string(),
            "        End Sub".to_string(),
            "".to_string(),
        ]);

        // Shared HTTP helper (synchronous) to reduce duplication
        lines.extend([
            "        Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing) As TResp".to_string(),
            "            If request Is Nothing Then Throw New ArgumentNullException(\"request\")".to_string(),
            "            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))".to_string(),
            "            Dim json As String = JsonConvert.SerializeObject(request)".to_string(),
            "            Dim data As Byte() = Encoding.UTF8.GetBytes(json)".to_string(),
            "            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)".to_string(),
            "            req.Method = \"POST\"".to_string(),
            "            req.ContentType = \"application/json\"".to_string(),
            "            req.ContentLength = data.Length".to_string(),
            "            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value".to_string(),
            "            Using reqStream As Stream = req.GetRequestStream()".to_string(),
            "                reqStream.Write(data, 0, data.Length)".to_string(),
            "            End Using".to_string(),
            "            Try".to_string(),
            "                Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)".to_string(),
            "                    Using respStream As Stream = resp.GetResponseStream()".to_string(),
            "                        Using reader As New StreamReader(respStream, Encoding.UTF8)".to_string(),
            "                            Dim respJson As String = reader.ReadToEnd()".to_string(),
            "                            If String.IsNullOrWhiteSpace(respJson) Then".to_string(),
            "                                Throw New InvalidOperationException(\"Received empty response from server\")".to_string(),
            "                            End If".to_string(),
            "                            Return JsonConvert.DeserializeObject(Of TResp)(respJson)".to_string(),
            "                        End Using".to_string(),
            "                    End Using".to_string(),
            "                End Using".to_string(),
            "            Catch ex As WebException".to_string(),
            "                If TypeOf ex.Response Is HttpWebResponse Then".to_string(),
            "                    Using errorResp As HttpWebResponse = CType(ex.Response, HttpWebResponse)".to_string(),
            "                        Using errorStream As Stream = errorResp.GetResponseStream()".to_string(),
            "                            If errorStream IsNot Nothing Then".to_string(),
            "                                Using errorReader As New StreamReader(errorStream, Encoding.UTF8)".to_string(),
            "                                    Dim errorBody As String = errorReader.ReadToEnd()".to_string(),
            "                                    Throw New WebException($\"Request failed with status {(CInt(errorResp.StatusCode))} ({errorResp.StatusDescription}): {errorBody}\")".to_string(),
            "                                End Using".to_string(),
            "                            Else".to_string(),
            "                                Throw New WebException($\"Request failed with status {(CInt(errorResp.StatusCode))} ({errorResp.StatusDescription})\")".to_string(),
            "                            End If".to_string(),
            "                        End Using".to_string(),
            "                    End Using".to_string(),
            "                Else".to_string(),
            "                    Throw New WebException($\"Request failed: {ex.Message}\", ex)".to_string(),
            "                End If".to_string(),
            "            End Try".to_string(),
            "        End Function".to_string(),
            "".to_string(),
        ]);

        for rpc in service.unary_rpcs() {
            lines.extend(self.generate_rpc_methods_net40hwr(rpc, proto));
            lines.push("".to_string());
        }

        lines.push("    End Class".to_string());
        lines.join("\n")
    }

    /// Generate RPC method overloads for .NET 4.5 mode (with and without cancellation token)
    fn generate_rpc_methods_net45(&self, rpc: &ProtoRpc, proto: &ProtoFile) -> Vec<String> {
        let method_name = format!("{}Async", rpc.name());
        let input_type = rpc.input_type().to_vb_type(proto.package());
        let output_type = rpc.output_type().to_vb_type(proto.package());
        let relative_path = self.build_relative_path(rpc, proto);

        let mut methods = Vec::new();

        // Overload without cancellation token or timeout
        methods.extend([
            format!(
                "        Public Function {}(request As {}) As Task(Of {})",
                method_name, input_type, output_type
            ),
            format!(
                "            Return {}(request, CancellationToken.None)",
                method_name
            ),
            "        End Function".to_string(),
            "".to_string(),
        ]);

        // Overload with cancellation token but no timeout
        methods.extend([
            format!(
                "        Public Function {}(request As {}, cancellationToken As CancellationToken) As Task(Of {})",
                method_name, input_type, output_type
            ),
            format!(
                "            Return {}(request, cancellationToken, Nothing)",
                method_name
            ),
            "        End Function".to_string(),
            "".to_string(),
        ]);

        // Main implementation with cancellation token and optional timeout
        methods.extend([
            format!("        Public Async Function {}(request As {}, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of {})", method_name, input_type, output_type),
            format!("            Return Await PostJsonAsync(Of {}, {})({}, request, cancellationToken, timeoutMs).ConfigureAwait(False)", input_type, output_type, relative_path),
            "        End Function".to_string(),
        ]);

        methods
    }

    /// Generate RPC methods for .NET 4.0 HttpWebRequest mode (synchronous)
    fn generate_rpc_methods_net40hwr(&self, rpc: &ProtoRpc, proto: &ProtoFile) -> Vec<String> {
        let method_name = rpc.name().to_string();
        let input_type = rpc.input_type().to_vb_type(proto.package());
        let output_type = rpc.output_type().to_vb_type(proto.package());
        let relative_path = self.build_relative_path(rpc, proto);

        vec![
            // Overload without timeout
            format!(
                "        Public Function {}(request As {}) As {}",
                method_name, input_type, output_type
            ),
            format!(
                "            Return {}(request, Nothing)",
                method_name
            ),
            "        End Function".to_string(),
            "".to_string(),
            // Main implementation with optional timeout
            format!(
                "        Public Function {}(request As {}, Optional timeoutMs As Integer? = Nothing) As {}",
                method_name, input_type, output_type
            ),
            format!(
                "            Return PostJson(Of {}, {})({}, request, timeoutMs)",
                input_type, output_type, relative_path
            ),
            "        End Function".to_string(),
        ]
    }

    /// Build URL template for RPC method
    fn build_url_template(&self, rpc: &ProtoRpc, proto: &ProtoFile) -> String {
        let file_stem = Path::new(proto.file_name())
            .file_stem()
            .unwrap_or_default()
            .to_string_lossy();
        let kebab_rpc = rpc.url_name();
        format!("\"{{{}}}/{}/{}\"", "0", file_stem, kebab_rpc)
    }

    /// Build relative path string for RPC method (leading slash)
    fn build_relative_path(&self, rpc: &ProtoRpc, proto: &ProtoFile) -> String {
        let file_stem = Path::new(proto.file_name())
            .file_stem()
            .unwrap_or_default()
            .to_string_lossy();
        let (base_rpc_name, version_seg) = self.split_rpc_name_and_version(rpc.name().as_str());
        let kebab_rpc = crate::types::to_kebab_case(&base_rpc_name);
        format!("\"/{}/{}/{}\"", file_stem, kebab_rpc, version_seg)
    }

    /// Split an RPC method name into (base_name, version_segment).
    /// - If name ends with 'V' followed by digits (e.g., FooV2), returns (Foo, 'v2').
    /// - Otherwise returns (name, 'v1').
    /// The version segment is always lower-case.
    fn split_rpc_name_and_version(&self, name: &str) -> (String, String) {
        if name.is_empty() {
            return (name.to_string(), "v1".to_string());
        }
        
        // Check if name ends with 'V' followed by digits using simple string operations
        let chars: Vec<char> = name.chars().collect();
        if chars.len() >= 2 {
            // Find the last 'V' followed by digits
            for i in (1..chars.len()).rev() {
                if chars[i - 1] == 'V' && chars[i].is_ascii_digit() {
                    // Check if all remaining characters are digits
                    let version_part = &chars[i..];
                    if version_part.iter().all(|c| c.is_ascii_digit()) {
                        let base = chars[..i - 1].iter().collect::<String>();
                        let version = version_part.iter().collect::<String>();
                        if !base.is_empty() {
                            return (base, format!("v{}", version));
                        }
                    }
                }
            }
        }
        
        (name.to_string(), "v1".to_string())
    }
}

impl CodeGenerator for VbNetGenerator {
    fn generate_to_file(&self, proto: &ProtoFile, output_dir: &Path) -> Result<PathBuf> {
        let code = self.generate_code(proto)?;

        fs::create_dir_all(output_dir)?;

        let file_name = Path::new(proto.file_name())
            .file_stem()
            .unwrap_or_default()
            .to_string_lossy();
        let output_file = output_dir.join(format!("{}.vb", file_name));

        fs::write(&output_file, code)?;
        Ok(output_file)
    }

    fn generate_code(&self, proto: &ProtoFile) -> Result<String> {
        let mut sections = Vec::new();

        // Imports
        sections.push(self.generate_imports());

        // Namespace start
        sections.push(self.generate_namespace(proto));
        sections.push("".to_string());

        // Enums
        let enums = self.generate_enums(proto);
        if !enums.is_empty() {
            sections.push(enums);
            sections.push("".to_string());
        }

        // Messages (DTOs)
        let messages = self.generate_messages(proto);
        if !messages.is_empty() {
            sections.push(messages);
            sections.push("".to_string());
        }

        // Services (HTTP clients)
        let services = self.generate_services(proto);
        if !services.is_empty() {
            sections.push(services);
            sections.push("".to_string());
        }

        // Namespace end
        sections.push("End Namespace".to_string());

        Ok(sections.join("\n"))
    }

    fn file_extension(&self) -> &'static str {
        "vb"
    }

    fn description(&self) -> &'static str {
        "VB.NET HTTP proxy client and DTO generator"
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn create_test_proto() -> ProtoFile {
        let hello_request = ProtoMessageBuilder::default()
            .name(Identifier::new("HelloRequest").unwrap())
            .fields(vec![ProtoFieldBuilder::default()
                .name(Identifier::new("name").unwrap())
                .field_type(ProtoType::Scalar(ScalarType::String))
                .field_number(1)
                .build()
                .unwrap()])
            .build()
            .unwrap();

        let hello_reply = ProtoMessageBuilder::default()
            .name(Identifier::new("HelloReply").unwrap())
            .fields(vec![ProtoFieldBuilder::default()
                .name(Identifier::new("message").unwrap())
                .field_type(ProtoType::Scalar(ScalarType::String))
                .field_number(1)
                .build()
                .unwrap()])
            .build()
            .unwrap();

        let say_hello_rpc = ProtoRpcBuilder::default()
            .name(Identifier::new("SayHello").unwrap())
            .input_type(ProtoType::Message {
                name: "HelloRequest".to_string(),
                package: None,
            })
            .output_type(ProtoType::Message {
                name: "HelloReply".to_string(),
                package: None,
            })
            .build()
            .unwrap();

        let greeter_service = ProtoServiceBuilder::default()
            .name(Identifier::new("Greeter").unwrap())
            .rpcs(vec![say_hello_rpc])
            .build()
            .unwrap();

        let mut messages = std::collections::HashMap::new();
        messages.insert("HelloRequest".to_string(), hello_request);
        messages.insert("HelloReply".to_string(), hello_reply);

        ProtoFileBuilder::default()
            .file_name("helloworld.proto".to_string())
            .package(Some(PackageName::new("helloworld").unwrap()))
            .messages(messages)
            .services(vec![greeter_service])
            .build()
            .unwrap()
    }

    #[test]
    fn test_vb_code_generation_net45() {
        let proto = create_test_proto();
        let generator = VbNetGenerator::new(None, CompatibilityMode::Net45);

        let code = generator.generate_code(&proto).unwrap();

        // Basic structure tests
        assert!(code.contains("Namespace Helloworld"));
        assert!(code.contains("Public Class HelloRequest"));
        assert!(code.contains("Public Class HelloReply"));
        assert!(code.contains("Public Class GreeterClient"));
        assert!(code.contains("Public Function SayHelloAsync"));

        // VB.NET syntax tests
        assert!(code.contains("TrimEnd(\"/\"c)"));
        assert!(code.contains("/helloworld/say-hello/v1"));
        assert!(code.contains("<JsonProperty(\"name\")>"));
        assert!(code.contains("<JsonProperty(\"message\")>"));
        
        // HttpClient injection tests (Net45 mode)
        assert!(code.contains("http As HttpClient"));
        assert!(code.contains("If http Is Nothing Then Throw New ArgumentNullException"));
        assert!(code.contains("_http = http"));
        assert!(code.contains("Imports System.Net.Http"));
        assert!(code.contains("Imports System.Threading"));
        
        // Timeout support tests
        assert!(code.contains("Optional timeoutMs As Integer? = Nothing"));
        assert!(code.contains("CancellationTokenSource"));
        
        // Multiple overload tests  
        assert!(code.contains("Public Function SayHelloAsync(request As HelloRequest) As Task(Of HelloReply)"));
        assert!(code.contains("Public Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken) As Task(Of HelloReply)"));
        assert!(code.contains("Public Async Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of HelloReply)"));
        
        // Error handling tests
        assert!(code.contains("HttpRequestException"));
        assert!(code.contains("IsSuccessStatusCode"));
        
        // Response validation tests
        assert!(code.contains("If String.IsNullOrWhiteSpace(respJson) Then"));
        assert!(code.contains("InvalidOperationException"));
    }

    #[test]
    fn test_vb_code_generation_net40hwr() {
        let proto = create_test_proto();
        let generator = VbNetGenerator::new(None, CompatibilityMode::Net40Hwr);

        let code = generator.generate_code(&proto).unwrap();

        // Basic structure tests
        assert!(code.contains("Namespace Helloworld"));
        assert!(code.contains("Public Class HelloRequest"));
        assert!(code.contains("Public Class HelloReply"));
        assert!(code.contains("Public Class GreeterClient"));
        assert!(code.contains("Public Function SayHello(")); // No "Async" suffix

        // VB.NET syntax tests
        assert!(code.contains("TrimEnd(\"/\"c)"));
        assert!(code.contains("/helloworld/say-hello/v1"));
        assert!(code.contains("<JsonProperty(\"name\")>"));
        assert!(code.contains("<JsonProperty(\"message\")>"));
        
        // HttpWebRequest tests (Net40Hwr mode)
        assert!(code.contains("baseUrl As String"));
        assert!(code.contains("HttpWebRequest"));
        assert!(code.contains("Imports System.Net"));
        assert!(code.contains("Imports System.IO"));
        assert!(!code.contains("Imports System.Net.Http"));
        assert!(!code.contains("Imports System.Threading"));
        assert!(!code.contains("CancellationToken"));
        assert!(!code.contains("Async Function"));
        
        // Timeout support tests (Net40Hwr mode)
        assert!(code.contains("Optional timeoutMs As Integer? = Nothing"));
        assert!(code.contains("If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value"));
        
        // Multiple overload tests (Net40Hwr mode)
        assert!(code.contains("Public Function SayHello(request As HelloRequest) As HelloReply"));
        assert!(code.contains("Public Function SayHello(request As HelloRequest, Optional timeoutMs As Integer? = Nothing) As HelloReply"));
        
        // Error handling tests (Net40Hwr mode)
        assert!(code.contains("Catch ex As WebException"));
        assert!(code.contains("Using errorResp As HttpWebResponse"));
        assert!(code.contains("Using errorReader As New StreamReader"));
        
        // Resource disposal tests
        assert!(code.contains("Using resp As HttpWebResponse"));
        assert!(code.contains("Using respStream As Stream"));
        assert!(code.contains("Using reader As New StreamReader"));
        
        // Response validation tests (Net40Hwr mode)
        assert!(code.contains("If String.IsNullOrWhiteSpace(respJson) Then"));
        assert!(code.contains("InvalidOperationException"));
    }

    #[test]
    fn test_custom_namespace() {
        let proto = create_test_proto();
        let generator = VbNetGenerator::new(Some("CustomNamespace".to_string()), CompatibilityMode::Net45);

        let code = generator.generate_code(&proto).unwrap();
        assert!(code.contains("Namespace CustomNamespace"));
    }

    #[test]
    fn test_rpc_version_extraction() {
        let generator = VbNetGenerator::new(None, CompatibilityMode::Net45);
        
        // Test version extraction logic
        assert_eq!(generator.split_rpc_name_and_version("GetUser"), ("GetUser".to_string(), "v1".to_string()));
        assert_eq!(generator.split_rpc_name_and_version("GetUserV2"), ("GetUser".to_string(), "v2".to_string()));
        assert_eq!(generator.split_rpc_name_and_version("GetUserV10"), ("GetUser".to_string(), "v10".to_string()));
        assert_eq!(generator.split_rpc_name_and_version("ProcessPaymentV3"), ("ProcessPayment".to_string(), "v3".to_string()));
        assert_eq!(generator.split_rpc_name_and_version("SimpleMethod"), ("SimpleMethod".to_string(), "v1".to_string()));
        
        // Edge cases
        assert_eq!(generator.split_rpc_name_and_version("V2Method"), ("V2Method".to_string(), "v1".to_string())); // V2 at start
        assert_eq!(generator.split_rpc_name_and_version("MethodV"), ("MethodV".to_string(), "v1".to_string())); // V without number
    }

    #[test] 
    fn test_timeout_parameter_generation() {
        let proto = create_test_proto();
        
        // Test Net45 mode timeout parameters
        let generator_net45 = VbNetGenerator::new(None, CompatibilityMode::Net45);
        let code_net45 = generator_net45.generate_code(&proto).unwrap();
        assert!(code_net45.contains("Optional timeoutMs As Integer? = Nothing"));
        assert!(code_net45.contains("CancellationTokenSource"));
        
        // Test Net40Hwr mode timeout parameters  
        let generator_net40 = VbNetGenerator::new(None, CompatibilityMode::Net40Hwr);
        let code_net40 = generator_net40.generate_code(&proto).unwrap();
        assert!(code_net40.contains("Optional timeoutMs As Integer? = Nothing"));
        assert!(code_net40.contains("req.Timeout = timeoutMs.Value"));
    }
}
