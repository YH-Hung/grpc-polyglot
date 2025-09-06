use crate::error::{Error, Result};
use derive_builder::Builder;
use std::collections::HashMap;
use std::fmt;
use std::str::FromStr;

/// Validated identifier for proto elements
#[derive(Debug, Clone, PartialEq, Eq, Hash)]
pub struct Identifier(String);

impl Identifier {
    pub fn new(name: impl Into<String>) -> Result<Self> {
        let name = name.into();
        if name.is_empty() || !name.chars().next().unwrap().is_alphabetic() {
            return Err(Error::InvalidIdentifier { identifier: name });
        }
        if !name.chars().all(|c| c.is_alphanumeric() || c == '_') {
            return Err(Error::InvalidIdentifier { identifier: name });
        }
        Ok(Self(name))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}

impl fmt::Display for Identifier {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

impl FromStr for Identifier {
    type Err = Error;

    fn from_str(s: &str) -> Result<Self> {
        Self::new(s)
    }
}

/// Proto package name with validation
#[derive(Debug, Clone, PartialEq, Eq)]
pub struct PackageName(String);

impl PackageName {
    pub fn new(name: impl Into<String>) -> Result<Self> {
        let name = name.into();
        if name.is_empty() {
            return Err(Error::validation_error("Package name cannot be empty"));
        }

        // Validate package name segments
        for segment in name.split('.') {
            if segment.is_empty() || !segment.chars().next().unwrap().is_alphabetic() {
                return Err(Error::validation_error(format!(
                    "Invalid package segment: {}",
                    segment
                )));
            }
        }

        Ok(Self(name))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }

    /// Convert to VB.NET namespace format
    pub fn to_vb_namespace(&self) -> String {
        self.0
            .replace('.', "_")
            .split('_')
            .map(|part| capitalize(part))
            .collect()
    }
}

impl fmt::Display for PackageName {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.0)
    }
}

/// Proto type with validation and conversion capabilities
#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ProtoType {
    Scalar(ScalarType),
    Message {
        name: String,
        package: Option<PackageName>,
    },
    Enum {
        name: String,
        package: Option<PackageName>,
    },
    Repeated(Box<ProtoType>),
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum ScalarType {
    String,
    Int32,
    Int64,
    UInt32,
    UInt64,
    Bool,
    Float,
    Double,
    Bytes,
}

impl ScalarType {
    pub fn to_vb_type(&self) -> &'static str {
        match self {
            ScalarType::String => "String",
            ScalarType::Int32 => "Integer",
            ScalarType::Int64 => "Long",
            ScalarType::UInt32 => "UInteger",
            ScalarType::UInt64 => "ULong",
            ScalarType::Bool => "Boolean",
            ScalarType::Float => "Single",
            ScalarType::Double => "Double",
            ScalarType::Bytes => "Byte()",
        }
    }
}

impl FromStr for ScalarType {
    type Err = Error;

    fn from_str(s: &str) -> Result<Self> {
        match s {
            "string" => Ok(ScalarType::String),
            "int32" => Ok(ScalarType::Int32),
            "int64" => Ok(ScalarType::Int64),
            "uint32" => Ok(ScalarType::UInt32),
            "uint64" => Ok(ScalarType::UInt64),
            "bool" => Ok(ScalarType::Bool),
            "float" => Ok(ScalarType::Float),
            "double" => Ok(ScalarType::Double),
            "bytes" => Ok(ScalarType::Bytes),
            _ => Err(Error::InvalidProtoType {
                proto_type: s.to_string(),
            }),
        }
    }
}

impl ProtoType {
    pub fn to_vb_type(&self, current_package: Option<&PackageName>) -> String {
        match self {
            ProtoType::Scalar(scalar) => scalar.to_vb_type().to_string(),
            ProtoType::Message { name, package } => {
                self.qualified_name(name, package.as_ref(), current_package)
            }
            ProtoType::Enum { name, package } => {
                self.qualified_name(name, package.as_ref(), current_package)
            }
            ProtoType::Repeated(inner) => {
                format!("List(Of {})", inner.to_vb_type(current_package))
            }
        }
    }

    fn qualified_name(
        &self,
        name: &str,
        package: Option<&PackageName>,
        current_package: Option<&PackageName>,
    ) -> String {
        match (package, current_package) {
            (Some(pkg), Some(current_pkg)) if pkg == current_pkg => name.to_string(),
            (Some(pkg), _) => format!("{}.{}", pkg.to_vb_namespace(), name),
            (None, _) => name.to_string(),
        }
    }
}

/// Proto field with strong typing
#[derive(Debug, Clone, Builder)]
pub struct ProtoField {
    name: Identifier,
    #[builder(setter(into))]
    field_type: ProtoType,
    #[builder(default)]
    field_number: u32,
}

impl ProtoField {
    pub fn name(&self) -> &Identifier {
        &self.name
    }

    pub fn field_type(&self) -> &ProtoType {
        &self.field_type
    }

    pub fn field_number(&self) -> u32 {
        self.field_number
    }
}

/// Proto message with builder pattern
#[derive(Debug, Clone, Builder)]
pub struct ProtoMessage {
    name: Identifier,
    #[builder(default)]
    fields: Vec<ProtoField>,
    #[builder(default)]
    nested_messages: HashMap<String, ProtoMessage>,
}

impl ProtoMessage {
    pub fn name(&self) -> &Identifier {
        &self.name
    }

    pub fn fields(&self) -> &[ProtoField] {
        &self.fields
    }

    pub fn nested_messages(&self) -> &HashMap<String, ProtoMessage> {
        &self.nested_messages
    }
}

/// Proto enum with strong typing
#[derive(Debug, Clone, Builder)]
pub struct ProtoEnum {
    name: Identifier,
    #[builder(default)]
    values: HashMap<String, i32>,
}

impl ProtoEnum {
    pub fn name(&self) -> &Identifier {
        &self.name
    }

    pub fn values(&self) -> &HashMap<String, i32> {
        &self.values
    }
}

/// Proto RPC method
#[derive(Debug, Clone, Builder)]
pub struct ProtoRpc {
    name: Identifier,
    input_type: ProtoType,
    output_type: ProtoType,
    #[builder(default = "false")]
    client_streaming: bool,
    #[builder(default = "false")]
    server_streaming: bool,
}

impl ProtoRpc {
    pub fn name(&self) -> &Identifier {
        &self.name
    }

    pub fn input_type(&self) -> &ProtoType {
        &self.input_type
    }

    pub fn output_type(&self) -> &ProtoType {
        &self.output_type
    }

    pub fn is_unary(&self) -> bool {
        !self.client_streaming && !self.server_streaming
    }

    /// Convert RPC name to kebab-case for URL
    pub fn url_name(&self) -> String {
        to_kebab_case(self.name.as_str())
    }
}

/// Proto service with builder pattern
#[derive(Debug, Clone, Builder)]
pub struct ProtoService {
    name: Identifier,
    #[builder(default)]
    rpcs: Vec<ProtoRpc>,
}

impl ProtoService {
    pub fn name(&self) -> &Identifier {
        &self.name
    }

    pub fn rpcs(&self) -> &[ProtoRpc] {
        &self.rpcs
    }

    /// Get only unary RPCs (no streaming)
    pub fn unary_rpcs(&self) -> impl Iterator<Item = &ProtoRpc> {
        self.rpcs.iter().filter(|rpc| rpc.is_unary())
    }
}

/// Complete proto file representation
#[derive(Debug, Clone, Builder)]
pub struct ProtoFile {
    file_name: String,
    #[builder(default)]
    package: Option<PackageName>,
    #[builder(default)]
    messages: HashMap<String, ProtoMessage>,
    #[builder(default)]
    enums: HashMap<String, ProtoEnum>,
    #[builder(default)]
    services: Vec<ProtoService>,
}

impl ProtoFile {
    pub fn file_name(&self) -> &str {
        &self.file_name
    }

    pub fn package(&self) -> Option<&PackageName> {
        self.package.as_ref()
    }

    pub fn messages(&self) -> &HashMap<String, ProtoMessage> {
        &self.messages
    }

    pub fn enums(&self) -> &HashMap<String, ProtoEnum> {
        &self.enums
    }

    pub fn services(&self) -> &[ProtoService] {
        &self.services
    }

    /// Get the default namespace for this file
    pub fn default_namespace(&self) -> String {
        self.package
            .as_ref()
            .map(|p| p.to_vb_namespace())
            .unwrap_or_else(|| {
                std::path::Path::new(&self.file_name)
                    .file_stem()
                    .unwrap_or_default()
                    .to_string_lossy()
                    .chars()
                    .map(|c| if c.is_alphanumeric() { c } else { '_' })
                    .collect::<String>()
                    .split('_')
                    .map(capitalize)
                    .collect()
            })
    }
}

// Utility functions
fn capitalize(s: &str) -> String {
    let mut chars = s.chars();
    match chars.next() {
        None => String::new(),
        Some(first) => first.to_uppercase().chain(chars.as_str().chars()).collect(),
    }
}

fn to_kebab_case(s: &str) -> String {
    if s.is_empty() {
        return s.to_string();
    }

    // If contains separators, split and re-join lowercased
    if s.contains('_') || s.contains('-') {
        return s
            .split(|c| c == '_' || c == '-')
            .filter(|part| !part.is_empty())
            .map(|part| part.to_lowercase())
            .collect::<Vec<_>>()
            .join("-");
    }

    let mut result = String::new();
    let chars: Vec<char> = s.chars().collect();

    for (i, &ch) in chars.iter().enumerate() {
        if i > 0 && ch.is_uppercase() {
            // Check for acronym patterns
            let prev_upper = i > 0 && chars[i - 1].is_uppercase();
            let next_lower = i + 1 < chars.len() && chars[i + 1].is_lowercase();

            if !prev_upper || next_lower {
                result.push('-');
            }
        } else if i > 0 && ch.is_ascii_digit() && chars[i - 1].is_alphabetic() {
            result.push('-');
        } else if i > 0 && ch.is_alphabetic() && chars[i - 1].is_ascii_digit() {
            result.push('-');
        }

        result.push(ch.to_lowercase().next().unwrap());
    }

    // Clean up multiple dashes using a simple approach
    while result.contains("--") {
        result = result.replace("--", "-");
    }

    result
}

// Conversion utilities
pub fn to_camel_case(name: &str) -> String {
    let parts: Vec<&str> = name.split(|c| c == '_' || c == '-').collect();
    if parts.is_empty() {
        return name.to_string();
    }

    let first = parts[0].to_lowercase();
    let rest: String = parts[1..]
        .iter()
        .filter(|&&part| !part.is_empty())
        .map(|&part| capitalize(part))
        .collect();

    format!("{}{}", first, rest)
}

pub fn to_pascal_case(name: &str) -> String {
    name.split(|c| c == '_' || c == '-')
        .filter(|part| !part.is_empty())
        .map(capitalize)
        .collect()
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_identifier_validation() {
        assert!(Identifier::new("valid_name").is_ok());
        assert!(Identifier::new("ValidName").is_ok());
        assert!(Identifier::new("name123").is_ok());

        assert!(Identifier::new("").is_err());
        assert!(Identifier::new("123invalid").is_err());
        assert!(Identifier::new("invalid-name").is_err());
    }

    #[test]
    fn test_kebab_case_conversion() {
        assert_eq!(to_kebab_case("SayHello"), "say-hello");
        assert_eq!(to_kebab_case("GetUserInfo"), "get-user-info");
        assert_eq!(to_kebab_case("ProcessHTTPRequest"), "process-http-request");
        assert_eq!(to_kebab_case("already-kebab"), "already-kebab");
    }

    #[test]
    fn test_package_to_namespace() {
        let pkg = PackageName::new("com.example.api").unwrap();
        assert_eq!(pkg.to_vb_namespace(), "ComExampleApi");
    }
}
