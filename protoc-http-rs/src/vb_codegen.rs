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
    /// Priority order: 1) Proto package, 2) CLI namespace, 3) Filename-based default
    fn generate_namespace(&self, proto: &ProtoFile) -> String {
        // Priority 1: Proto package (highest priority)
        let ns = if let Some(package) = proto.package() {
            package.to_vb_namespace()
        } else if let Some(custom_ns) = &self.namespace {
            // Priority 2: CLI namespace argument (fallback)
            custom_ns.clone()
        } else {
            // Priority 3: Filename-based default (lowest priority)
            proto.default_namespace()
        };

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

        // Get message name for special logic context
        let message_name = message.name().as_str();

        // Class declaration
        lines.push(format!("{}Public Class {}", indent, message_name));

        // Fields as properties
        for field in message.fields() {
            let prop_type = field.field_type().to_vb_type(proto.package());

            // Use context-aware camelCase conversion
            // Special case: msgHdr messages preserve exact field names
            let json_name = crate::types::to_camel_case_with_context(
                field.name().as_str(),
                Some(message_name)
            );
            let prop_name = crate::types::escape_vb_identifier(&to_pascal_case(field.name().as_str()));

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
            "        Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp".to_string(),
            "            If request Is Nothing Then Throw New ArgumentNullException(\"request\")".to_string(),
            "            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))".to_string(),
            "            Dim json As String = JsonConvert.SerializeObject(request)".to_string(),
            "            Dim data As Byte() = Encoding.UTF8.GetBytes(json)".to_string(),
            "            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)".to_string(),
            "            req.Method = \"POST\"".to_string(),
            "            req.ContentType = \"application/json\"".to_string(),
            "            req.ContentLength = data.Length".to_string(),
            "            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value".to_string(),
            "            ".to_string(),
            "            ' Add authorization headers if provided".to_string(),
            "            If authHeaders IsNot Nothing Then".to_string(),
            "                For Each kvp In authHeaders".to_string(),
            "                    req.Headers.Add(kvp.Key, kvp.Value)".to_string(),
            "                Next".to_string(),
            "            End If".to_string(),
            "            ".to_string(),
            "            Using reqStream As Stream = req.GetRequestStream()".to_string(),
            "                reqStream.Write(data, 0, data.Length)".to_string(),
            "            End Using".to_string(),
            "            Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)".to_string(),
            "                Using respStream As Stream = resp.GetResponseStream()".to_string(),
            "                    Using reader As New StreamReader(respStream, Encoding.UTF8)".to_string(),
            "                        Dim respJson As String = reader.ReadToEnd()".to_string(),
            "                        If String.IsNullOrWhiteSpace(respJson) Then".to_string(),
            "                            Throw New InvalidOperationException(\"Received empty response from server\")".to_string(),
            "                        End If".to_string(),
            "                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)".to_string(),
            "                    End Using".to_string(),
            "                End Using".to_string(),
            "            End Using".to_string(),
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
            // Overload without timeout or auth headers
            format!(
                "        Public Function {}(request As {}) As {}",
                method_name, input_type, output_type
            ),
            format!(
                "            Return {}(request, Nothing, Nothing)",
                method_name
            ),
            "        End Function".to_string(),
            "".to_string(),
            // Main implementation with optional timeout and auth headers
            format!(
                "        Public Function {}(request As {}, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As {}",
                method_name, input_type, output_type
            ),
            format!(
                "            Return PostJson(Of {}, {})({}, request, timeoutMs, authHeaders)",
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
        let version = rpc.version();
        if version > 1 {
            // For versioned RPCs, append the version after the RPC name, e.g., /helloworld/say-hello/v2
            format!("\"{{{}}}/{}/{}/v{}\"", "0", file_stem, kebab_rpc, version)
        } else {
            // keep backward-compatible URL without version segment for v1
            format!("\"{{{}}}/{}/{}\"", "0", file_stem, kebab_rpc)
        }
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

    /// Generate a shared HTTP utility class for multiple proto files in the same directory
    pub fn generate_http_utility(
        utility_name: &str,
        namespace: &str,
        compat_mode: CompatibilityMode,
    ) -> Result<String> {
        let mut sections = Vec::new();

        // Generate imports based on compatibility mode
        let mut imports = vec!["Imports System"];
        match compat_mode {
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
        sections.push(imports.join("\n") + "\n");

        // Namespace start
        sections.push(format!("Namespace {}", namespace));
        sections.push("".to_string());

        // Utility class
        sections.push(format!("    Public Class {}", utility_name));

        match compat_mode {
            CompatibilityMode::Net45 => {
                // NET45 mode - HttpClient with async/await
                sections.extend([
                    "        Private ReadOnly _http As HttpClient".to_string(),
                    "        Private ReadOnly _baseUrl As String".to_string(),
                    "".to_string(),
                    "        Public Sub New(http As HttpClient, baseUrl As String)".to_string(),
                    "            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))".to_string(),
                    "            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")".to_string(),
                    "            _http = http".to_string(),
                    "            _baseUrl = baseUrl.TrimEnd(\"/\"c)".to_string(),
                    "        End Sub".to_string(),
                    "".to_string(),
                    "        Public Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)".to_string(),
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
                ]);
            }
            CompatibilityMode::Net40Hwr => {
                // NET40HWR mode - HttpWebRequest synchronous
                sections.extend([
                    "        Private ReadOnly _baseUrl As String".to_string(),
                    "".to_string(),
                    "        Public Sub New(baseUrl As String)".to_string(),
                    "            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")".to_string(),
                    "            _baseUrl = baseUrl.TrimEnd(\"/\"c)".to_string(),
                    "        End Sub".to_string(),
                    "".to_string(),
                    "        Public Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp".to_string(),
                    "            If request Is Nothing Then Throw New ArgumentNullException(\"request\")".to_string(),
                    "            Dim url As String = String.Format(\"{0}/{1}\", _baseUrl, relativePath.TrimStart(\"/\"c))".to_string(),
                    "            Dim json As String = JsonConvert.SerializeObject(request)".to_string(),
                    "            Dim data As Byte() = Encoding.UTF8.GetBytes(json)".to_string(),
                    "            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)".to_string(),
                    "            req.Method = \"POST\"".to_string(),
                    "            req.ContentType = \"application/json\"".to_string(),
                    "            req.ContentLength = data.Length".to_string(),
                    "            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value".to_string(),
                    "            ".to_string(),
                    "            ' Add authorization headers if provided".to_string(),
                    "            If authHeaders IsNot Nothing Then".to_string(),
                    "                For Each kvp In authHeaders".to_string(),
                    "                    req.Headers.Add(kvp.Key, kvp.Value)".to_string(),
                    "                Next".to_string(),
                    "            End If".to_string(),
                    "            ".to_string(),
                    "            Using reqStream As Stream = req.GetRequestStream()".to_string(),
                    "                reqStream.Write(data, 0, data.Length)".to_string(),
                    "            End Using".to_string(),
                    "            Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)".to_string(),
                    "                Using respStream As Stream = resp.GetResponseStream()".to_string(),
                    "                    Using reader As New StreamReader(respStream, Encoding.UTF8)".to_string(),
                    "                        Dim respJson As String = reader.ReadToEnd()".to_string(),
                    "                        If String.IsNullOrWhiteSpace(respJson) Then".to_string(),
                    "                            Throw New InvalidOperationException(\"Received empty response from server\")".to_string(),
                    "                        End If".to_string(),
                    "                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)".to_string(),
                    "                    End Using".to_string(),
                    "                End Using".to_string(),
                    "            End Using".to_string(),
                    "        End Function".to_string(),
                ]);
            }
        }

        // End class and namespace
        sections.push("    End Class".to_string());
        sections.push("".to_string());
        sections.push("End Namespace".to_string());

        Ok(sections.join("\n"))
    }

    /// Generate service client code that uses a shared utility class
    fn generate_service_with_shared_utility(&self, service: &ProtoService, proto: &ProtoFile, shared_utility_name: &str) -> String {
        match self.compat_mode {
            CompatibilityMode::Net45 => self.generate_service_net45_with_utility(service, proto, shared_utility_name),
            CompatibilityMode::Net40Hwr => self.generate_service_net40hwr_with_utility(service, proto, shared_utility_name),
        }
    }

    /// Generate service client for .NET 4.5 mode using shared utility
    fn generate_service_net45_with_utility(&self, service: &ProtoService, proto: &ProtoFile, shared_utility_name: &str) -> String {
        let mut lines = Vec::new();
        let client_name = format!("{}Client", service.name());

        // Class declaration and fields
        lines.extend([
            format!("    Public Class {}", client_name),
            format!("        Private ReadOnly _httpUtility As {}", shared_utility_name),
            "".to_string(),
        ]);

        // Constructor
        lines.extend([
            "        Public Sub New(http As HttpClient, baseUrl As String)".to_string(),
            "            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))".to_string(),
            "            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")".to_string(),
            format!("            _httpUtility = New {}(http, baseUrl)", shared_utility_name),
            "        End Sub".to_string(),
            "".to_string(),
        ]);

        for rpc in service.unary_rpcs() {
            lines.extend(self.generate_rpc_methods_net45_with_utility(rpc, proto, shared_utility_name));
            lines.push("".to_string());
        }

        lines.push("    End Class".to_string());
        lines.join("\n")
    }

    /// Generate service client for .NET 4.0 HttpWebRequest mode using shared utility
    fn generate_service_net40hwr_with_utility(&self, service: &ProtoService, proto: &ProtoFile, shared_utility_name: &str) -> String {
        let mut lines = Vec::new();
        let client_name = format!("{}Client", service.name());

        // Class declaration and fields
        lines.extend([
            format!("    Public Class {}", client_name),
            format!("        Private ReadOnly _httpUtility As {}", shared_utility_name),
            "".to_string(),
        ]);

        // Constructor
        lines.extend([
            "        Public Sub New(baseUrl As String)".to_string(),
            "            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException(\"baseUrl cannot be null or empty\")".to_string(),
            format!("            _httpUtility = New {}(baseUrl)", shared_utility_name),
            "        End Sub".to_string(),
            "".to_string(),
        ]);

        for rpc in service.unary_rpcs() {
            lines.extend(self.generate_rpc_methods_net40hwr_with_utility(rpc, proto, shared_utility_name));
            lines.push("".to_string());
        }

        lines.push("    End Class".to_string());
        lines.join("\n")
    }

    /// Generate RPC method overloads for .NET 4.5 mode using shared utility
    fn generate_rpc_methods_net45_with_utility(&self, rpc: &ProtoRpc, proto: &ProtoFile, _shared_utility_name: &str) -> Vec<String> {
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

        // Main implementation with cancellation token and optional timeout using shared utility
        methods.extend([
            format!("        Public Async Function {}(request As {}, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of {})", method_name, input_type, output_type),
            format!("            Return Await _httpUtility.PostJsonAsync(Of {}, {})({}, request, cancellationToken, timeoutMs).ConfigureAwait(False)", input_type, output_type, relative_path),
            "        End Function".to_string(),
        ]);

        methods
    }

    /// Generate RPC methods for .NET 4.0 HttpWebRequest mode using shared utility
    fn generate_rpc_methods_net40hwr_with_utility(&self, rpc: &ProtoRpc, proto: &ProtoFile, _shared_utility_name: &str) -> Vec<String> {
        let method_name = rpc.name().to_string();
        let input_type = rpc.input_type().to_vb_type(proto.package());
        let output_type = rpc.output_type().to_vb_type(proto.package());
        let relative_path = self.build_relative_path(rpc, proto);

        vec![
            // Overload without timeout or auth headers
            format!(
                "        Public Function {}(request As {}) As {}",
                method_name, input_type, output_type
            ),
            format!(
                "            Return {}(request, Nothing, Nothing)",
                method_name
            ),
            "        End Function".to_string(),
            "".to_string(),
            // Main implementation with optional timeout and auth headers using shared utility
            format!(
                "        Public Function {}(request As {}, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As {}",
                method_name, input_type, output_type
            ),
            format!(
                "            Return _httpUtility.PostJson(Of {}, {})({}, request, timeoutMs, authHeaders)",
                input_type, output_type, relative_path
            ),
            "        End Function".to_string(),
        ]
    }

    /// Generate VB.NET code with an optional shared utility name
    pub fn generate_code_with_shared_utility(&self, proto: &ProtoFile, shared_utility_name: Option<&str>) -> Result<String> {
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

        // Services (HTTP clients) - use shared utility if available
        let services = if let Some(utility_name) = shared_utility_name {
            proto
                .services()
                .iter()
                .map(|service| self.generate_service_with_shared_utility(service, proto, utility_name))
                .collect::<Vec<_>>()
                .join("\n\n")
        } else {
            self.generate_services(proto)
        };

        if !services.is_empty() {
            sections.push(services);
            sections.push("".to_string());
        }

        // Namespace end
        sections.push("End Namespace".to_string());

        Ok(sections.join("\n"))
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
        assert!(code.contains("Public Function SayHello(request As HelloRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As HelloReply"));

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
        // Test with proto that has NO package - CLI namespace should be used
        let proto_without_package = ProtoFileBuilder::default()
            .file_name("test.proto".to_string())
            .package(None) // No package
            .build()
            .unwrap();

        let generator = VbNetGenerator::new(Some("CustomNamespace".to_string()), CompatibilityMode::Net45);
        let code = generator.generate_code(&proto_without_package).unwrap();
        assert!(code.contains("Namespace CustomNamespace"), "CLI namespace should be used when proto has no package");

        // Test with proto that HAS package - proto package should take priority
        let proto_with_package = create_test_proto(); // Has package "helloworld"
        let code_with_package = generator.generate_code(&proto_with_package).unwrap();
        assert!(code_with_package.contains("Namespace Helloworld"), "Proto package should override CLI namespace");
        assert!(!code_with_package.contains("Namespace CustomNamespace"), "CLI namespace should NOT be used when proto has package");
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
