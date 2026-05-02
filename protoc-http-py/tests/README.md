# Test Suite Documentation

## Quick Map

- **tests/test_generation_check.py**: Pytest wrapper with one test, `test_generation_check`, that delegates to `tests/generation_check.py::main()` and expects it to return `True`.
- **tests/generation_check.py**: Integration generation smoke test for `proto/simple` and `proto/complex`. It checks shared utilities, camelCase JSON, versioned routes, embedded vs shared HTTP helpers, nested types, and VB reserved keyword escaping.
- **tests/test_compat_modes.py**: Compatibility mode coverage for default async output, `net45`, `net40hwr`, and the CLI `--net40` alias.
- **tests/test_special_cases.py**: Targeted regression coverage for `msgHdr` field-name preservation, `N2` kebab-case routing, and proto package vs CLI namespace priority.
- **tests/test_bytes_encoding.py**: Bytes-field detection and generated converter helper coverage, including standalone output, shared utility output, cross-namespace converter qualification, descriptor fallback, and runtime encoding selection.
- **tests/generate_variants.py**: Manual comparison utility for generating output variants; this is not a pytest test module.

## Test Case Reference

### tests/test_generation_check.py

| Test case | Covers | Pass means | Fail means |
| --- | --- | --- | --- |
| `test_generation_check` | Calls `generation_check.main()` and asserts it returns `True`. | The broad generated VB.NET integration contract still holds for simple and complex fixtures. | Inspect the failing assertion in `tests/generation_check.py`, because the wrapper only reports the delegated failure. |

### generation_check.py assertions

`tests/generation_check.py` is executed through `tests/test_generation_check.py::test_generation_check`. It writes generated files to `out_test` and performs the detailed checks below before returning `True`.

| Assertion group | Covers | Pass means | Fail means |
| --- | --- | --- | --- |
| `ComplexHttpUtility.vb` shared utility | Confirms the file exists and contains `Public Async Function PostJsonAsync`, `Class ComplexHttpUtility`, and `Namespace DemoNested`. | Directory generation emitted the expected shared async HTTP helper under the namespace chosen from the complex proto package. | Shared utility generation, namespace selection, or async helper emission regressed. |
| `user-service.vb` integration output | Checks `JsonProperty("userId")`, `JsonProperty("totalPrice")`, absence of snake_case JSON names, `/user-service/get-user-information/v1`, `/user-service/trade-stock/v1`, `_httpUtility.PostJsonAsync`, and `ComplexHttpUtility` usage. | Complex service DTOs use camelCase JSON names, versioned routes, and the shared utility instead of embedding HTTP code. | Inspect `out_test/user-service.vb` for route, JSON naming, or shared-helper regressions. |
| `stock-service.vb` integration output | Checks `JsonProperty("ticker")`, `JsonProperty("price")`, `/stock-service/get-stock-price/v1`, and shared utility calls. | Stock service generation still emits expected JSON properties, v1 unary route, and shared utility wiring. | Inspect `out_test/stock-service.vb`; unary route or shared utility behavior changed unexpectedly. |
| `helloworld.vb` simple output | Checks `JsonProperty("name")`, `JsonProperty("message")`, `/helloworld/say-hello/v1`, `/helloworld/say-hello/v2`, embedded `Private Async Function PostJsonAsync`, and no complex shared utility references. | Single-file simple generation keeps embedded HTTP helper behavior and emits both versioned hello routes. | Inspect `out_test/helloworld.vb`; simple generation may have changed route versions or helper placement. |
| `nested.vb` nested type output | Checks nested class emission plus `Outer.Inner` and `List(Of Outer.Inner)` references. | Nested messages are emitted as nested VB classes and referenced with qualified nested type names. | Inspect `out_test/nested.vb`; nested class emission or type reference formatting regressed. |
| `test_vb_reserved_keywords` | Creates a temporary proto with VB reserved keywords, verifies properties are bracket-escaped, and verifies JSON names remain unescaped camelCase strings. | VB identifiers are safe for reserved words while serialized JSON field names remain compatible with proto names. | Inspect `out_test/test_keywords`; identifier escaping or JSON attribute generation changed. |

### tests/test_compat_modes.py

| Test case | Covers | Pass means | Fail means |
| --- | --- | --- | --- |
| `test_generate_default_async` | Default generation emits `HttpClient`, threading/task imports, async `PostJsonAsync`, async service methods, and v1/v2 helloworld routes. | Default compatibility mode remains async and targets the expected route contract. | Inspect the `tmp_path` output for missing async imports, methods, or route strings. |
| `test_generate_net45_async` | `compat="net45"` keeps async `HttpClient` output and allows `NameOf(http)` / `NameOf(request)`. | .NET 4.5 mode still uses the async code path and modern argument validation. | Inspect the `tmp_path` output for accidental downgrade to sync code or lost `NameOf` validation. |
| `test_generate_net40hwr_sync` | `compat="net40hwr"` emits synchronous `HttpWebRequest` / `System.IO` output and excludes `HttpClient`, async functions, and `CancellationToken`. | .NET 4.0 compatibility still avoids async-only APIs and uses synchronous request code. | Inspect the `tmp_path` output for async imports or `HttpClient` references that would break .NET 4.0 targets. |
| `test_cli_alias_net40` | CLI `--net40` returns success, writes `helloworld.vb`, and matches `net40hwr` output expectations. | The command-line alias remains wired to the .NET 4.0 synchronous compatibility mode. | Check CLI stderr/stdout and generated `helloworld.vb`; alias parsing or sync generation changed. |

### tests/test_special_cases.py

| Test case | Covers | Pass means | Fail means |
| --- | --- | --- | --- |
| `test_msghdr_preserves_field_names` | `Public Class msgHdr` keeps exact JSON property names such as `userId`, `FirstName`, and `accountNumber`. | The special `msgHdr` exception still bypasses normal field-name conversion. | Inspect the generated `tmp_path` file; `msgHdr` JSON attributes were converted or omitted. |
| `test_regular_message_uses_camelcase` | Non-`msgHdr` messages in the same fixture still use normal camelCase JSON naming. | The `msgHdr` special case is scoped and does not leak to regular messages. | Inspect the `RegularMessage` class in the generated `tmp_path` file; general camelCase conversion may be broken. |
| `test_nested_msghdr_preserves_field_names` | Nested `msgHdr` keeps exact names while outer regular fields still camelCase. | Recursive message handling applies the `msgHdr` exception only where the nested message name requires it. | Inspect nested class output; recursion or outer-message casing logic regressed. |
| `test_msghdr_json_schema_preserves_fields` | JSON schema `$defs.msgHdr.properties` preserves exact field names; this test is skipped when `google.protobuf` is unavailable. | Descriptor-based schema generation respects the same `msgHdr` field-name exception as VB output. | If not skipped, inspect schema generation for `$defs.msgHdr`; descriptor parsing or schema field naming changed. |
| `test_n2_converts_to_dash_n2_dash` | Generated routes keep `N2` together for `GetN2Data`, `N2ServiceCall`, `FetchN2`, and `N2ToN2Sync`, and never emit `-n-2-`. | URL kebab-case conversion preserves the project-specific `N2` pattern. | Inspect generated route strings; `N2` splitting behavior regressed. |
| `test_n2_unit_conversion` | Directly checks `to_kebab` conversions for `N2` cases and keeps the `N3` control split as `n-3`. | The low-level name converter matches route-generation expectations for both special and control cases. | Fix `to_kebab` before debugging generated files; the unit conversion itself failed. |
| `test_other_patterns_unchanged` | Generated N3 route remains `get-n-3-data/v1`. | The `N2` exception did not broaden to all letter-digit patterns. | Inspect generated route names; the special-case pattern may be too broad. |
| `test_package_overrides_cli_namespace` | Proto package namespace wins over CLI namespace. | Package-derived VB namespaces remain the highest priority when a proto declares `package`. | Inspect generated namespace output; CLI namespace may be incorrectly overriding proto package. |
| `test_cli_namespace_used_when_no_package` | CLI namespace is used as fallback when the proto has no `package`. | Namespace fallback behavior still works for package-less protos. | Inspect the generated temporary proto output; fallback namespace handling regressed. |
| `test_package_to_vb_namespace_function` | Direct unit check for package-to-VB namespace conversion and filename fallback. | Namespace conversion logic produces `ComExampleTest` for packages and `MyService` for filename fallback. | Fix `package_to_vb_namespace` before debugging generated output; the unit conversion itself failed. |

### tests/test_bytes_encoding.py

| Test case | Covers | Pass means | Fail means |
| --- | --- | --- | --- |
| `test_proto_has_bytes_field_true_for_scalar` | Descriptor parsing detects bytes fields in `proto/bytes_test/bytes_only.proto`; skipped when `google.protobuf` is unavailable. | Bytes pre-scan can identify fixtures that require converter helpers. | If not skipped, descriptor parsing or bytes detection failed for an actual bytes field. |
| `test_proto_has_bytes_field_false_for_helloworld` | Descriptor parsing does not produce false positives for `proto/simple/helloworld.proto`; skipped when `google.protobuf` is unavailable. | Non-bytes protos do not trigger bytes helper emission. | If not skipped, bytes detection is too broad and may emit unnecessary helpers. |
| `test_emit_bytes_helpers_contains_required_classes` | Helper emitter includes `ProtoBytesEncoding`, `BytesStringConverter`, `JsonConverter` inheritance, encoding whitelist, and base64 read/write paths. | The generated helper block has the required runtime encoding and base64 conversion surface. | Inspect helper emission in the generator; required converter classes or conversion paths are missing. |
| `test_standalone_proto_emits_helpers_inline` | Standalone bytes proto emits helpers inline and applies converter attributes for scalar, repeated, and nested bytes fields. | Single-file bytes generation is self-contained and converts all bytes-shaped DTO properties. | Inspect the generated `tmp_path` file; inline helpers or `JsonConverter` attributes were not emitted correctly. |
| `test_standalone_proto_without_bytes_skips_helpers` | Standalone non-bytes proto does not emit `BytesStringConverter` or `ProtoBytesEncoding`. | The generator avoids unused helper code for protos without bytes fields. | Inspect the generated `tmp_path` file; bytes helper emission may be unconditional. |
| `test_shared_utility_emits_helpers_once` | Directory generation for `proto/bytes_test/secrets` emits bytes helpers once in the shared utility and references them from DTO files. | Shared utility mode centralizes converter helpers without duplicating them into each DTO file. | Inspect `tmp_path/out_secrets`; helper placement or DTO converter references regressed. |
| `test_shared_utility_no_bytes_skips_helpers` | Complex directory without bytes fields does not include unused bytes helpers in the shared utility. | Shared utility generation keeps non-bytes directories clean. | Inspect `tmp_path/out_complex`; directory pre-scan may be producing false positives. |
| `test_cross_namespace_uses_qualified_converter` | Mixed-package directory qualifies converter type when a DTO namespace differs from the shared utility namespace. | Cross-namespace DTO files can still resolve the shared `BytesStringConverter`. | Inspect generated `alpha.vb`, `beta.vb`, and utility namespace; converter `GetType(...)` qualification is wrong. |
| `test_shared_utility_emits_helpers_when_descriptor_parser_fails` | Regex fallback still detects bytes when descriptor parser fails, preventing missing converter classes. | Directory pre-scan is resilient to descriptor parser failures and still emits helpers when needed. | Inspect `tmp_path/out_fallback`; fallback detection failed or DTOs reference a converter class that was not emitted. |
| `test_converter_uses_default_encoding_at_runtime` | Generated converter reads `ProtoBytesEncoding.Default` at runtime instead of hard-coding encodings. | Consuming apps can change bytes string encoding at runtime. | Inspect the `BytesStringConverter` body; hard-coded encoding strings or missing runtime default access regressed. |

## Running Tests

Run commands from the Python generator directory unless noted otherwise.

### Run All Tests

```bash
cd /Users/yinghanhung/Projects/grpc-polyglot/protoc-http-py
uv run pytest tests/ -v
```

Some tests are guarded by `HAS_PROTOBUF` and are skipped when `google.protobuf` is unavailable. Install/sync the project dependencies if you need those descriptor-based tests to run instead of skip.

### Run Specific Test File

```bash
# Run special cases tests
uv run pytest tests/test_special_cases.py -v

# Run compatibility mode tests
uv run pytest tests/test_compat_modes.py -v

# Run generation check tests
uv run pytest tests/test_generation_check.py -v

# Run bytes encoding tests
uv run pytest tests/test_bytes_encoding.py -v
```

### Run Specific Test Class

```bash
# Run msgHdr tests only
uv run pytest tests/test_special_cases.py::TestMsgHdrSpecialLogic -v

# Run N2 kebab-case tests only
uv run pytest tests/test_special_cases.py::TestN2KebabCaseHandling -v

# Run namespace priority tests only
uv run pytest tests/test_special_cases.py::TestNamespacePriority -v
```

### Run Specific Test Method

```bash
# Run a single special-case test
uv run pytest tests/test_special_cases.py::TestMsgHdrSpecialLogic::test_msghdr_preserves_field_names -v

# Run a single bytes encoding test
uv run pytest tests/test_bytes_encoding.py::test_converter_uses_default_encoding_at_runtime -v

# Run a single compatibility mode test
uv run pytest tests/test_compat_modes.py::test_generate_net40hwr_sync -v
```

### Run with Coverage

```bash
uv run pytest tests/ --cov=protoc_http_py --cov-report=html
```

Coverage reporting requires the relevant pytest-cov dependency if it is not already installed in the environment.

## Test Proto Files

Test proto files are organized by test category.

### Simple Proto Files

Located in `proto/simple/`:

- **helloworld.proto**: Basic service with unary RPCs and versioned endpoints.

### Complex Proto Files

Located in `proto/complex/`:

- **user-service.proto**: Service with cross-package imports and camelCase JSON assertions.
- **stock-service.proto**: Service with streaming RPCs in the fixture; only unary HTTP generation is tested.
- **common/common.proto**: Shared types such as the `Ticker` enum.
- **nested.proto**: Nested message type fixture for `Outer.Inner` references.

### Special Cases Proto Files

Located in `proto/test_special_cases/`:

- **test_msghdr.proto**: `msgHdr` special logic fixture with exact field-name preservation, regular-message camelCase control fields, and nested `msgHdr` coverage.
- **test_n2_kebab.proto**: `N2` kebab-case fixture with `GetN2Data`, `N2ServiceCall`, `FetchN2`, `N2ToN2Sync`, and the `GetN3Data` control case.
- **test_namespace_priority.proto**: Package-defined namespace fixture used to confirm proto package priority over CLI `--namespace`.

### Bytes Proto Files

Located in `proto/bytes_test/`:

- **bytes_only.proto**: Standalone bytes fixture used for scalar, repeated, nested bytes properties, helper emission, and runtime encoding checks.
- **secrets/note-service.proto**: Directory-generation fixture with bytes fields that reference shared converter helpers.
- **secrets/audit-service.proto**: Second bytes directory fixture used with `note-service.proto` to verify helpers are emitted once in the shared utility.

## Adding New Tests

### Test File Structure

```python
import pytest
from pathlib import Path
from protoc_http_py.main import generate

REPO_ROOT = Path(__file__).resolve().parents[1]
PROTO_DIR = REPO_ROOT / "proto" / "your_test_directory"

class TestYourFeature:
    """Test description"""

    def test_your_feature(self, tmp_path):
        """Test method description"""
        proto_path = PROTO_DIR / "your_test.proto"
        out_path = Path(generate(str(proto_path), str(tmp_path), None))
        content = out_path.read_text(encoding='utf-8')

        # Your assertions
        assert 'expected_pattern' in content
```

### Best Practices

1. Use descriptive test method names that explain what is being tested.
2. Use docstrings to document test purpose.
3. Use `tmp_path` fixture for test output directories with automatic cleanup.
4. Test both positive cases, where expected behavior must occur, and negative cases, where forbidden output must not occur.
5. For integration tests, read generated VB.NET and assert on specific patterns.
6. For unit tests, import and test functions directly from `protoc_http_py.main`.
7. Update the relevant `Test Case Reference` row with `Covers`, `Pass means`, and `Fail means` whenever adding or changing a test.

## CI/CD Integration

To integrate tests into a CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Install uv
  uses: astral-sh/setup-uv@v1

- name: Run tests
  run: |
    cd protoc-http-py
    uv run pytest tests/ -v --junit-xml=test-results.xml

- name: Publish test results
  uses: EnricoMi/publish-unit-test-result-action@v2
  if: always()
  with:
    files: protoc-http-py/test-results.xml
```

## Troubleshooting

### Test Failures

- **ImportError**: Ensure `uv` is installed and dependencies are synced with `uv sync`.
- **Missing protobuf**: Tests guarded by `HAS_PROTOBUF` are skipped when `google.protobuf` is unavailable. This affects descriptor-dependent cases in `tests/test_bytes_encoding.py` and `tests/test_special_cases.py`.
- **Path issues**: Use `REPO_ROOT` and relative paths for proto files.
- **Most pytest assertion failures**: Inspect generated VB.NET under the failing test's `tmp_path`. This applies to `tests/test_compat_modes.py`, `tests/test_special_cases.py`, and most `tests/test_bytes_encoding.py` generation tests.
- **`generation_check.py` failures**: Inspect `out_test`, because `tests/generation_check.py` writes to `REPO_ROOT/out_test` rather than a pytest `tmp_path`.
- **Skip behavior**: A skip is expected when protobuf is unavailable for tests marked with `skipif(not HAS_PROTOBUF, reason="protobuf library not installed")`; install protobuf if you need to exercise those paths locally or in CI.

### Debugging Tests

```bash
# Run with verbose output
uv run pytest tests/ -vv

# Run with stdout/stderr capture disabled (see print statements)
uv run pytest tests/ -v -s

# Run with pdb debugger on failure
uv run pytest tests/ -v --pdb

# Keep test output directories for inspection
uv run pytest tests/ -v --basetemp=/tmp/pytest-output
```

## Test Maintenance

When modifying code generation logic:

1. Run the full test suite to catch regressions.
2. Update affected test assertions if expected behavior changes.
3. Add new tests for new features before implementing when practical.
4. Update fixture documentation when adding, moving, or removing proto fixtures.
5. Update the `Test Case Reference` rows whenever test assertions, generated-file expectations, or fixtures change.
6. Keep `AGENTS.md` and `WARP.md` consistent when changing durable workflows that affect coding agents or human tooling.
