package main

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/generator"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/parser"
	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

const testProtoDir = "proto/test_special_cases"

// TestMsgHdrSpecialLogic tests that msgHdr messages preserve exact field names (no camelCase)
func TestMsgHdrSpecialLogic(t *testing.T) {
	t.Run("msgHdr preserves field names", func(t *testing.T) {
		// Parse proto
		protoPath := filepath.Join(testProtoDir, "test_msghdr.proto")
		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		// Generate VB code
		tmpDir := t.TempDir()
		outPath := filepath.Join(tmpDir, "test_msghdr.vb")
		gen := &generator.Generator{
			PackageOverride: "",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		// Read generated file
		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// msgHdr fields should preserve exact proto casing
		assert.Contains(t, contentStr, `JsonProperty("userId")`, "userId should be preserved as-is")
		assert.Contains(t, contentStr, `JsonProperty("FirstName")`, "FirstName should be preserved as-is")
		assert.Contains(t, contentStr, `JsonProperty("accountNumber")`, "accountNumber should be preserved as-is")

		// Verify context: these should be in msgHdr class
		lines := strings.Split(contentStr, "\n")
		inMsgHdr := false
		msgHdrJsonProps := []string{}
		for _, line := range lines {
			if strings.Contains(line, "Public Class msgHdr") {
				inMsgHdr = true
			} else if strings.Contains(line, "End Class") && inMsgHdr {
				inMsgHdr = false
			} else if inMsgHdr && strings.Contains(line, "JsonProperty") {
				msgHdrJsonProps = append(msgHdrJsonProps, line)
			}
		}

		// Verify exact preservation
		assert.True(t, containsAny(msgHdrJsonProps, `JsonProperty("userId")`))
		assert.True(t, containsAny(msgHdrJsonProps, `JsonProperty("FirstName")`))
		assert.True(t, containsAny(msgHdrJsonProps, `JsonProperty("accountNumber")`))
	})

	t.Run("regular message uses camelCase", func(t *testing.T) {
		protoPath := filepath.Join(testProtoDir, "test_msghdr.proto")
		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		tmpDir := t.TempDir()
		outPath := filepath.Join(tmpDir, "test_msghdr.vb")
		gen := &generator.Generator{
			PackageOverride: "",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// RegularMessage fields should be camelCase
		lines := strings.Split(contentStr, "\n")
		inRegular := false
		found := false
		for _, line := range lines {
			if strings.Contains(line, "Public Class RegularMessage") {
				inRegular = true
			} else if strings.Contains(line, "End Class") && inRegular {
				break
			} else if inRegular && strings.Contains(line, "JsonProperty") {
				// Within RegularMessage, should have camelCase
				if strings.Contains(line, "userId") || strings.Contains(line, "firstName") || strings.Contains(line, "accountNumber") {
					found = true
					break
				}
			}
		}
		assert.True(t, found, "RegularMessage should have camelCase fields")
	})

	t.Run("nested msgHdr preserves field names", func(t *testing.T) {
		protoPath := filepath.Join(testProtoDir, "test_msghdr.proto")
		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		tmpDir := t.TempDir()
		outPath := filepath.Join(tmpDir, "test_msghdr.vb")
		gen := &generator.Generator{
			PackageOverride: "",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// Nested msgHdr should preserve exact casing (InnerField with capital I)
		assert.Contains(t, contentStr, `JsonProperty("InnerField")`, "InnerField should be preserved as-is")
		// Outer message regular field should be converted to camelCase
		assert.Contains(t, contentStr, `JsonProperty("regularField")`, "regularField should be camelCase")
	})
}

// TestN2KebabCaseHandling tests that N2 pattern converts to -n2- not -n-2- in kebab-case
func TestN2KebabCaseHandling(t *testing.T) {
	t.Run("N2 converts to dash-n2-dash", func(t *testing.T) {
		protoPath := filepath.Join(testProtoDir, "test_n2_kebab.proto")
		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		tmpDir := t.TempDir()
		outPath := filepath.Join(tmpDir, "test_n2_kebab.vb")
		gen := &generator.Generator{
			PackageOverride: "",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// N2 should convert to -n2- not -n-2-
		assert.Contains(t, contentStr, "get-n2-data/v1")
		assert.Contains(t, contentStr, "n2-service-call/v1")
		assert.Contains(t, contentStr, "fetch-n2/v1")
		assert.Contains(t, contentStr, "n2-to-n2-sync/v1")

		// Should NOT contain -n-2-
		assert.NotContains(t, contentStr, "-n-2-")
	})

	t.Run("N2 unit conversion", func(t *testing.T) {
		// Test the KebabCase function directly
		assert.Equal(t, "get-n2-data", types.KebabCase("GetN2Data"))
		assert.Equal(t, "n2-service-call", types.KebabCase("N2ServiceCall"))
		assert.Equal(t, "fetch-n2", types.KebabCase("FetchN2"))
		assert.Equal(t, "n2-to-n2-sync", types.KebabCase("N2ToN2Sync"))

		// Control: N3 should still split
		assert.Equal(t, "get-n-3-data", types.KebabCase("GetN3Data"))
	})

	t.Run("other patterns unchanged", func(t *testing.T) {
		protoPath := filepath.Join(testProtoDir, "test_n2_kebab.proto")
		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		tmpDir := t.TempDir()
		outPath := filepath.Join(tmpDir, "test_n2_kebab.vb")
		gen := &generator.Generator{
			PackageOverride: "",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// N3 should still be split as -n-3-
		assert.Contains(t, contentStr, "get-n-3-data/v1")
	})
}

// TestNamespacePriority tests that proto package always takes priority over CLI --package
func TestNamespacePriority(t *testing.T) {
	t.Run("package overrides CLI namespace", func(t *testing.T) {
		protoPath := filepath.Join(testProtoDir, "test_namespace_priority.proto")
		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		tmpDir := t.TempDir()
		outPath := filepath.Join(tmpDir, "test_namespace_priority.vb")
		// Try to override with CLI namespace
		gen := &generator.Generator{
			PackageOverride: "MyCustomNamespace",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// Should use package-derived namespace, not CLI
		assert.Contains(t, contentStr, "Namespace Com.Example.Priority")
		assert.NotContains(t, contentStr, "Namespace MyCustomNamespace")
	})

	t.Run("CLI namespace used when no package", func(t *testing.T) {
		// Create temporary proto without package
		tmpDir := t.TempDir()
		protoPath := filepath.Join(tmpDir, "no_package.proto")
		protoContent := `syntax = "proto3";

message NoPackageTest {
  string field = 1;
}

service NoPackageService {
  rpc Call(NoPackageTest) returns (NoPackageTest) {}
}
`
		err := os.WriteFile(protoPath, []byte(protoContent), 0644)
		require.NoError(t, err)

		proto, err := parser.ParseProtoFile(protoPath)
		require.NoError(t, err)

		outPath := filepath.Join(tmpDir, "no_package.vb")
		gen := &generator.Generator{
			PackageOverride: "FallbackNamespace",
			FrameworkMode:   "net45",
		}
		err = gen.GenerateFile(proto, outPath)
		require.NoError(t, err)

		content, err := os.ReadFile(outPath)
		require.NoError(t, err)
		contentStr := string(content)

		// Should use CLI namespace as fallback
		assert.Contains(t, contentStr, "Namespace FallbackNamespace")
	})
}

// Helper functions
func containsAny(slice []string, substr string) bool {
	for _, s := range slice {
		if strings.Contains(s, substr) {
			return true
		}
	}
	return false
}
