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

Namespace Com.Example.Priority

' NamespaceTest represents the NamespaceTest message from the proto definition
Public Class NamespaceTest
    <JsonProperty("field")>
    Public Property Field As String
End Class

' NamespaceServiceClient is an HTTP client for the NamespaceService service
Public Class NamespaceServiceClient
    Private ReadOnly _httpUtility As Test_special_casesHttpUtility

    Public Sub New(httpClient As HttpClient, baseUrl As String)
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New Test_special_casesHttpUtility(httpClient, baseUrl)
    End Sub

    Public Function TestCallAsync(request As NamespaceTest) As Task(Of NamespaceTest)
        Return TestCallAsync(request, CancellationToken.None)
    End Function

    Public Function TestCallAsync(request As NamespaceTest, cancellationToken As CancellationToken) As Task(Of NamespaceTest)
        Return TestCallAsync(request, cancellationToken, Nothing)
    End Function

    Public Async Function TestCallAsync(request As NamespaceTest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of NamespaceTest)
        Return Await _httpUtility.PostJsonAsync(Of NamespaceTest, NamespaceTest)("/test_namespace_priority/test-call/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function

End Class

End Namespace
