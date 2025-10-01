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

Namespace Test_keywords

' KeywordTest represents the KeywordTest message from the proto definition
Public Class KeywordTest
    <JsonProperty("error")>
    Public Property [Error] As String
    <JsonProperty("class")>
    Public Property [Class] As String
    <JsonProperty("module")>
    Public Property [Module] As String
    <JsonProperty("integer")>
    Public Property [Integer] As Integer
    <JsonProperty("string")>
    Public Property [String] As String
    <JsonProperty("boolean")>
    Public Property [Boolean] As Boolean
    <JsonProperty("as")>
    Public Property [As] As String
    <JsonProperty("for")>
    Public Property [For] As String
    <JsonProperty("if")>
    Public Property [If] As String
    <JsonProperty("end")>
    Public Property [End] As String
    <JsonProperty("property")>
    Public Property [Property] As String
    <JsonProperty("select")>
    Public Property [Select] As String
    <JsonProperty("try")>
    Public Property [Try] As String
    <JsonProperty("catch")>
    Public Property [Catch] As String
    <JsonProperty("public")>
    Public Property [Public] As String
    <JsonProperty("private")>
    Public Property [Private] As String
End Class

' KeywordServiceClient is an HTTP client for the KeywordService service
Public Class KeywordServiceClient
    Public Property BaseUrl As String
    Private ReadOnly _httpClient As HttpClient

    Public Sub New(httpClient As HttpClient, baseUrl As String)
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        Me._httpClient = httpClient
        Me.BaseUrl = baseUrl.TrimEnd("/"c)
    End Sub

    Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)
        If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))
        Dim url As String = String.Format("{0}/{1}", Me.BaseUrl, relativePath.TrimStart("/"c))
        Dim json As String = JsonConvert.SerializeObject(request)
        Dim effectiveToken As CancellationToken = cancellationToken
        If timeoutMs.HasValue Then
            Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)
                Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)
                    effectiveToken = combined.Token
                    Using content As New StringContent(json, Encoding.UTF8, "application/json")
                        Dim response As HttpResponseMessage = Await Me._httpClient.PostAsync(url, content, effectiveToken).ConfigureAwait(False)
                        If Not response.IsSuccessStatusCode Then
                            Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                            Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                        End If
                        Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                        If String.IsNullOrWhiteSpace(respJson) Then
                            Throw New InvalidOperationException("Received empty response from server")
                        End If
                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)
                    End Using
                End Using
            End Using
        Else
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                Dim response As HttpResponseMessage = Await Me._httpClient.PostAsync(url, content, cancellationToken).ConfigureAwait(False)
                If Not response.IsSuccessStatusCode Then
                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                    Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                End If
                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                If String.IsNullOrWhiteSpace(respJson) Then
                    Throw New InvalidOperationException("Received empty response from server")
                End If
                Return JsonConvert.DeserializeObject(Of TResp)(respJson)
            End Using
        End If
    End Function

    Public Function TestMethodAsync(request As KeywordTest) As Task(Of KeywordTest)
        Return TestMethodAsync(request, CancellationToken.None)
    End Function

    Public Function TestMethodAsync(request As KeywordTest, cancellationToken As CancellationToken) As Task(Of KeywordTest)
        Return TestMethodAsync(request, cancellationToken, Nothing)
    End Function

    Public Async Function TestMethodAsync(request As KeywordTest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of KeywordTest)
        Return Await PostJsonAsync(Of KeywordTest, KeywordTest)("/test_keywords/test-method/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function

End Class

End Namespace
