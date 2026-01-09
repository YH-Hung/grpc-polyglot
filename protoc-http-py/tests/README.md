# Test Suite Documentation

## Test Structure

### Standard Tests
- **test_generation_check.py**: Main integration tests for VB.NET code generation
  - Tests camelCase JSON property naming
  - Tests nested type handling
  - Tests VB keyword escaping
  - Tests shared utility generation

- **test_compat_modes.py**: Tests for .NET Framework compatibility modes
  - Default async mode (HttpClient + async/await)
  - NET45 mode (.NET 4.5+ with async)
  - NET40HWR mode (.NET 4.0 with HttpWebRequest synchronous)
  - CLI alias validation

- **generate_variants.py**: Utility script to generate output variants for comparison

### Special Cases Tests
- **test_special_cases.py**: Tests for special behaviors:
  - **msgHdr field name preservation**: Messages named "msgHdr" preserve exact field names (no conversion)
  - **N2 kebab-case handling**: "N2" pattern converts to `-n2-` (not `-n-2-`)
  - **Namespace priority rules**: Proto package always takes priority over CLI `--namespace`

## Running Tests

### Run All Tests
```bash
cd /Users/yinghanhung/Projects/grpc-polyglot/protoc-http-py
uv run pytest tests/ -v
```

### Run Specific Test File
```bash
# Run special cases tests
uv run pytest tests/test_special_cases.py -v

# Run compatibility mode tests
uv run pytest tests/test_compat_modes.py -v

# Run generation check tests
uv run pytest tests/test_generation_check.py -v
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
# Run a single test
uv run pytest tests/test_special_cases.py::TestMsgHdrSpecialLogic::test_msghdr_preserves_field_names -v
```

### Run with Coverage
```bash
uv run pytest tests/ --cov=protoc_http_py --cov-report=html
```

## Test Proto Files

Test proto files are organized by test category:

### Simple Proto Files
Located in `/proto/simple/`:
- **helloworld.proto**: Basic service with unary RPCs and versioned endpoints

### Complex Proto Files
Located in `/proto/complex/`:
- **user-service.proto**: Service with cross-package imports
- **stock-service.proto**: Service with streaming RPCs (only unary tested)
- **common/common.proto**: Shared types (Ticker enum)
- **nested.proto**: Tests nested message types

### Special Cases Proto Files
Located in `/proto/test_special_cases/`:
- **test_msghdr.proto**: msgHdr special logic tests
  - Contains `msgHdr` message with snake_case fields
  - Contains `RegularMessage` for comparison (camelCase expected)
  - Contains nested `msgHdr` to test recursion

- **test_n2_kebab.proto**: N2 kebab-case pattern tests
  - RPCs with N2 in various positions: `GetN2Data`, `N2ServiceCall`, `FetchN2`, `N2ToN2Sync`
  - Control case with N3: `GetN3Data` (should still split as `-n-3-`)

- **test_namespace_priority.proto**: Namespace priority tests
  - Defines package to test that CLI namespace is ignored

## Test Expectations

### msgHdr Tests
- **Preserved field names**: `msgHdr` messages should have JSON properties with exact proto names
  - `user_id` → `JsonProperty("user_id")` NOT `JsonProperty("userId")`
- **Regular messages unchanged**: Non-msgHdr messages should still use camelCase
  - `user_id` → `JsonProperty("userId")`
- **Nested msgHdr**: Nested messages named `msgHdr` should also preserve field names

### N2 Kebab-Case Tests
- **N2 pattern handling**: RPC names containing "N2" should convert to `-n2-` in URLs
  - `GetN2Data` → `/service/get-n2-data/v1`
  - `N2ServiceCall` → `/service/n2-service-call/v1`
- **Other patterns unchanged**: Other letter-digit patterns should still split normally
  - `GetN3Data` → `/service/get-n-3-data/v1`

### Namespace Priority Tests
- **Package overrides CLI**: When proto has `package`, CLI `--namespace` is ignored
  - Proto with `package com.example.test` + CLI `--namespace Custom` → `Namespace ComExampleTest`
- **CLI as fallback**: When proto has no package, CLI `--namespace` is used
  - Proto without package + CLI `--namespace Custom` → `Namespace Custom`

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
1. Use descriptive test method names that explain what is being tested
2. Use docstrings to document test purpose
3. Use `tmp_path` fixture for test output directories (auto-cleanup)
4. Test both positive cases (expected behavior) and negative cases (should not occur)
5. For integration tests, read generated VB.NET and assert on specific patterns
6. For unit tests, import and test functions directly from `protoc_http_py.main`

## CI/CD Integration

To integrate tests into CI/CD pipeline:

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
- **ImportError**: Ensure uv is installed and dependencies are synced (`uv sync`)
- **Missing protobuf**: Some tests are skipped if `google.protobuf` is not installed (expected)
- **Path issues**: Use `REPO_ROOT` and relative paths for proto files
- **Assertion failures**: Check generated VB.NET content in tmp_path (visible in error output)

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
1. Run full test suite to catch regressions
2. Update affected test assertions if expected behavior changes
3. Add new tests for new features before implementing (TDD)
4. Update test documentation when adding new test categories
