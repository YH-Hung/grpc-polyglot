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

Namespace Helloworld

' HelloRequest represents the HelloRequest message from the proto definition
Public Class HelloRequest
    <JsonProperty("name")>
    Public Property Name As String
End Class

' HelloReply represents the HelloReply message from the proto definition
Public Class HelloReply
    <JsonProperty("message")>
    Public Property Message As String
End Class

' GreeterClient is an HTTP client for the Greeter service
Public Class GreeterClient
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

    Public Function SayHelloAsync(request As HelloRequest) As Task(Of HelloReply)
        Return SayHelloAsync(request, CancellationToken.None)
    End Function

    Public Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken) As Task(Of HelloReply)
        Return SayHelloAsync(request, cancellationToken, Nothing)
    End Function

    Public Async Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of HelloReply)
        Return Await PostJsonAsync(Of HelloRequest, HelloReply)("/helloworld/say-hello/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function

    Public Function SayHelloV2Async(request As HelloRequest) As Task(Of HelloReply)
        Return SayHelloV2Async(request, CancellationToken.None)
    End Function

    Public Function SayHelloV2Async(request As HelloRequest, cancellationToken As CancellationToken) As Task(Of HelloReply)
        Return SayHelloV2Async(request, cancellationToken, Nothing)
    End Function

    Public Async Function SayHelloV2Async(request As HelloRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of HelloReply)
        Return Await PostJsonAsync(Of HelloRequest, HelloReply)("/helloworld/say-hello/v2", request, cancellationToken, timeoutMs).ConfigureAwait(False)
    End Function

End Class

End Namespace
