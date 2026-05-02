package generator

import "strings"

const bytesEncodingWhitelistLiteral = `"utf-8", "big5", "gb2312", "gbk", "shift_jis", "ascii", "iso-8859-1", "utf-16"`
const bytesEncodingWhitelistPretty = "utf-8, big5, gb2312, gbk, shift_jis, ascii, iso-8859-1, utf-16"

// emitBytesHelpers writes VB.NET helpers that convert protobuf JSON bytes
// fields between base64 wire values and decoded text strings.
func emitBytesHelpers(sb *strings.Builder, indent string) {
	lines := []string{
		"Public NotInheritable Class ProtoBytesEncoding",
		"    Private Sub New()",
		"    End Sub",
		"",
		"    Private Shared _encoding As Encoding = Encoding.UTF8",
		"",
		"    Public Shared Property [Default] As Encoding",
		"        Get",
		"            Return _encoding",
		"        End Get",
		"        Set(value As Encoding)",
		"            If value Is Nothing Then Throw New ArgumentNullException(\"value\")",
		"            _encoding = value",
		"        End Set",
		"    End Property",
		"",
		"    Public Shared Sub UseEncoding(encodingName As String)",
		"        [Default] = ResolveEncoding(encodingName)",
		"    End Sub",
		"",
		"    Public Shared Function ResolveEncoding(encodingName As String) As Encoding",
		"        If String.IsNullOrWhiteSpace(encodingName) Then",
		"            Throw New ArgumentException(\"encodingName cannot be null or empty\", \"encodingName\")",
		"        End If",
		"        Dim normalized As String = encodingName.Trim().ToLowerInvariant()",
		"        Dim supported As String() = New String() {" + bytesEncodingWhitelistLiteral + "}",
		"        Dim ok As Boolean = False",
		"        For Each name As String In supported",
		"            If name = normalized Then",
		"                ok = True",
		"                Exit For",
		"            End If",
		"        Next",
		"        If Not ok Then",
		"            Throw New NotSupportedException(\"Encoding '\" & encodingName & \"' is not supported. Supported encodings: " + bytesEncodingWhitelistPretty + "\")",
		"        End If",
		"        Return Encoding.GetEncoding(normalized)",
		"    End Function",
		"End Class",
		"",
		"Public Class BytesStringConverter",
		"    Inherits JsonConverter",
		"",
		"    Public Overrides Function CanConvert(objectType As Type) As Boolean",
		"        Return objectType Is GetType(String)",
		"    End Function",
		"",
		"    Public Overrides Function ReadJson(reader As JsonReader, objectType As Type, existingValue As Object, serializer As JsonSerializer) As Object",
		"        If reader.TokenType = JsonToken.Null Then Return Nothing",
		"        Dim base64Value As String = TryCast(reader.Value, String)",
		"        If base64Value Is Nothing Then Return Nothing",
		"        If base64Value.Length = 0 Then Return String.Empty",
		"        Dim raw As Byte() = Convert.FromBase64String(base64Value)",
		"        Return ProtoBytesEncoding.Default.GetString(raw)",
		"    End Function",
		"",
		"    Public Overrides Sub WriteJson(writer As JsonWriter, value As Object, serializer As JsonSerializer)",
		"        If value Is Nothing Then",
		"            writer.WriteNull()",
		"            Return",
		"        End If",
		"        Dim text As String = CStr(value)",
		"        Dim raw As Byte() = ProtoBytesEncoding.Default.GetBytes(text)",
		"        writer.WriteValue(Convert.ToBase64String(raw))",
		"    End Sub",
		"End Class",
		"",
	}

	for _, line := range lines {
		if line == "" {
			sb.WriteString("\n")
			continue
		}
		sb.WriteString(indent)
		sb.WriteString(line)
		sb.WriteString("\n")
	}
}
