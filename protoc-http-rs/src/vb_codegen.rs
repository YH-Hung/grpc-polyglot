use crate::codegen::CodeGenerator;
use crate::error::Result;
use crate::types::*;
use indoc::indoc;
use std::fs;
use std::path::{Path, PathBuf};

/// VB.NET code generator with functional and declarative approach
pub struct VbNetGenerator {
    namespace: Option<String>,
}

impl VbNetGenerator {
    /// Create a new VB.NET generator with optional custom namespace
    pub fn new(namespace: Option<String>) -> Self {
        Self { namespace }
    }

    /// Generate VB.NET imports section
    fn generate_imports(&self) -> String {
        indoc! {"
            Imports System
            Imports System.Net.Http
            Imports System.Text
            Imports System.Threading
            Imports System.Threading.Tasks
            Imports System.Collections.Generic
            Imports Newtonsoft.Json
            "}
        .to_string()
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
        let mut lines = Vec::new();
        let client_name = format!("{}Client", service.name());

        // Class declaration and fields
        lines.extend([
            format!("    Public Class {}", client_name),
            "        Private Shared ReadOnly _http As HttpClient = New HttpClient()".to_string(),
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

        // RPC methods - only unary ones
        for rpc in service.unary_rpcs() {
            lines.extend(self.generate_rpc_methods(rpc, proto));
            lines.push("".to_string());
        }

        lines.push("    End Class".to_string());
        lines.join("\n")
    }

    /// Generate RPC method overloads (with and without cancellation token)
    fn generate_rpc_methods(&self, rpc: &ProtoRpc, proto: &ProtoFile) -> Vec<String> {
        let method_name = format!("{}Async", rpc.name());
        let input_type = rpc.input_type().to_vb_type(proto.package());
        let output_type = rpc.output_type().to_vb_type(proto.package());
        let url_template = self.build_url_template(rpc, proto);

        let mut methods = Vec::new();

        // Overload without cancellation token
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
        ]);

        // Main implementation with cancellation token
        methods.extend([
            format!("        Public Async Function {}(request As {}, cancellationToken As CancellationToken) As Task(Of {})", method_name, input_type, output_type),
            "            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))".to_string(),
            format!("            Dim url As String = String.Format({}, _baseUrl)", url_template),
            "            Dim json As String = JsonConvert.SerializeObject(request)".to_string(),
            "            Using content As New StringContent(json, Encoding.UTF8, \"application/json\")".to_string(),
            "                Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)".to_string(),
            "                If Not response.IsSuccessStatusCode Then".to_string(),
            "                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)".to_string(),
            "                    Throw New HttpRequestException($\"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}\")".to_string(),
            "                End If".to_string(),
            "                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)".to_string(),
            format!("                Return JsonConvert.DeserializeObject(Of {})(respJson)", output_type),
            "            End Using".to_string(),
            "        End Function".to_string(),
        ]);

        methods
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
    fn test_vb_code_generation() {
        let proto = create_test_proto();
        let generator = VbNetGenerator::new(None);

        let code = generator.generate_code(&proto).unwrap();

        // Basic structure tests
        assert!(code.contains("Namespace Helloworld"));
        assert!(code.contains("Public Class HelloRequest"));
        assert!(code.contains("Public Class HelloReply"));
        assert!(code.contains("Public Class GreeterClient"));
        assert!(code.contains("Public Function SayHelloAsync"));

        // VB.NET syntax tests
        assert!(code.contains("TrimEnd(\"/\"c)"));
        assert!(code.contains("/helloworld/say-hello"));
        assert!(code.contains("<JsonProperty(\"name\")>"));
        assert!(code.contains("<JsonProperty(\"message\")>"));
    }

    #[test]
    fn test_custom_namespace() {
        let proto = create_test_proto();
        let generator = VbNetGenerator::new(Some("CustomNamespace".to_string()));

        let code = generator.generate_code(&proto).unwrap();
        assert!(code.contains("Namespace CustomNamespace"));
    }
}
