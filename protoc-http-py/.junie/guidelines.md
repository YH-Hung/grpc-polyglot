Project: protoc-http-py — Protobuf to VB.NET DTOs and HTTP client stubs (unary RPC only)

This document captures project-specific build, test, and development notes to accelerate future work on this codebase. It assumes an advanced developer familiar with Python tooling, protoc, and Protobuf descriptors.

1) Build and configuration

- Python/runtime
  - Targeted Python: 3.13+ (per pyproject). The code currently runs on Python 3.9+ for basic functionality using the legacy regex parser if protoc/protobuf are absent, but descriptor-based parsing and CI should use 3.13+.
  - Recommended: Use uv or a modern virtual environment to pin dependencies from pyproject.toml/uv.lock.

- Dependencies
  - Runtime: protobuf>=4.25.0 (only required for descriptor-based parsing; not needed for the legacy regex fallback), protoc on PATH for best accuracy.
  - Dev: pytest>=8.4.2.

- Installing dependencies
  - With uv (preferred if available):
    - uv venv
    - uv pip install -e .
    - uv pip install -r <(uv pip compile --extra dev pyproject.toml)  # or uv pip install pytest
  - With pip:
    - python3 -m venv .venv && source .venv/bin/activate
    - python -m pip install -e .
    - python -m pip install pytest protobuf

- Protoc setup (recommended)
  - Install protoc and ensure it is on PATH. The generator invokes protoc to produce a descriptor set and maps that into VB.NET code.
    - macOS: brew install protobuf
    - Debian/Ubuntu: sudo apt-get install -y protobuf-compiler
    - Windows (Chocolatey): choco install protoc
  - If protoc and/or protobuf are missing, the tool falls back to a regex parser with important limitations (see Development notes).

- Running the tool
  - From repo root (module entry):
    - python -m protoc_http_py.main --proto <file-or-dir> --out <out_dir> [--namespace VB.Namespace]
  - Installed console script:
    - protoc-http-py --proto <file-or-dir> --out <out_dir> [--namespace VB.Namespace]

- Include paths
  - The generator calls protoc with -I set to the proto file’s directory and the repo proto/ directory. If your imports live elsewhere, ensure they are available under those roots or adjust your working directory accordingly.

2) Testing: configuration, running, adding tests

- Test runners
  - pytest is the default. From the project root:
    - pytest
    - python -m pytest
  - A standalone script exists and can be used without pytest:
    - python tests/generation_check.py

- Baseline tests in repo
  - tests/test_generation_check.py delegates to tests/generation_check.py. The script compiles all sample protos (proto/simple and proto/complex) to out_test/ and verifies:
    - CamelCase JSON property naming (JsonProperty attributes using lowerCamelCase).
    - Nested message emission and qualification (Outer.Inner).

- Environment notes verified during preparation of this guide
  - The repository’s generation_check.py ran successfully under Python 3.9 using the legacy regex parser (no protoc and no protobuf installed). Expect warnings that descriptor-based parsing is unavailable.
  - For maximal fidelity (cross-file references, options, etc.), install protoc and protobuf>=4.25.0 to enable descriptor-based parsing.

- Adding a new pytest test (guidelines)
  - Keep tests hermetic. Favor generating into a temporary directory and cleaning up at the end of the test.
  - For generation tests, import generate from protoc_http_py.main and target sample protos under proto/.
  - Example (pytest-style):
    - File: tests/test_smoke_example.py
      - from pathlib import Path
      - import shutil
      - from protoc_http_py.main import generate
      - def test_smoke(tmp_path: Path):
      -     out = tmp_path / "out"
      -     out.mkdir(parents=True, exist_ok=True)
      -     out_path = generate(str(Path("proto/simple/helloworld.proto")), str(out), None)
      -     assert Path(out_path).exists()
      -     text = Path(out_path).read_text(encoding="utf-8")
      -     assert 'JsonProperty("name")' in text
      -     assert 'JsonProperty("message")' in text
  - Running:
    - python -m pytest -q tests/test_smoke_example.py

- Example executed during authoring (without pytest)
  - A temporary smoke test equivalent to the above was executed directly (python) to validate generation and assertions, then removed. You can reproduce with the standalone script approach by cloning the logic from tests/generation_check.py if pytest isn’t available.

3) Development notes and debugging tips

- Architecture overview
  - main.py contains:
    - Descriptor-based parser (preferred): parse_proto_via_descriptor() invokes protoc to emit a descriptor set, then maps it to ProtoFile/Message/Field/Service structures.
    - Legacy regex parser (fallback): parse_proto() which scans .proto text for a constrained subset of syntax. This is used if protoc is missing or protobuf isn’t installed.
    - Code generation: generate_vb() emits VB.NET DTOs and simple HttpClient-based clients for unary RPCs.
    - Naming utilities: to_pascal, to_camel, to_kebab; package_to_vb_namespace; qualify_proto_type; vb_type.

- Namespaces and type resolution
  - VB namespace derives from either --namespace or the .proto package (dots -> underscores, PascalCased). If no package, file name is used.
  - Non-scalar types without dots are treated as local to the file’s namespace.
  - Nested type chains (Outer.Inner) are emitted as nested VB classes; references are auto-qualified (Outer.Inner) when appropriate.
  - Cross-package dotted references (foo.bar.Outer.Inner) map to the VB namespace generated from foo.bar unless the current file’s package matches.

- Services support
  - Only unary RPCs are generated. Streaming RPCs are skipped. Clients call:
    - POST {baseUrl}/{proto-file-name-without-ext}/{rpc-name-in-kebab}

- Known limitations (affect test expectations and contributor changes)
  - Fallback regex parser limitations: no map fields; oneof treated as plain fields; nested enums not emitted; constrained handling of comments/options/extensions. Prefer protoc+descriptors for accurate type graphs across files.
  - Map fields are not supported by the generator (even under descriptors).
  - Custom options/annotations/comments are not propagated to output.

- Debugging and local iteration
  - Use tests/generation_check.py to quickly validate end-to-end generation on bundled protos. It prints a clear success line and fails with assert messages for common regressions (camelCase JSON, nested type qualification).
  - To compare descriptor vs fallback behavior, temporarily install protobuf and ensure protoc is on PATH; rerun generation_check to confirm both paths work.
  - If protoc errors, re-run protoc with the same -I flags that the tool uses (file dir and repo proto/). Verify all imports are resolvable.

- Code style and conventions
  - Python: follow PEP 8. Keep functions small and composable; prefer pure functions for parsing and generation helpers. Use dataclasses for simple data structures (already in use).
  - VB.NET output: Properties use <JsonProperty("lowerCamel")>. Lists are emitted as List(Of T). Nested classes are emitted inline; enums emitted as Public Enum.

- Adding new features safely
  - Extend descriptor mapping first; then provide a compatible fallback in parse_proto() where feasible, or explicitly gate features behind descriptor availability.
  - Update/extend tests/generation_check.py and add focused pytest tests. Prefer tmp_path for isolation; assert on minimal, stable substrings in generated code.
  - Document new flags/semantics in readme.md and here if they affect developer workflows.

- CI suggestions (if/when added)
  - Matrix on Python 3.13 (required) and lowest supported version you choose to keep for fallback-only behavior.
  - Jobs: lint (optional), pytest, and a script step to run tests/generation_check.py. Cache protoc, or install protobuf wheel.

Appendix: Quick commands

- Generate all samples into ./out:
  - python -m protoc_http_py.main --proto proto/simple --out out
  - python -m protoc_http_py.main --proto proto/complex --out out

- Run tests (pytest):
  - python -m pytest -q

- Run standalone generation check (no pytest required):
  - python tests/generation_check.py
