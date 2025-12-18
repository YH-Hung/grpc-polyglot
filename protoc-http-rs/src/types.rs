use crate::error::{Error, Result};
use derive_builder::Builder;
use phf::phf_set;
use std::collections::HashMap;
use std::fmt;
use std::str::FromStr;

/// VB.NET reserved keywords that must be escaped with square brackets when used as identifiers
/// Source: https://learn.microsoft.com/en-us/dotnet/visual-basic/language-reference/keywords/
static VB_RESERVED_KEYWORDS: phf::Set<&'static str> = phf_set! {
    "AddHandler", "AddressOf", "Alias", "And", "AndAlso", "As", "Boolean", "ByRef", "Byte", "ByVal",
    "Call", "Case", "Catch", "CBool", "CByte", "CChar", "CDate", "CDbl", "CDec", "Char", "CInt",
    "Class", "CLng", "CObj", "Const", "Continue", "CSByte", "CShort", "CSng", "CStr", "CType",
    "CUInt", "CULng", "CUShort", "Date", "Decimal", "Declare", "Default", "Delegate", "Dim",
    "DirectCast", "Do", "Double", "Each", "Else", "ElseIf", "End", "EndIf", "Enum", "Erase",
    "Error", "Event", "Exit", "False", "Finally", "For", "Friend", "Function", "Get", "GetType",
    "GetXMLNamespace", "Global", "GoTo", "Handles", "If", "Implements", "Imports", "In", "Inherits",
    "Integer", "Interface", "Is", "IsNot", "Lib", "Like", "Long", "Loop", "Me", "Mod", "Module",
    "MustInherit", "MustOverride", "MyBase", "MyClass", "NameOf", "Namespace", "Narrowing", "New",
    "Next", "Not", "Nothing", "NotInheritable", "NotOverridable", "Object", "Of", "Operator",
    "Option", "Optional", "Or", "OrElse", "Overloads", "Overridable", "Overrides", "ParamArray",
    "Partial", "Private", "Property", "Protected", "Public", "RaiseEvent", "ReadOnly", "ReDim",
    "REM", "RemoveHandler", "Resume", "Return", "SByte", "Select", "Set", "Shadows", "Shared",
    "Short", "Single", "Static", "Step", "Stop", "String", "Structure", "Sub", "SyncLock", "Then",
    "Throw", "To", "True", "Try", "TryCast", "TypeOf", "UInteger", "ULong", "UShort", "Using",
    "When", "While", "Widening", "With", "WithEvents", "WriteOnly", "Xor"
};

/// .NET Framework compatibility mode for generated VB.NET code
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum CompatibilityMode {
    /// Target .NET Framework 4.5+ with HttpClient + async/await
    /// Or .NET 4.0 with Microsoft.Net.Http + Microsoft.Bcl.Async
    Net45,
    /// Target .NET Framework 4.0 with HttpWebRequest (synchronous)
    Net40Hwr,
}

impl Default for CompatibilityMode {
    fn default() -> Self {
        CompatibilityMode::Net45
    }
}

impl CompatibilityMode {
    /// Whether this mode uses HttpClient (true) or HttpWebRequest (false)
    pub fn uses_http_client(self) -> bool {
        matches!(self, CompatibilityMode::Net45)
    }

    /// Whether this mode supports async/await
    pub fn supports_async(self) -> bool {
        matches!(self, CompatibilityMode::Net45)
    }

    /// Get the HTTP client type name for this mode
    pub fn http_client_type(self) -> &'static str {
        match self {
            CompatibilityMode::Net45 => "HttpClient",
            CompatibilityMode::Net40Hwr => "HttpWebRequest",
        }
    }

    /// Get the method suffix for this mode ("Async" for Net45, empty for Net40Hwr)
    pub fn method_suffix(self) -> &'static str {
        match self {
            CompatibilityMode::Net45 => "Async",
            CompatibilityMode::Net40Hwr => "",
        }
    }
}

impl FromStr for CompatibilityMode {
    type Err = Error;

    fn from_str(s: &str) -> Result<Self> {
        match s.to_lowercase().as_str() {
            "net45" => Ok(CompatibilityMode::Net45),
            "net40hwr" | "net40" => Ok(CompatibilityMode::Net40Hwr),
            _ => Err(Error::validation_error(format!(
                "Invalid compatibility mode: {}. Supported modes: net45, net40hwr",
                s
            ))),
        }
    }
}

impl fmt::Display for CompatibilityMode {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        match self {
            CompatibilityMode::Net45 => write!(f, "net45"),
            CompatibilityMode::Net40Hwr => write!(f, "net40hwr"),
        }
    }
}

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
    Sint32,
    Sint64,
    Fixed32,
    Fixed64,
    Sfixed32,
    Sfixed64,
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
            ScalarType::Sint32 => "Integer",
            ScalarType::Sint64 => "Long",
            ScalarType::Fixed32 => "UInteger",
            ScalarType::Fixed64 => "ULong",
            ScalarType::Sfixed32 => "Integer",
            ScalarType::Sfixed64 => "Long",
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
            "sint32" => Ok(ScalarType::Sint32),
            "sint64" => Ok(ScalarType::Sint64),
            "fixed32" => Ok(ScalarType::Fixed32),
            "fixed64" => Ok(ScalarType::Fixed64),
            "sfixed32" => Ok(ScalarType::Sfixed32),
            "sfixed64" => Ok(ScalarType::Sfixed64),
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

    /// Convert RPC name to kebab-case for URL (excluding trailing version suffix like V2)
    pub fn url_name(&self) -> String {
        let base = self.base_name_without_version();
        to_kebab_case(&base)
    }

    /// Extract RPC version from the method name suffix. Examples:
    /// - SayHello -> 1 (default)
    /// - SayHelloV2 -> 2
    /// - SayHelloV10 -> 10
    pub fn version(&self) -> u32 {
        let name = self.name.as_str();
        // Find a trailing pattern V<digits>
        if let Some(pos) = name.rfind('V') {
            if pos + 1 < name.len() {
                let digits = &name[pos + 1..];
                if !digits.is_empty() && digits.chars().all(|c| c.is_ascii_digit()) {
                    if let Ok(n) = digits.parse::<u32>() {
                        return n.max(1);
                    }
                }
            }
        }
        1
    }

    /// Return the base method name with any trailing version suffix removed.
    fn base_name_without_version(&self) -> String {
        let name = self.name.as_str();
        if let Some(pos) = name.rfind('V') {
            if pos + 1 < name.len() {
                let digits = &name[pos + 1..];
                if !digits.is_empty() && digits.chars().all(|c| c.is_ascii_digit()) {
                    return name[..pos].to_string();
                }
            }
        }
        name.to_string()
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

pub fn to_kebab_case(s: &str) -> String {
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

/// Escape VB.NET reserved keywords by wrapping them in square brackets.
///
/// # Arguments
/// * `name` - The identifier name (e.g., property name)
///
/// # Returns
/// The escaped identifier if it's a reserved keyword, otherwise the name unchanged.
///
/// # Examples
/// ```
/// use protoc_http_rs::types::escape_vb_identifier;
/// assert_eq!(escape_vb_identifier("Error"), "[Error]");
/// assert_eq!(escape_vb_identifier("String"), "[String]");
/// assert_eq!(escape_vb_identifier("UserName"), "UserName");
/// ```
pub fn escape_vb_identifier(name: &str) -> String {
    if VB_RESERVED_KEYWORDS.contains(name) {
        format!("[{}]", name)
    } else {
        name.to_string()
    }
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

    #[test]
    fn test_compatibility_mode_parsing() {
        assert_eq!("net45".parse::<CompatibilityMode>().unwrap(), CompatibilityMode::Net45);
        assert_eq!("NET45".parse::<CompatibilityMode>().unwrap(), CompatibilityMode::Net45);
        assert_eq!("net40hwr".parse::<CompatibilityMode>().unwrap(), CompatibilityMode::Net40Hwr);
        assert_eq!("net40".parse::<CompatibilityMode>().unwrap(), CompatibilityMode::Net40Hwr); // Legacy alias
        assert!("invalid".parse::<CompatibilityMode>().is_err());
    }

    #[test]
    fn test_compatibility_mode_properties() {
        let net45 = CompatibilityMode::Net45;
        assert!(net45.uses_http_client());
        assert!(net45.supports_async());
        assert_eq!(net45.method_suffix(), "Async");
        assert_eq!(net45.http_client_type(), "HttpClient");

        let net40hwr = CompatibilityMode::Net40Hwr;
        assert!(!net40hwr.uses_http_client());
        assert!(!net40hwr.supports_async());
        assert_eq!(net40hwr.method_suffix(), "");
        assert_eq!(net40hwr.http_client_type(), "HttpWebRequest");
    }
}
