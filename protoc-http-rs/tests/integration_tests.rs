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

#[test]
fn test_shared_utilities_generation() {
    let output_dir = "tests/output_shared_utilities";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool on complex proto (multiple files)
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

    // Check that shared utility file was generated
    let utility_file = Path::new(output_dir).join("DemoNestedHttpUtility.vb");
    assert!(
        utility_file.exists(),
        "Shared HTTP utility file should exist"
    );

    let utility_content = fs::read_to_string(&utility_file).expect("Failed to read utility file");

    // Verify utility contains shared HTTP logic
    assert!(
        utility_content.contains("Public Class DemoNestedHttpUtility"),
        "Should contain utility class"
    );
    assert!(
        utility_content.contains("PostJsonAsync"),
        "Should contain PostJsonAsync method for NET45"
    );
    assert!(
        utility_content.contains("Namespace DemoNested"),
        "Should have correct namespace"
    );

    // Check that service files use shared utility
    let user_service_file = Path::new(output_dir).join("user-service.vb");
    assert!(user_service_file.exists(), "user-service.vb should exist");

    let user_service_content = fs::read_to_string(&user_service_file).expect("Failed to read user service file");

    // Verify service client uses shared utility
    assert!(
        user_service_content.contains("Private ReadOnly _httpUtility As DemoNestedHttpUtility"),
        "Should use shared utility field"
    );
    assert!(
        user_service_content.contains("_httpUtility = New DemoNestedHttpUtility"),
        "Should initialize shared utility"
    );
    assert!(
        user_service_content.contains("_httpUtility.PostJsonAsync"),
        "Should delegate to shared utility method"
    );

    // Verify service client does NOT contain embedded PostJson function
    assert!(
        !user_service_content.contains("Private Async Function PostJsonAsync"),
        "Should NOT contain embedded PostJson function"
    );

    // Check stock service also uses shared utility
    let stock_service_file = Path::new(output_dir).join("stock-service.vb");
    assert!(stock_service_file.exists(), "stock-service.vb should exist");

    let stock_service_content = fs::read_to_string(&stock_service_file).expect("Failed to read stock service file");

    assert!(
        stock_service_content.contains("_httpUtility.PostJsonAsync"),
        "Stock service should also use shared utility"
    );
}

#[test]
fn test_shared_utilities_net40hwr_mode() {
    let output_dir = "tests/output_shared_net40hwr";
    fs::create_dir_all(output_dir).unwrap();

    // Clean up any existing output
    let _ = fs::remove_dir_all(output_dir);
    fs::create_dir_all(output_dir).unwrap();

    // Run the protoc-http-rs tool with NET40HWR mode
    let output = Command::new("cargo")
        .args(&[
            "run",
            "--",
            "--proto",
            "proto/complex",
            "--out",
            output_dir,
            "--net40hwr",
        ])
        .current_dir(".")
        .output()
        .expect("Failed to execute protoc-http-rs");

    assert!(
        output.status.success(),
        "Command failed: {}",
        String::from_utf8_lossy(&output.stderr)
    );

    // Check that shared utility file was generated for NET40HWR
    let utility_file = Path::new(output_dir).join("DemoNestedHttpUtility.vb");
    assert!(
        utility_file.exists(),
        "NET40HWR shared HTTP utility file should exist"
    );

    let utility_content = fs::read_to_string(&utility_file).expect("Failed to read utility file");

    // Verify NET40HWR utility contains synchronous logic
    assert!(
        utility_content.contains("Public Function PostJson"),
        "Should contain PostJson method (not PostJsonAsync) for NET40HWR"
    );
    assert!(
        !utility_content.contains("PostJsonAsync"),
        "Should NOT contain PostJsonAsync in NET40HWR mode"
    );
    assert!(
        utility_content.contains("HttpWebRequest"),
        "Should use HttpWebRequest for NET40HWR"
    );
    assert!(
        !utility_content.contains("HttpClient"),
        "Should NOT use HttpClient in NET40HWR mode"
    );

    // Check that service files use shared utility with synchronous calls
    let user_service_file = Path::new(output_dir).join("user-service.vb");
    let user_service_content = fs::read_to_string(&user_service_file).expect("Failed to read user service file");

    assert!(
        user_service_content.contains("_httpUtility.PostJson"),
        "Should use synchronous PostJson method"
    );
    assert!(
        !user_service_content.contains("PostJsonAsync"),
        "Should NOT use async methods in NET40HWR mode"
    );
}

#[test]
fn test_single_file_no_shared_utility() {
    let output_dir = "tests/output_single_no_shared";
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

    assert!(output.status.success());

    // Check that NO shared utility file was generated
    let utility_file = Path::new(output_dir).join("HelloworldHttpUtility.vb");
    assert!(
        !utility_file.exists(),
        "Should NOT generate shared utility for single file"
    );

    // Check that service file contains embedded PostJson function
    let helloworld_file = Path::new(output_dir).join("helloworld.vb");
    assert!(helloworld_file.exists(), "helloworld.vb should exist");

    let helloworld_content = fs::read_to_string(&helloworld_file).expect("Failed to read helloworld file");

    // Verify service client uses embedded function
    assert!(
        helloworld_content.contains("Private Async Function PostJsonAsync"),
        "Should contain embedded PostJsonAsync function"
    );
    assert!(
        !helloworld_content.contains("_httpUtility"),
        "Should NOT use shared utility"
    );
    assert!(
        helloworld_content.contains("PostJsonAsync(Of HelloRequest, HelloReply)"),
        "Should call embedded PostJsonAsync directly"
    );
}
