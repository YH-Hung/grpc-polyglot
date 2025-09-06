use crate::error::{Error, Result};
use crate::types::*;
use once_cell::sync::Lazy;
use regex::Regex;
use std::collections::HashMap;
use std::fs;
use std::path::Path;

/// Proto file parser with functional parsing approach
pub struct ProtoParser {
    // Compiled regexes for efficient parsing
    comment_re: Regex,
    whitespace_re: Regex,
    package_re: Regex,
    enum_value_re: Regex,
    field_re: Regex,
    rpc_re: Regex,
}

static BLOCK_KEYWORD_RE: Lazy<Regex> =
    Lazy::new(|| Regex::new(r"\b(\w+)\s+([A-Za-z_][\w]*)\s*\{").unwrap());

impl ProtoParser {
    pub fn new() -> Self {
        Self {
            comment_re: Regex::new(r"//.*").unwrap(),
            whitespace_re: Regex::new(r"\s+").unwrap(),
            package_re: Regex::new(r"\bpackage\s+([a-zA-Z_][\w\.]*)\s*;").unwrap(),
            enum_value_re: Regex::new(r"([A-Za-z_][\w]*)\s*=\s*(\d+)\s*;").unwrap(),
            field_re: Regex::new(r"(repeated\s+)?([A-Za-z_][\w\.]*)\s+([A-Za-z_][\w]*)\s*=\s*(\d+)\s*;").unwrap(),
            rpc_re: Regex::new(r"\brpc\s+([A-Za-z_][\w]*)\s*\(\s*(stream\s+)?([A-Za-z_][\w\.]*)\s*\)\s*returns\s*\(\s*(stream\s+)?([A-Za-z_][\w\.]*)\s*\)\s*\{?\s*\}?").unwrap(),
        }
    }

    /// Parse a proto file from the given path
    pub fn parse_file(&self, proto_path: &Path) -> Result<ProtoFile> {
        let content = fs::read_to_string(proto_path)
            .map_err(|e| Error::parse_error(proto_path, format!("Failed to read file: {e}")))?;

        self.parse_content(&content, proto_path)
    }

    /// Parse proto content with the given file path for error reporting
    pub fn parse_content(&self, content: &str, proto_path: &Path) -> Result<ProtoFile> {
        // Clean and normalize the content
        let cleaned_content = self.preprocess_content(content);

        // Extract package
        let package = self.extract_package(&cleaned_content)?;

        // Parse top-level blocks using functional approach
        let blocks = self.extract_blocks(&cleaned_content);

        let mut messages = HashMap::new();
        let mut enums = HashMap::new();
        let mut services = Vec::new();

        // Process blocks using iterator chains
        for (block_type, name, body) in blocks {
            match block_type.as_str() {
                "message" => {
                    let message = self.parse_message(&name, &body, &[])?;
                    messages.insert(name, message);
                }
                "enum" => {
                    let proto_enum = self.parse_enum(&name, &body)?;
                    enums.insert(name, proto_enum);
                }
                "service" => {
                    let service = self.parse_service(&name, &body)?;
                    services.push(service);
                }
                _ => {} // Ignore unknown blocks
            }
        }

        let file_name = proto_path
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("unknown.proto")
            .to_string();

        ProtoFileBuilder::default()
            .file_name(file_name)
            .package(package)
            .messages(messages)
            .enums(enums)
            .services(services)
            .build()
            .map_err(|e| {
                Error::parse_error(proto_path, format!("Failed to build proto file: {}", e))
            })
    }

    /// Preprocess content by removing comments and normalizing whitespace
    fn preprocess_content(&self, content: &str) -> String {
        let no_comments = self.comment_re.replace_all(content, "");
        self.whitespace_re
            .replace_all(&no_comments, " ")
            .to_string()
    }

    /// Extract package name
    fn extract_package(&self, content: &str) -> Result<Option<PackageName>> {
        self.package_re
            .captures(content)
            .and_then(|caps| caps.get(1))
            .map(|m| PackageName::new(m.as_str()))
            .transpose()
    }

    /// Extract top-level blocks (messages, enums, services) using functional parsing
    fn extract_blocks(&self, content: &str) -> Vec<(String, String, String)> {
        let mut blocks = Vec::new();
        let chars: Vec<char> = content.chars().collect();
        let mut pos = 0;

        while pos < chars.len() {
            if let Some(captures) = BLOCK_KEYWORD_RE.captures(&content[pos..]) {
                let full_match = captures.get(0).unwrap();
                let keyword = captures.get(1).unwrap().as_str().to_string();
                let name = captures.get(2).unwrap().as_str().to_string();

                let brace_start = pos + full_match.end() - 1;

                if let Some(body) = self.extract_balanced_block(&chars, brace_start) {
                    blocks.push((keyword, name, body.clone()));
                    pos = brace_start + body.len() + 2; // Skip past closing brace
                } else {
                    pos += full_match.end();
                }
            } else {
                pos += 1;
            }
        }

        blocks
    }

    /// Extract content between balanced braces
    fn extract_balanced_block(&self, chars: &[char], brace_start: usize) -> Option<String> {
        if brace_start >= chars.len() || chars[brace_start] != '{' {
            return None;
        }

        let mut depth = 1;
        let mut pos = brace_start + 1;

        while pos < chars.len() && depth > 0 {
            match chars[pos] {
                '{' => depth += 1,
                '}' => depth -= 1,
                _ => {}
            }
            pos += 1;
        }

        if depth == 0 {
            Some(chars[(brace_start + 1)..(pos - 1)].iter().collect())
        } else {
            None
        }
    }

    /// Parse a message definition using builder pattern
    fn parse_message(
        &self,
        name: &str,
        body: &str,
        parent_path: &[String],
    ) -> Result<ProtoMessage> {
        let identifier = Identifier::new(name)?;

        // Extract nested messages first
        let nested_blocks = self.extract_blocks(body);
        let nested_messages: HashMap<String, ProtoMessage> = nested_blocks
            .into_iter()
            .filter(|(block_type, _, _)| block_type == "message")
            .map(|(_, nested_name, nested_body)| {
                let mut current_path = parent_path.to_vec();
                current_path.push(name.to_string());
                let nested_msg = self.parse_message(&nested_name, &nested_body, &current_path)?;
                Ok((nested_name, nested_msg))
            })
            .collect::<Result<HashMap<_, _>>>()?;

        // Remove nested message blocks from body for field parsing
        let field_body = self.remove_nested_blocks(body);

        // Parse fields using iterator chain
        let fields: Vec<ProtoField> = self
            .field_re
            .captures_iter(&field_body)
            .map(|caps| self.parse_field_from_captures(caps))
            .collect::<Result<Vec<_>>>()?;

        ProtoMessageBuilder::default()
            .name(identifier)
            .fields(fields)
            .nested_messages(nested_messages)
            .build()
            .map_err(|e| Error::validation_error(format!("Invalid message {}: {}", name, e)))
    }

    /// Remove nested message/enum blocks from content for field parsing
    fn remove_nested_blocks(&self, content: &str) -> String {
        // Simple approach: remove content between braces
        let result = content.to_string();
        let mut depth = 0;
        let mut chars = result.chars().collect::<Vec<_>>();
        let mut i = 0;

        while i < chars.len() {
            match chars[i] {
                '{' => {
                    if depth > 0 {
                        chars[i] = ' '; // Replace with space
                    }
                    depth += 1;
                }
                '}' => {
                    depth -= 1;
                    if depth > 0 {
                        chars[i] = ' '; // Replace with space
                    }
                }
                _ if depth > 0 => {
                    chars[i] = ' '; // Replace with space
                }
                _ => {}
            }
            i += 1;
        }

        chars.into_iter().collect()
    }

    /// Parse a field from regex captures
    fn parse_field_from_captures(&self, caps: regex::Captures) -> Result<ProtoField> {
        let is_repeated = caps.get(1).is_some();
        let type_str = caps.get(2).unwrap().as_str();
        let field_name = caps.get(3).unwrap().as_str();
        let field_number: u32 = caps
            .get(4)
            .unwrap()
            .as_str()
            .parse()
            .map_err(|_| Error::validation_error("Invalid field number"))?;

        let field_type = self.parse_proto_type(type_str, is_repeated)?;

        ProtoFieldBuilder::default()
            .name(Identifier::new(field_name)?)
            .field_type(field_type)
            .field_number(field_number)
            .build()
            .map_err(|e| Error::validation_error(format!("Invalid field {}: {}", field_name, e)))
    }

    /// Parse a proto type from string representation
    fn parse_proto_type(&self, type_str: &str, is_repeated: bool) -> Result<ProtoType> {
        let base_type = if let Ok(scalar) = type_str.parse::<ScalarType>() {
            ProtoType::Scalar(scalar)
        } else if type_str.contains('.') {
            // Qualified type (e.g., "common.Ticker")
            let parts: Vec<&str> = type_str.split('.').collect();
            if parts.len() >= 2 {
                let package_parts = &parts[0..parts.len() - 1];
                let type_name = parts[parts.len() - 1];
                let package = if package_parts.is_empty() {
                    None
                } else {
                    Some(PackageName::new(package_parts.join("."))?)
                };
                // Assume it's a message for now (could be enhanced to detect enums)
                ProtoType::Message {
                    name: type_name.to_string(),
                    package,
                }
            } else {
                return Err(Error::InvalidProtoType {
                    proto_type: type_str.to_string(),
                });
            }
        } else {
            // Unqualified type - assume message in current package
            ProtoType::Message {
                name: type_str.to_string(),
                package: None,
            }
        };

        if is_repeated {
            Ok(ProtoType::Repeated(Box::new(base_type)))
        } else {
            Ok(base_type)
        }
    }

    /// Parse an enum definition
    fn parse_enum(&self, name: &str, body: &str) -> Result<ProtoEnum> {
        let identifier = Identifier::new(name)?;

        let values: HashMap<String, i32> = self
            .enum_value_re
            .captures_iter(body)
            .map(|caps| {
                let key = caps.get(1).unwrap().as_str().to_string();
                let val = caps
                    .get(2)
                    .unwrap()
                    .as_str()
                    .parse::<i32>()
                    .map_err(|_| Error::validation_error("Invalid enum value"))?;
                Ok((key, val))
            })
            .collect::<Result<HashMap<_, _>>>()?;

        ProtoEnumBuilder::default()
            .name(identifier)
            .values(values)
            .build()
            .map_err(|e| Error::validation_error(format!("Invalid enum {}: {}", name, e)))
    }

    /// Parse a service definition
    fn parse_service(&self, name: &str, body: &str) -> Result<ProtoService> {
        let identifier = Identifier::new(name)?;

        let rpcs: Vec<ProtoRpc> = self
            .rpc_re
            .captures_iter(body)
            .map(|caps| {
                let rpc_name = caps.get(1).unwrap().as_str();
                let client_streaming = caps.get(2).is_some();
                let input_type = caps.get(3).unwrap().as_str();
                let server_streaming = caps.get(4).is_some();
                let output_type = caps.get(5).unwrap().as_str();

                let input_proto_type = self.parse_proto_type(input_type, false)?;
                let output_proto_type = self.parse_proto_type(output_type, false)?;

                ProtoRpcBuilder::default()
                    .name(Identifier::new(rpc_name)?)
                    .input_type(input_proto_type)
                    .output_type(output_proto_type)
                    .client_streaming(client_streaming)
                    .server_streaming(server_streaming)
                    .build()
                    .map_err(|e| {
                        Error::validation_error(format!("Invalid RPC {}: {}", rpc_name, e))
                    })
            })
            .collect::<Result<Vec<_>>>()?;

        ProtoServiceBuilder::default()
            .name(identifier)
            .rpcs(rpcs)
            .build()
            .map_err(|e| Error::validation_error(format!("Invalid service {}: {}", name, e)))
    }
}

impl Default for ProtoParser {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::io::Write;
    use tempfile::NamedTempFile;

    #[test]
    fn test_parse_simple_proto() {
        let proto_content = r#"
            syntax = "proto3";
            package helloworld;
            
            message HelloRequest {
                string name = 1;
            }
            
            message HelloReply {
                string message = 1;
            }
            
            service Greeter {
                rpc SayHello (HelloRequest) returns (HelloReply);
            }
        "#;

        let mut temp_file = NamedTempFile::new().unwrap();
        write!(temp_file, "{}", proto_content).unwrap();

        let parser = ProtoParser::new();
        let proto = parser.parse_file(temp_file.path()).unwrap();

        assert_eq!(proto.package().unwrap().as_str(), "helloworld");
        assert_eq!(proto.messages().len(), 2);
        assert!(proto.messages().contains_key("HelloRequest"));
        assert!(proto.messages().contains_key("HelloReply"));
        assert_eq!(proto.services().len(), 1);
        assert_eq!(proto.services()[0].name().as_str(), "Greeter");
    }
}
