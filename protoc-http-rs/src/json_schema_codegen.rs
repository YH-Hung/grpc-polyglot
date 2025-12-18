use crate::error::Result;
use crate::parser::ProtoParser;
use crate::types::{PackageName, ProtoEnum, ProtoFile, ProtoMessage, ProtoType, ScalarType};
use serde_json::{json, Map, Value};
use std::collections::HashMap;
use std::fs;
use std::path::{Path, PathBuf};

pub struct JsonSchemaGenerator;

impl JsonSchemaGenerator {
    pub fn new() -> Self {
        Self
    }

    pub fn generate_to_file(&self, proto: &ProtoFile, output_dir: &Path) -> Result<PathBuf> {
        let json_dir = output_dir.join("json");
        fs::create_dir_all(&json_dir)?;

        let base_name = Path::new(proto.file_name())
            .file_stem()
            .and_then(|s| s.to_str())
            .unwrap_or("unknown");

        let mut description = format!(
            "JSON Schema definitions for all messages and enums in {}",
            proto.file_name()
        );
        if let Some(pkg) = proto.package() {
            description.push_str(&format!(" (package: {})", pkg.as_str()));
        }

        let mut defs = HashMap::new();

        for proto_enum in proto.enums().values() {
            let enum_schema = self.build_enum_schema(proto_enum);
            defs.insert(proto_enum.name().as_str().to_string(), enum_schema);
        }

        for msg in proto.messages().values() {
            self.build_message_schema(msg, &[], &mut defs, proto.package())?;
        }

        let schema_doc = json!({
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": format!("https://example.com/schemas/{}.json", base_name),
            "title": format!("Schemas for {}", proto.file_name()),
            "description": description,
            "$defs": defs
        });

        let json_string = serde_json::to_string_pretty(&schema_doc)?;

        let output_path = json_dir.join(format!("{}.json", base_name));
        fs::write(&output_path, json_string)?;

        Ok(output_path)
    }

    fn scalar_type_to_json_schema(&self, scalar: &ScalarType) -> Value {
        match scalar {
            ScalarType::String => json!({"type": "string"}),
            ScalarType::Int32 => json!({"type": "integer", "format": "int32"}),
            ScalarType::Int64 => json!({"type": "integer", "format": "int64"}),
            ScalarType::UInt32 => json!({"type": "integer", "format": "uint32", "minimum": 0}),
            ScalarType::UInt64 => json!({"type": "integer", "format": "uint64", "minimum": 0}),
            ScalarType::Sint32 => json!({"type": "integer", "format": "int32"}),
            ScalarType::Sint64 => json!({"type": "integer", "format": "int64"}),
            ScalarType::Fixed32 => json!({"type": "integer", "format": "uint32", "minimum": 0}),
            ScalarType::Fixed64 => json!({"type": "integer", "format": "uint64", "minimum": 0}),
            ScalarType::Sfixed32 => json!({"type": "integer", "format": "int32"}),
            ScalarType::Sfixed64 => json!({"type": "integer", "format": "int64"}),
            ScalarType::Bool => json!({"type": "boolean"}),
            ScalarType::Float => json!({"type": "number", "format": "float"}),
            ScalarType::Double => json!({"type": "number", "format": "double"}),
            ScalarType::Bytes => json!({"type": "string", "contentEncoding": "base64"}),
        }
    }

    fn qualify_json_schema_ref(
        &self,
        proto_type: &ProtoType,
        current_pkg: Option<&PackageName>,
    ) -> String {
        match proto_type {
            ProtoType::Scalar(_) => {
                panic!("qualify_json_schema_ref called on scalar type")
            }
            ProtoType::Message { name, package } | ProtoType::Enum { name, package } => {
                match (package, current_pkg) {
                    (Some(pkg), Some(current)) if pkg == current => {
                        format!("#/$defs/{}", name)
                    }
                    (None, _) => {
                        format!("#/$defs/{}", name)
                    }
                    (Some(pkg), _) => {
                        let pkg_parts: Vec<&str> = pkg.as_str().split('.').collect();
                        let file_name = pkg_parts.last().unwrap_or(&"unknown");
                        format!("{}.json#/$defs/{}", file_name, name)
                    }
                }
            }
            ProtoType::Repeated(_) => {
                panic!("qualify_json_schema_ref called on repeated type")
            }
        }
    }

    fn get_json_schema_type(
        &self,
        field_type: &ProtoType,
        current_pkg: Option<&PackageName>,
    ) -> Value {
        match field_type {
            ProtoType::Scalar(scalar) => self.scalar_type_to_json_schema(scalar),
            ProtoType::Repeated(inner) => {
                let items_schema = self.get_json_schema_type(inner, current_pkg);
                json!({
                    "type": "array",
                    "items": items_schema
                })
            }
            ProtoType::Message { .. } | ProtoType::Enum { .. } => {
                json!({
                    "$ref": self.qualify_json_schema_ref(field_type, current_pkg)
                })
            }
        }
    }

    fn build_enum_schema(&self, proto_enum: &ProtoEnum) -> Value {
        let mut enum_values: Vec<String> = proto_enum
            .values()
            .keys()
            .map(|k| k.clone())
            .collect();
        enum_values.sort();

        let descriptions: Vec<String> = enum_values
            .iter()
            .map(|name| {
                let value = proto_enum.values().get(name).unwrap();
                format!("{}={}", name, value)
            })
            .collect();

        json!({
            "type": "string",
            "enum": enum_values,
            "description": format!("Enum values: {}", descriptions.join(", "))
        })
    }

    fn build_message_schema(
        &self,
        msg: &ProtoMessage,
        parent_path: &[String],
        schemas: &mut HashMap<String, Value>,
        current_pkg: Option<&PackageName>,
    ) -> Result<()> {
        let mut current_path = parent_path.to_vec();
        current_path.push(msg.name().as_str().to_string());
        let qualified_name = current_path.join(".");

        let mut properties = Map::new();
        for field in msg.fields() {
            let field_name = to_camel_case(field.name().as_str());
            let field_schema = self.get_json_schema_type(field.field_type(), current_pkg);
            properties.insert(field_name, field_schema);
        }

        let schema = json!({
            "type": "object",
            "properties": properties,
            "additionalProperties": false
        });

        schemas.insert(qualified_name.clone(), schema);

        for nested_msg in msg.nested_messages().values() {
            self.build_message_schema(nested_msg, &current_path, schemas, current_pkg)?;
        }

        Ok(())
    }
}

pub fn generate_json_schemas_for_directory(
    proto_files: &[PathBuf],
    parser: &ProtoParser,
    output_dir: &Path,
) -> Vec<Result<PathBuf>> {
    let generator = JsonSchemaGenerator::new();

    proto_files
        .iter()
        .map(|proto_file| {
            let proto = parser.parse_file(proto_file)?;
            generator.generate_to_file(&proto, output_dir)
        })
        .collect()
}

fn to_camel_case(name: &str) -> String {
    let mut result = String::new();
    let mut capitalize_next = false;

    for (i, c) in name.chars().enumerate() {
        if c == '_' {
            capitalize_next = true;
        } else if i == 0 {
            result.push(c.to_ascii_lowercase());
        } else if capitalize_next {
            result.push(c.to_ascii_uppercase());
            capitalize_next = false;
        } else {
            result.push(c);
        }
    }

    result
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::{Identifier, ProtoEnumBuilder, ProtoFieldBuilder, ProtoMessageBuilder};

    #[test]
    fn test_scalar_type_mapping() {
        let generator = JsonSchemaGenerator::new();

        let string_schema = generator.scalar_type_to_json_schema(&ScalarType::String);
        assert_eq!(string_schema["type"], "string");

        let int32_schema = generator.scalar_type_to_json_schema(&ScalarType::Int32);
        assert_eq!(int32_schema["type"], "integer");
        assert_eq!(int32_schema["format"], "int32");

        let bytes_schema = generator.scalar_type_to_json_schema(&ScalarType::Bytes);
        assert_eq!(bytes_schema["contentEncoding"], "base64");

        let uint32_schema = generator.scalar_type_to_json_schema(&ScalarType::UInt32);
        assert_eq!(uint32_schema["minimum"], 0);
    }

    #[test]
    fn test_enum_schema_generation() {
        let mut values = HashMap::new();
        values.insert("UNKNOWN".to_string(), 0);
        values.insert("ACTIVE".to_string(), 1);
        values.insert("INACTIVE".to_string(), 2);

        let proto_enum = ProtoEnumBuilder::default()
            .name(Identifier::new("Status").unwrap())
            .values(values)
            .build()
            .unwrap();

        let generator = JsonSchemaGenerator::new();
        let schema = generator.build_enum_schema(&proto_enum);

        assert_eq!(schema["type"], "string");
        assert!(schema["enum"].is_array());
        assert!(schema["description"]
            .as_str()
            .unwrap()
            .contains("ACTIVE=1"));
    }

    #[test]
    fn test_reference_qualification() {
        let generator = JsonSchemaGenerator::new();

        let msg_type = ProtoType::Message {
            name: "HelloRequest".to_string(),
            package: None,
        };
        let ref_str = generator.qualify_json_schema_ref(&msg_type, None);
        assert_eq!(ref_str, "#/$defs/HelloRequest");

        let cross_pkg_type = ProtoType::Message {
            name: "Ticker".to_string(),
            package: Some(PackageName::new("common").unwrap()),
        };
        let pkg = PackageName::new("user").unwrap();
        let cross_ref = generator.qualify_json_schema_ref(&cross_pkg_type, Some(&pkg));
        assert_eq!(cross_ref, "common.json#/$defs/Ticker");

        let nested_type = ProtoType::Message {
            name: "Outer.Inner".to_string(),
            package: None,
        };
        let nested_ref = generator.qualify_json_schema_ref(&nested_type, None);
        assert_eq!(nested_ref, "#/$defs/Outer.Inner");
    }

    #[test]
    fn test_repeated_field_handling() {
        let generator = JsonSchemaGenerator::new();

        let repeated_type = ProtoType::Repeated(Box::new(ProtoType::Scalar(ScalarType::String)));

        let schema = generator.get_json_schema_type(&repeated_type, None);
        assert_eq!(schema["type"], "array");
        assert_eq!(schema["items"]["type"], "string");
    }

    #[test]
    fn test_to_camel_case() {
        assert_eq!(to_camel_case("hello_world"), "helloWorld");
        assert_eq!(to_camel_case("user_name"), "userName");
        assert_eq!(to_camel_case("id"), "id");
        assert_eq!(to_camel_case("user_id"), "userId");
        assert_eq!(to_camel_case("some_long_field_name"), "someLongFieldName");
    }

    #[test]
    fn test_message_schema_with_nested() {
        let inner_msg = ProtoMessageBuilder::default()
            .name(Identifier::new("Inner").unwrap())
            .fields(vec![ProtoFieldBuilder::default()
                .name(Identifier::new("value").unwrap())
                .field_type(ProtoType::Scalar(ScalarType::String))
                .field_number(1)
                .build()
                .unwrap()])
            .nested_messages(HashMap::new())
            .build()
            .unwrap();

        let mut nested_messages = HashMap::new();
        nested_messages.insert("Inner".to_string(), inner_msg);

        let outer_msg = ProtoMessageBuilder::default()
            .name(Identifier::new("Outer").unwrap())
            .fields(vec![ProtoFieldBuilder::default()
                .name(Identifier::new("inner_field").unwrap())
                .field_type(ProtoType::Message {
                    name: "Outer.Inner".to_string(),
                    package: None,
                })
                .field_number(1)
                .build()
                .unwrap()])
            .nested_messages(nested_messages)
            .build()
            .unwrap();

        let generator = JsonSchemaGenerator::new();
        let mut schemas = HashMap::new();

        generator
            .build_message_schema(&outer_msg, &[], &mut schemas, None)
            .unwrap();

        assert!(schemas.contains_key("Outer"));
        assert!(schemas.contains_key("Outer.Inner"));

        let outer_schema = &schemas["Outer"];
        let inner_field_schema = &outer_schema["properties"]["innerField"];
        assert_eq!(inner_field_schema["$ref"], "#/$defs/Outer.Inner");
    }
}
