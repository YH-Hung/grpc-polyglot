use crate::error::Result;
use crate::types::ProtoFile;
use std::path::{Path, PathBuf};

#[allow(dead_code)] // Traits defined for extensibility

/// Trait for code generators that can produce output from proto files
pub trait CodeGenerator {
    /// Generate code from a proto file and write to the output directory
    fn generate_to_file(&self, proto: &ProtoFile, output_dir: &Path) -> Result<PathBuf>;

    /// Generate code from a proto file and return as a string
    fn generate_code(&self, proto: &ProtoFile) -> Result<String>;

    /// Get the file extension for generated files
    fn file_extension(&self) -> &'static str;

    /// Get a description of what this generator produces
    fn description(&self) -> &'static str;
}

/// Trait for formatters that can format generated code
pub trait CodeFormatter {
    /// Format the given code string
    fn format(&self, code: &str) -> Result<String>;
}

/// Basic no-op formatter
pub struct NoOpFormatter;

impl CodeFormatter for NoOpFormatter {
    fn format(&self, code: &str) -> Result<String> {
        Ok(code.to_string())
    }
}

/// Trait for template engines that can render templates
pub trait TemplateEngine {
    /// Render a template with the given context
    fn render(&self, template: &str, context: &serde_json::Value) -> Result<String>;
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::types::*;

    struct TestGenerator;

    impl CodeGenerator for TestGenerator {
        fn generate_to_file(&self, _proto: &ProtoFile, _output_dir: &Path) -> Result<PathBuf> {
            Ok(PathBuf::from("test.txt"))
        }

        fn generate_code(&self, _proto: &ProtoFile) -> Result<String> {
            Ok("test code".to_string())
        }

        fn file_extension(&self) -> &'static str {
            "txt"
        }

        fn description(&self) -> &'static str {
            "Test generator"
        }
    }

    #[test]
    fn test_code_generator_trait() {
        let generator = TestGenerator;
        assert_eq!(generator.file_extension(), "txt");
        assert_eq!(generator.description(), "Test generator");
    }
}
