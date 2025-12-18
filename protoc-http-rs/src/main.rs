#![allow(clippy::all, dead_code)] // Suppress clippy warnings during refactoring

use clap::Parser;
use std::path::PathBuf;

mod codegen;
mod error;
mod json_schema_codegen;
mod parser;
mod types;
mod utils;
mod vb_codegen;

use codegen::CodeGenerator;
use error::Result;
use parser::ProtoParser;
use types::{CompatibilityMode, ProtoFile};
use vb_codegen::VbNetGenerator;
use std::fs;
use std::collections::HashMap;

#[derive(Parser)]
#[command(name = "protoc-http-rs")]
#[command(about = "Generate VB.NET Http proxy client and DTOs from .proto files (unary RPCs only)")]
struct Cli {
    /// Path to a .proto file or a directory containing .proto files (recursively)
    #[arg(long, required = true)]
    proto: PathBuf,

    /// Output directory for generated .vb file(s)
    #[arg(long, required = true)]
    out: PathBuf,

    /// VB.NET namespace for generated code (defaults to proto package or file name)
    #[arg(long)]
    namespace: Option<String>,

    /// Emit .NET Framework 4.5 compatible VB.NET code (HttpClient + async/await)
    #[arg(long)]
    net45: bool,

    /// Emit .NET Framework 4.0 compatible VB.NET code using synchronous HttpWebRequest (no async/await)
    #[arg(long)]
    net40hwr: bool,

    /// Alias of --net40hwr for backward compatibility
    #[arg(long)]
    net40: bool,
}

/// Generate VB.NET files from multiple proto files with shared utilities when appropriate
fn generate_directory_with_shared_utilities(
    proto_files: Vec<PathBuf>,
    out_dir: &PathBuf,
    namespace: Option<String>,
    compat_mode: CompatibilityMode,
) -> Result<Vec<PathBuf>> {
    if proto_files.is_empty() {
        return Ok(Vec::new());
    }

    let parser = ProtoParser::new();

    // Group proto files by directory
    let mut by_directory: HashMap<PathBuf, Vec<PathBuf>> = HashMap::new();
    for proto_path in proto_files {
        let parent_dir = proto_path.parent().unwrap_or_else(|| std::path::Path::new(".")).to_path_buf();
        by_directory.entry(parent_dir).or_default().push(proto_path);
    }

    let mut all_generated = Vec::new();

    for (_dir_path, files) in by_directory {
        if files.len() > 1 {
            // Multiple files in same directory: generate shared utility

            // Parse all proto files to determine shared utility namespace
            let protos: Result<Vec<ProtoFile>> = files
                .iter()
                .map(|file| parser.parse_file(file))
                .collect();
            let protos = protos?;

            // Use first proto's namespace or provided namespace for utility
            let utility_namespace = if let Some(ns) = &namespace {
                ns.clone()
            } else if let Some(first_proto) = protos.first() {
                first_proto.default_namespace()
            } else {
                "Complex".to_string()
            };

            let utility_name = format!("{}HttpUtility", utility_namespace);

            // Generate shared utility file
            let utility_code = VbNetGenerator::generate_http_utility(
                &utility_name,
                &utility_namespace,
                compat_mode,
            )?;

            fs::create_dir_all(out_dir)?;
            let utility_path = out_dir.join(format!("{}.vb", utility_name));
            fs::write(&utility_path, utility_code)?;
            all_generated.push(utility_path);

            // Generate individual proto files using shared utility
            let generator = VbNetGenerator::new(namespace.clone(), compat_mode);
            for (proto_file, proto) in files.iter().zip(protos.iter()) {
                let out_path = generate_with_shared_utility(&generator, proto, out_dir, &utility_name)?;
                all_generated.push(out_path);
            }
        } else {
            // Single file in directory: generate without shared utility
            let generator = VbNetGenerator::new(namespace.clone(), compat_mode);
            for proto_file in files {
                let proto = parser.parse_file(&proto_file)?;
                let out_path = generator.generate_to_file(&proto, out_dir)?;
                all_generated.push(out_path);
            }
        }
    }

    Ok(all_generated)
}

/// Generate a VB.NET file using a shared utility class
fn generate_with_shared_utility(
    generator: &VbNetGenerator,
    proto: &ProtoFile,
    out_dir: &PathBuf,
    shared_utility_name: &str,
) -> Result<PathBuf> {
    let code = generator.generate_code_with_shared_utility(proto, Some(shared_utility_name))?;

    fs::create_dir_all(out_dir)?;

    let file_name = std::path::Path::new(proto.file_name())
        .file_stem()
        .unwrap_or_default()
        .to_string_lossy();
    let output_file = out_dir.join(format!("{}.vb", file_name));

    fs::write(&output_file, code)?;
    Ok(output_file)
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    // Determine compatibility mode
    let compat_mode = if cli.net40hwr || cli.net40 {
        CompatibilityMode::Net40Hwr
    } else if cli.net45 {
        CompatibilityMode::Net45
    } else {
        CompatibilityMode::default() // Default to Net45
    };

    if cli.proto.is_dir() {
        let proto_files = utils::find_proto_files(&cli.proto)?;
        if proto_files.is_empty() {
            println!("No .proto files found under directory: {:?}", cli.proto);
            return Ok(());
        }

        // Use new directory-based generation with shared utilities
        let generated = generate_directory_with_shared_utilities(
            proto_files.clone(),
            &cli.out,
            cli.namespace,
            compat_mode,
        )?;

        println!("Generated VB.NET:");
        for path in generated {
            println!("  {}", path.display());
        }

        // Generate JSON schemas
        let json_results = json_schema_codegen::generate_json_schemas_for_directory(
            &proto_files,
            &ProtoParser::new(),
            &cli.out,
        );

        let mut json_generated = Vec::new();
        for result in json_results {
            match result {
                Ok(path) => json_generated.push(path),
                Err(e) => eprintln!("Warning: JSON schema generation failed: {}", e),
            }
        }

        if !json_generated.is_empty() {
            println!("\nGenerated JSON Schemas:");
            for path in json_generated {
                println!("  {}", path.display());
            }
        }
    } else {
        let generator = VbNetGenerator::new(cli.namespace, compat_mode);
        let parser = ProtoParser::new();
        let proto = parser.parse_file(&cli.proto)?;
        let out_path = generator.generate_to_file(&proto, &cli.out)?;
        println!("Generated VB.NET: {}", out_path.display());

        // Generate JSON schema
        let json_generator = json_schema_codegen::JsonSchemaGenerator::new();
        match json_generator.generate_to_file(&proto, &cli.out) {
            Ok(json_path) => println!("Generated JSON Schema: {}", json_path.display()),
            Err(e) => eprintln!("Warning: JSON schema generation failed: {}", e),
        }
    }

    Ok(())
}
