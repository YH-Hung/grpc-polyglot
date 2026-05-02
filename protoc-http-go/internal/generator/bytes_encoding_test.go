package generator

import (
	"os"
	"path/filepath"
	"strings"
	"testing"

	"github.com/yinghanhung/grpc-polyglot/protoc-http-go/internal/types"
)

func testBytesProto() *types.ProtoFile {
	return &types.ProtoFile{
		FileName: "bytes_only.proto",
		BaseName: "bytes_only",
		Package:  "bytespkg",
		Messages: map[string]*types.ProtoMessage{
			"BytesRequest": {
				Name: "BytesRequest",
				Fields: []*types.ProtoField{
					{Name: "body", Type: "bytes"},
					{Name: "attachments", Type: "bytes", Repeated: true},
				},
				NestedMessages: map[string]*types.ProtoMessage{
					"Inner": {
						Name: "Inner",
						Fields: []*types.ProtoField{
							{Name: "nested_blob", Type: "bytes"},
						},
						NestedMessages: map[string]*types.ProtoMessage{},
						NestedEnums:    map[string]*types.ProtoEnum{},
					},
				},
				NestedEnums: map[string]*types.ProtoEnum{},
			},
		},
		Enums:    map[string]*types.ProtoEnum{},
		Services: []*types.ProtoService{},
	}
}

func testNoBytesProto() *types.ProtoFile {
	return &types.ProtoFile{
		FileName: "hello.proto",
		BaseName: "hello",
		Package:  "hello",
		Messages: map[string]*types.ProtoMessage{
			"HelloRequest": {
				Name: "HelloRequest",
				Fields: []*types.ProtoField{
					{Name: "name", Type: "string"},
				},
				NestedMessages: map[string]*types.ProtoMessage{},
				NestedEnums:    map[string]*types.ProtoEnum{},
			},
		},
		Enums:    map[string]*types.ProtoEnum{},
		Services: []*types.ProtoService{},
	}
}

func generateProto(t *testing.T, proto *types.ProtoFile) string {
	t.Helper()

	tmpDir := t.TempDir()
	outPath := filepath.Join(tmpDir, proto.BaseName+".vb")
	gen := &Generator{FrameworkMode: "net45"}
	if err := gen.GenerateFile(proto, outPath); err != nil {
		t.Fatalf("GenerateFile() error = %v", err)
	}

	content, err := os.ReadFile(outPath)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}
	return string(content)
}

func TestBytesFieldsEmitConvertersAndHelpers(t *testing.T) {
	content := generateProto(t, testBytesProto())

	assertContains(t, content, `Public NotInheritable Class ProtoBytesEncoding`)
	assertContains(t, content, `Public Class BytesStringConverter`)
	assertContains(t, content, `Public Shared Property [Default] As Encoding`)
	assertContains(t, content, `Public Shared Sub UseEncoding(encodingName As String)`)
	for _, encodingName := range []string{"utf-8", "big5", "gb2312", "gbk", "shift_jis", "ascii", "iso-8859-1", "utf-16"} {
		assertContains(t, content, `"`+encodingName+`"`)
	}
	assertContains(t, content, `Convert.FromBase64String`)
	assertContains(t, content, `ProtoBytesEncoding.Default.GetString`)
	assertContains(t, content, `ProtoBytesEncoding.Default.GetBytes`)
	assertContains(t, content, `Convert.ToBase64String`)

	assertContains(t, content, `<JsonProperty("body")>`)
	assertContains(t, content, `<JsonConverter(GetType(BytesStringConverter))>`)
	assertContains(t, content, `Public Property Body As String  ' base64 wire / decoded text via ProtoBytesEncoding.Default`)
	assertContains(t, content, `<JsonProperty("attachments", ItemConverterType:=GetType(BytesStringConverter))>`)
	assertContains(t, content, `Public Property Attachments As List(Of String)  ' base64 wire / decoded text via ProtoBytesEncoding.Default`)
	assertContains(t, content, `<JsonProperty("nestedBlob")>`)

	if count := strings.Count(content, `<JsonConverter(GetType(BytesStringConverter))>`); count < 2 {
		t.Fatalf("expected scalar bytes fields, including nested fields, to use JsonConverter at least twice; got %d\n%s", count, content)
	}
}

func TestProtoWithoutBytesSkipsBytesHelpers(t *testing.T) {
	content := generateProto(t, testNoBytesProto())

	assertNotContains(t, content, `BytesStringConverter`)
	assertNotContains(t, content, `ProtoBytesEncoding`)
}

func TestSharedUtilityEmitsBytesHelpersOnce(t *testing.T) {
	tmpDir := t.TempDir()
	utilityPath := filepath.Join(tmpDir, "SharedHttpUtility.vb")
	gen := &Generator{FrameworkMode: "net45"}

	if err := gen.GenerateSharedUtility("SharedHttpUtility", "Shared", utilityPath, true); err != nil {
		t.Fatalf("GenerateSharedUtility() error = %v", err)
	}
	utilityContent, err := os.ReadFile(utilityPath)
	if err != nil {
		t.Fatalf("ReadFile() error = %v", err)
	}

	assertContains(t, string(utilityContent), `Public NotInheritable Class ProtoBytesEncoding`)
	assertContains(t, string(utilityContent), `Public Class BytesStringConverter`)

	proto := testBytesProto()
	proto.Package = "other"
	proto.UseSharedUtility = true
	proto.SharedUtilityName = "SharedHttpUtility"
	proto.SharedUtilityNamespace = "Shared"

	dtoContent := generateProto(t, proto)
	assertNotContains(t, dtoContent, `Public Class BytesStringConverter`)
	assertContains(t, dtoContent, `<JsonConverter(GetType(Shared.BytesStringConverter))>`)
	assertContains(t, dtoContent, `<JsonProperty("attachments", ItemConverterType:=GetType(Shared.BytesStringConverter))>`)
}

func assertContains(t *testing.T, content, want string) {
	t.Helper()
	if !strings.Contains(content, want) {
		t.Fatalf("expected generated content to contain %q\n%s", want, content)
	}
}

func assertNotContains(t *testing.T, content, want string) {
	t.Helper()
	if strings.Contains(content, want) {
		t.Fatalf("expected generated content not to contain %q\n%s", want, content)
	}
}
