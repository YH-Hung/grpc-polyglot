Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Helloworld

    Public Class HelloReply
        <JsonProperty("message")>
        Public Property Message As String

    End Class

    Public Class HelloRequest
        <JsonProperty("name")>
        Public Property Name As String

    End Class

    Public Class GreeterClient
        Private ReadOnly _http As HttpClient
        Private ReadOnly _baseUrl As String

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _http = http
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of TResp)
            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))
            Dim url As String = String.Format("{0}/{1}", _baseUrl, relativePath.TrimStart("/"c))
            Dim json As String = JsonConvert.SerializeObject(request)
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                If timeoutMs.HasValue Then
                    Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)
                        Using combined As CancellationTokenSource = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token)
                            Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, combined.Token).ConfigureAwait(False)
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
                Else
                    Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)
                    If Not response.IsSuccessStatusCode Then
                        Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                        Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                    End If
                    Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                    If String.IsNullOrWhiteSpace(respJson) Then
                        Throw New InvalidOperationException("Received empty response from server")
                    End If
                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)
                End If
            End Using
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