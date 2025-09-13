use std::fs;
use std::path::Path;
use std::process::Command;

#[test]
fn test_simple_proto_generation() {
    let output_dir = "tests/output";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool on simple proto
    let output = Command::new("cargo")
        .args(&["run", "--", "--proto", "proto/simple", "--out", output_dir])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    // Check that helloworld.vb was generated
    let generated_file = Path::new(output_dir).join("helloworld.vb");
    assert!(generated_file.exists(), "Generated VB file should exist");

    let content = fs::read_to_string(&generated_file).expect("Failed to read generated file");

    // Verify basic structure
    assert!(content.contains("Namespace Helloworld"));
    assert!(content.contains("Public Class HelloRequest"));
    assert!(content.contains("Public Class HelloReply"));
    assert!(content.contains("Public Class GreeterClient"));
    assert!(content.contains("Public Function SayHelloAsync"));

    // Verify proper VB.NET syntax for character literal
    assert!(
        content.contains("TrimEnd(\"/\"c)"),
        "Should use proper VB.NET character literal syntax"
    );

    // Verify kebab-case URL for v1 (no explicit version)
    assert!(
        content.contains("/helloworld/say-hello"),
        "Should use kebab-case for RPC method names"
    );

    // Verify versioned route for V2 method
    assert!(
        content.contains("/helloworld/say-hello/v2"),
        "Should include version segment for V2 RPC routes (trailing)"
    );

    // Verify camelCase JSON properties
    assert!(content.contains("<JsonProperty(\"name\")>"));
    assert!(content.contains("<JsonProperty(\"message\")>"));
}

#[test]
fn test_complex_proto_generation() {
    let output_dir = "tests/output_complex";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool on complex proto
    let output = Command::new("cargo")
        .args(&["run", "--", "--proto", "proto/complex", "--out", output_dir])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    // Check that multiple VB files were generated
    let user_service_file = Path::new(output_dir).join("user-service.vb");
    assert!(user_service_file.exists(), "user-service.vb should exist");

    let content = fs::read_to_string(&user_service_file).expect("Failed to read generated file");

    // Verify namespace and classes
    assert!(content.contains("Namespace User"));
    assert!(content.contains("Public Enum TradeAction"));
    assert!(content.contains("Public Class UserInformation"));
    assert!(content.contains("Public Class Holding"));
    assert!(content.contains("Public Class UserServiceClient"));

    // Verify cross-package references
    assert!(
        content.contains("Common.Ticker"),
        "Should reference types from imported packages with proper namespace qualification"
    );

    // Verify proper type mappings
    assert!(
        content.contains("As Integer"),
        "int32 should map to Integer"
    );
    assert!(content.contains("As String"), "string should map to String");
    assert!(
        content.contains("List(Of Holding)"),
        "repeated fields should map to List(Of T)"
    );
}

#[test]
fn test_single_file_generation() {
    let output_dir = "tests/output_single";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool on single proto file
    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/simple/helloworld.proto",
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

    // Check that only one VB file was generated
    let generated_file = Path::new(output_dir).join("helloworld.vb");
    assert!(generated_file.exists(), "Generated VB file should exist");

    let content = fs::read_to_string(&generated_file).expect("Failed to read generated file");
    assert!(content.contains("Namespace Helloworld"));
}

#[test]
fn test_custom_namespace() {
    let output_dir = "tests/output_custom_ns";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool with custom namespace
    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/simple/helloworld.proto",
            "--out",
            output_dir,
            "--namespace",
            "CustomNamespace",
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    let generated_file = Path::new(output_dir).join("helloworld.vb");
    let content = fs::read_to_string(&generated_file).expect("Failed to read generated file");

    // Verify custom namespace is used
    assert!(
        content.contains("Namespace CustomNamespace"),
        "Should use custom namespace"
    );
}

#[test]
fn test_no_streaming_rpc() {
    let output_dir = "tests/output_no_streaming";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool
    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/simple/helloworld.proto",
            "--out",
            output_dir,
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(output.status.success());

    let generated_file = Path::new(output_dir).join("helloworld.vb");
    let content = fs::read_to_string(&generated_file).expect("Failed to read generated file");

    // Verify only unary RPC methods are generated (SayHello)
    assert!(
        content.contains("SayHelloAsync"),
        "Should contain unary RPC method"
    );

    // Streaming methods should not be generated
    assert!(
        !content.contains("SayHelloStreamReplyAsync"),
        "Should not contain streaming RPC methods"
    );
    assert!(
        !content.contains("SayHelloBidiStreamAsync"),
        "Should not contain streaming RPC methods"
    );
}
