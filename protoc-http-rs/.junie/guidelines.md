Project: protoc-http-rs — Dev Guidelines for Contributors

Audience: Experienced Rust developers contributing to this repo.

1) Build and Configuration
- Toolchain: Rust 1.70+ with Cargo. No protoc binary is needed — the project uses a pure-Rust parsing stack (protox + prost-types) to load descriptors.
- Build:
  - Debug: cargo build
  - Release: cargo build --release
  - Binary path: target/release/protoc-http-rs (or target/debug/protoc-http-rs)
- Running the tool:
  - cargo run -- --proto proto/simple --out ./test_output
  - You can pass either a single .proto file or a directory. The program walks directories recursively.
  - Include paths: the directory of each input .proto and the repo’s proto/ directory are automatically added for import resolution.
- CLI options (subset, see --help):
  - --proto <PATH>   Input .proto file or directory (required)
  - --out <DIR>      Output directory for generated .vb files (required)
  - --namespace <VBNamespace>  Optional: override the VB.NET Namespace
- Known warnings: you may see deprecation warnings from prost-types enum conversions in src/parser.rs; these do not affect functionality. Consider migrating to TryFrom<i32> if refactoring parser code.

2) Testing: How to Run, Add, and Verify
- Test strategy:
  - Unit tests live alongside modules in src (e.g., parser/codegen specifics).
  - Integration tests live in tests/. They execute the local binary via cargo run, generate VB.NET output under tests/output*, and assert on emitted source.
- Run all tests:
  - cargo test
- Run only integration tests file:
  - cargo test --test integration_tests
- Determinism:
  - Codegen is expected to be deterministic for a given input set. Integration tests clean and recreate their output directories before each run.
- Temporary outputs used by tests:
  - tests/output, tests/output_complex, tests/output_single, tests/output_custom_ns, tests/output_no_streaming are created/overwritten by tests. Do not commit artifacts from ad‑hoc test runs.

2.1) Adding a New Integration Test (demonstrated and verified)
- Pattern: spawn the binary through Cargo and assert on stdout/stderr and generated files. Example minimal smoke test:

  // File: tests/smoke_guidelines.rs
  use std::process::Command;

  #[test]
  fn smoke_help_runs() {
      let output = Command::new("cargo")
          .args(["run", "--", "--help"]) // run local binary
          .output()
          .expect("failed to spawn cargo run -- --help");

      assert!(output.status.success());
      let stdout = String::from_utf8_lossy(&output.stdout);
      assert!(stdout.contains("--proto"));
      assert!(stdout.contains("--out"));
  }

- How we verified: we created this exact test locally, ran cargo test --test smoke_guidelines to ensure it passes, and then removed the file to keep the repo clean. You can re-create it if needed.

2.2) Adding Tests That Generate Files
- Use std::fs to create a unique output dir under tests/, remove it if it exists, then recreate it before running cargo run.
- Example call pattern used throughout tests:
  Command::new("cargo")
      .args(["run", "--", "--proto", "proto/simple", "--out", "tests/output"]) 
      .current_dir(".")
      .output()?;
- After the run, assert on:
  - Exit status success
  - Presence of expected *.vb files
  - Presence of key strings (namespaces, class names, kebab-case URLs, camelCase JsonProperty names, absence of streaming methods, etc.)

3) Additional Development Notes
- Architecture overview:
  - src/main.rs: CLI wiring using clap; dispatches to parser and codegen.
  - src/parser.rs: Parses .proto via protox to prost-types descriptors; translates descriptors to internal domain types. Import paths are augmented with input dir(s) and repo proto/ for test fixtures. Unary-only assumption is enforced at generation time.
  - src/codegen.rs and src/vb_codegen.rs: Trait-driven generation (CodeGenerator) producing VB.NET DTOs and HTTP proxy client classes. Uses indoc for declarative templates and derive_builder for ergonomics.
  - src/types.rs: Strong domain types with validation (Identifier, PackageName, ProtoType, etc.).
  - src/error.rs: thiserror-based rich error types; functions return Result<_, Error> with contextual messages suitable for CLI surfacing.
- Supported features (relevant to tests and implementations):
  - Unary RPCs only. Any client/server streaming RPCs are parsed but intentionally not emitted in VB.NET output; tests assert the absence of such methods.
  - JSON property names are camelCase; RPC method names in URLs are kebab-case.
  - Cross-package references are qualified in VB with the package namespace (e.g., Common.Ticker).
- Code style:
  - Use rustfmt defaults. Prefer iterator combinators over indexed loops, early returns for error handling, and builders for constructing complex structures.
  - Error handling: prefer anyhow-like context but this project standardizes on thiserror custom variants; propagate with ? and convert external errors into domain errors in parser/codegen layers.
- Adding new proto fixtures:
  - Place under proto/, mirroring package structure if helpful. Tests’ include path handling automatically includes the repo’s proto/ folder and the input .proto’s directory. Avoid relying on protoc; keep descriptors consumable by protox.
- Debugging tips:
  - For failing integration tests, re-run with verbose output to inspect stderr of cargo run invocations. You can also run the binary directly to isolate issues: target/debug/protoc-http-rs --proto <...> --out <...>
  - If descriptor parsing fails, verify import paths and package names; ensure the imported .proto files are under proto/ or siblings of the input files.
  - If you touch parser enum conversions, consider replacing prost-types from_i32 calls with TryFrom<i32> to silence deprecation warnings.

4) Reproducible Local Workflow (tested)
- Clean build: cargo clean && cargo build
- Full test run: cargo test (passes on the current codebase)
- Single test: cargo test --test integration_tests
- Manual smoke: cargo run -- --help

5) Housekeeping
- Integration tests intentionally create and overwrite test output directories under tests/. Keep these out of version control. The repo currently contains expected-output snapshots under tests/output_* used for assertions; do not hand-edit generated files.
- When you add temporary tests (like smoke_guidelines.rs) for experimentation, remove them before opening a PR unless they are intended to remain.
