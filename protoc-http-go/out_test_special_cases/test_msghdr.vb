Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks

Namespace Msghdr.Test

' msgHdr represents the msgHdr message from the proto definition
Public Class msgHdr
    <JsonProperty("userId")>
    Public Property UserId As String
    <JsonProperty("FirstName")>
    Public Property FirstName As String
    <JsonProperty("accountNumber")>
    Public Property AccountNumber As Integer
End Class

' RegularMessage represents the RegularMessage message from the proto definition
Public Class RegularMessage
    <JsonProperty("userId")>
    Public Property UserId As String
    <JsonProperty("firstName")>
    Public Property FirstName As String
    <JsonProperty("accountNumber")>
    Public Property AccountNumber As Integer
End Class

' OuterMessage represents the OuterMessage message from the proto definition
Public Class OuterMessage
    <JsonProperty("innerField")>
    Public Property InnerField As String
    <JsonProperty("header")>
    Public Property Header As msgHdr
    <JsonProperty("regularField")>
    Public Property RegularField As String
End Class

' OuterMessage_msgHdr represents the msgHdr message from the proto definition
Public Class OuterMessage_msgHdr
    <JsonProperty("InnerField")>
    Public Property InnerField As String
End Class

' TestServiceClient is an HTTP client for the TestService service
Public Class TestServiceClient
    Private ReadOnly _httpUtility As Test_special_casesHttpUtility

    Public Sub New(httpClient As HttpClient, baseUrl As String)
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New Test_special_casesHttpUtility(httpClient, baseUrl)
    End Sub

    Public Function ProcessHeaderAsync(request As msgHdr) As Task(Of RegularMessage)
        Return ProcessHeaderAsync(request, CancellationToken.None)
    End Function

    Public Function ProcessHeaderAsync(request As msgHdr, cancellationToken As CancellationToken) As Task(Of RegularMessage)
        Return ProcessHeaderAsync(request, cancellationToken, Nothing)
    End Function

    Public Async Function ProcessHeaderAsync(request As msgHdr, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of RegularMessage)
        Return Await _httpUtility.PostJsonAsync(Of msgHdr, RegularMessage)("/test_msghdr/process-header/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function

End Class

End Namespace
