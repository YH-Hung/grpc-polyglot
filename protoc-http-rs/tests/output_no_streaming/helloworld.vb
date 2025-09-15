Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Helloworld

    Public Class HelloRequest
        <JsonProperty("name")>
        Public Property Name As String

    End Class

    Public Class HelloReply
        <JsonProperty("message")>
        Public Property Message As String

    End Class

    Public Class GreeterClient
        Private ReadOnly _httpClient As HttpClient
        Private ReadOnly _baseUrl As String

        Public Sub New(baseUrl As String, httpClient As HttpClient)
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
            _baseUrl = baseUrl.TrimEnd("/"c)
            _httpClient = httpClient
        End Sub

        Private Async Function SendAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken) As Task(Of TResp)
            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))
            Dim url As String = If(relativePath.StartsWith("/"), _baseUrl & relativePath, String.Format("{0}/{1}", _baseUrl, relativePath))
            Dim json As String = JsonConvert.SerializeObject(request)
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                Dim response As HttpResponseMessage = Await _httpClient.PostAsync(url, content, cancellationToken).ConfigureAwait(False)
                If Not response.IsSuccessStatusCode Then
                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                    Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                End If
                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                Return JsonConvert.DeserializeObject(Of TResp)(respJson)
            End Using
        End Function

        Public Function SayHelloAsync(request As HelloRequest) As Task(Of HelloReply)
            Return SayHelloAsync(request, CancellationToken.None)
        End Function
        Public Async Function SayHelloAsync(request As HelloRequest, cancellationToken As CancellationToken) As Task(Of HelloReply)
            Return SendAsync(Of HelloRequest, HelloReply)("/helloworld/say-hello", request, cancellationToken)
        End Function

    End Class

End Namespace