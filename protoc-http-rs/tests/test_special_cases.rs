use std::fs;
use std::path::Path;
use std::process::Command;

/// Helper function to extract the content of a specific TOP-LEVEL class from VB.NET code
/// Handles nested classes by counting class/end class pairs
/// Only matches classes at the top level (exactly 4 space indent in Namespace)
fn extract_class_section(content: &str, class_name: &str) -> String {
    // Look for top-level class (indented with EXACTLY 4 spaces in namespace)
    let start_marker = format!("    Public Class {}", class_name);

    let lines: Vec<&str> = content.lines().collect();
    let mut found_start = false;
    let mut depth = 0;
    let mut result_lines = Vec::new();

    for line in lines {
        // Match line that starts with EXACTLY "    Public Class ClassName"
        if !found_start && line == &start_marker {
            found_start = true;
        }

        if found_start {
            result_lines.push(line);

            // Count class declarations (increase depth)
            if line.trim_start().starts_with("Public Class") || line.trim_start().starts_with("Private Class") {
                depth += 1;
            }

            // Count end class (decrease depth)
            if line.trim() == "End Class" {
                depth -= 1;
                if depth == 0 {
                    // Found the matching End Class
                    return result_lines.join("\n");
                }
            }
        }
    }

    String::new()
}

/// Test that msgHdr messages preserve exact field name casing in JSON properties
#[test]
fn test_msghdr_preserves_field_names() {
    let output_dir = "tests/output_msghdr";
    fs::create_dir_all(output_dir).unwrap();
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Generate code
    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/test_special_cases/test_msghdr.proto",
            "--out",
            output_dir,
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let generated_file = Path::new(output_dir).join("test_msghdr.vb");
    assert!(generated_file.exists(), "Generated VB file should exist");
    let content = fs::read_to_string(&generated_file).unwrap();

    // Extract msgHdr class section
    let msghdr_section = extract_class_section(&content, "msgHdr");
    assert!(!msghdr_section.is_empty(), "msgHdr class should exist");

    // Check msgHdr preserves exact casing
    assert!(
        msghdr_section.contains("<JsonProperty(\"userId\")>"),
        "msgHdr should preserve 'userId' not convert to camelCase"
    );
    assert!(
        msghdr_section.contains("<JsonProperty(\"FirstName\")>"),
        "msgHdr should preserve 'FirstName' not convert to 'firstName'"
    );
    assert!(
        msghdr_section.contains("<JsonProperty(\"user_age\")>"),
        "msgHdr should preserve 'user_age' not convert to 'userAge'"
    );
    assert!(
        msghdr_section.contains("<JsonProperty(\"MixedCase_Field\")>"),
        "msgHdr should preserve 'MixedCase_Field'"
    );

    // Extract RegularMessage class section
    let regular_section = extract_class_section(&content, "RegularMessage");
    assert!(
        !regular_section.is_empty(),
        "RegularMessage class should exist"
    );

    // Check RegularMessage uses standard camelCase
    assert!(
        regular_section.contains("<JsonProperty(\"userId\")>"),
        "Regular message should convert 'user_id' to 'userId'"
    );
    assert!(
        regular_section.contains("<JsonProperty(\"firstName\")>"),
        "Regular message should convert 'first_name' to 'firstName'"
    );
    assert!(
        regular_section.contains("<JsonProperty(\"accountNumber\")>"),
        "Regular message should convert 'account_number' to 'accountNumber'"
    );
}

/// Test nested msgHdr messages preserve field names
#[test]
fn test_nested_msghdr_preserves_field_names() {
    let output_dir = "tests/output_msghdr";
    let generated_file = Path::new(output_dir).join("test_msghdr.vb");

    // Generate if doesn't exist
    if !generated_file.exists() {
        fs::create_dir_all(output_dir).unwrap();
        let output = Command::new("cargo")
            .args(&[
                "run",
                "--",
                "--proto",
                "proto/test_special_cases/test_msghdr.proto",
                "--out",
                output_dir,
            ])
            .current_dir(".")
            .output()
            .expect("Failed to execute protoc-http-rs");
        assert!(output.status.success());
    }

    let content = fs::read_to_string(&generated_file).unwrap();

    // The nested msgHdr is defined inside OuterMessage class
    let outer_section = extract_class_section(&content, "OuterMessage");
    assert!(!outer_section.is_empty(), "OuterMessage class should exist");

    // Check nested msgHdr preserves exact field names
    assert!(
        outer_section.contains("<JsonProperty(\"NestedField\")>"),
        "Nested msgHdr should preserve 'NestedField'"
    );
    assert!(
        outer_section.contains("<JsonProperty(\"another_field\")>"),
        "Nested msgHdr should preserve 'another_field'"
    );

    // Check OuterMessage's own fields use standard conversion
    assert!(
        outer_section.contains("<JsonProperty(\"outerField\")>"),
        "OuterMessage should convert 'outer_field' to 'outerField'"
    );
}

/// Test N2 pattern converts to -n2- not -n-2-
#[test]
fn test_n2_converts_to_dash_n2_dash() {
    let output_dir = "tests/output_n2";
    fs::create_dir_all(output_dir).unwrap();
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/test_special_cases/test_n2_kebab.proto",
            "--out",
            output_dir,
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let generated_file = Path::new(output_dir).join("test_n2_kebab.vb");
    let content = fs::read_to_string(&generated_file).unwrap();

    // Check N2 pattern URLs
    assert!(
        content.contains("\"/test_n2_kebab/get-n2-data/v1\"")
            || content.contains("/test_n2_kebab/get-n2-data/v1"),
        "GetN2Data should generate URL with -n2- not -n-2-"
    );
    assert!(
        content.contains("\"/test_n2_kebab/n2-to-n2-sync/v1\"")
            || content.contains("/test_n2_kebab/n2-to-n2-sync/v1"),
        "N2ToN2Sync should handle multiple N2 patterns"
    );
    assert!(
        content.contains("\"/test_n2_kebab/n2-fetch/v1\"")
            || content.contains("/test_n2_kebab/n2-fetch/v1"),
        "N2Fetch should handle N2 at start"
    );

    // Control cases: N3, N1 should still split
    assert!(
        content.contains("\"/test_n2_kebab/get-n-3-data/v1\"")
            || content.contains("/test_n2_kebab/get-n-3-data/v1"),
        "GetN3Data should split to -n-3- (control test)"
    );
    assert!(
        content.contains("\"/test_n2_kebab/get-n-1-data/v1\"")
            || content.contains("/test_n2_kebab/get-n-1-data/v1"),
        "GetN1Data should split to -n-1- (control test)"
    );
}

/// Test proto package overrides CLI namespace
#[test]
fn test_package_overrides_cli_namespace() {
    let output_dir = "tests/output_priority";
    fs::create_dir_all(output_dir).unwrap();
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Pass --namespace CLI arg, but proto has package declaration
    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/test_special_cases/test_namespace_priority.proto",
            "--namespace",
            "IgnoredNamespace", // Should be ignored
            "--out",
            output_dir,
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let generated_file = Path::new(output_dir).join("test_namespace_priority.vb");
    let content = fs::read_to_string(&generated_file).unwrap();

    // Should use proto package "com.example.priority" -> "ComExamplePriority"
    assert!(
        content.contains("Namespace ComExamplePriority"),
        "Should use proto package 'ComExamplePriority', not CLI 'IgnoredNamespace'"
    );
    assert!(
        !content.contains("Namespace IgnoredNamespace"),
        "Should NOT use CLI namespace when proto package exists"
    );
}

/// Test CLI namespace is used when proto has no package
#[test]
fn test_cli_namespace_used_when_no_package() {
    let output_dir = "tests/output_nopackage";
    fs::create_dir_all(output_dir).unwrap();
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/test_special_cases/test_namespace_nopackage.proto",
            "--namespace",
            "FallbackNamespace",
            "--out",
            output_dir,
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let generated_file = Path::new(output_dir).join("test_namespace_nopackage.vb");
    let content = fs::read_to_string(&generated_file).unwrap();

    // Should use CLI namespace since proto has no package
    assert!(
        content.contains("Namespace FallbackNamespace"),
        "Should use CLI namespace 'FallbackNamespace' when proto has no package"
    );
}
