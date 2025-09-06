#![allow(clippy::all, dead_code)] // Suppress clippy warnings during refactoring

use clap::Parser;
use std::path::PathBuf;

mod codegen;
mod error;
mod parser;
mod types;
mod utils;
mod vb_codegen;

use codegen::CodeGenerator;
use error::Result;
use parser::ProtoParser;
use vb_codegen::VbNetGenerator;

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
}

fn main() -> Result<()> {
    let cli = Cli::parse();

    let generator = VbNetGenerator::new(cli.namespace);
    let parser = ProtoParser::new();

    if cli.proto.is_dir() {
        let proto_files = utils::find_proto_files(&cli.proto)?;
        if proto_files.is_empty() {
            println!("No .proto files found under directory: {:?}", cli.proto);
            return Ok(());
        }

        let generated = proto_files
            .into_iter()
            .map(|proto_file| {
                let proto = parser.parse_file(&proto_file)?;
                generator.generate_to_file(&proto, &cli.out)
            })
            .collect::<Result<Vec<_>>>()?;

        println!("Generated:");
        for path in generated {
            println!("{}", path.display());
        }
    } else {
        let proto = parser.parse_file(&cli.proto)?;
        let out_path = generator.generate_to_file(&proto, &cli.out)?;
        println!("Generated: {}", out_path.display());
    }

    Ok(())
}
