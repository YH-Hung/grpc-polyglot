Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization

Namespace Helloworld

' HelloReply represents the HelloReply message from the proto definition
Public Class HelloReply
    <JsonProperty("message")>
    Public Property Message As String
End Class

' HelloRequest represents the HelloRequest message from the proto definition
Public Class HelloRequest
    <JsonProperty("name")>
    Public Property Name As String
End Class

' GreeterClient is an HTTP client for the Greeter service
Public Class GreeterClient
    Public Property BaseUrl As String
    Private ReadOnly _httpClient As HttpClient

    Public Sub New(baseUrl As String)
        Me.BaseUrl = baseUrl
        Me._httpClient = New HttpClient()
    End Sub

    Public Sub New(baseUrl As String, httpClient As HttpClient)
        Me.BaseUrl = baseUrl
        Me._httpClient = httpClient
    End Sub

    Private Async Function PostJsonAsync(Of TResponse)(url As String, requestBody As Object, cancellationToken As CancellationToken) As Task(Of TResponse)
        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }
        Dim reqJson As String = JsonConvert.SerializeObject(requestBody, settings)
        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)
            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, "application/json")
            httpRequest.Headers.Accept.Clear()
            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue("application/json"))
            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)
            Dim respBody As String = Await response.Content.ReadAsStringAsync()
            If Not response.IsSuccessStatusCode Then
                Throw New HttpRequestException(String.Format("HTTP request failed with status {0}: {1}", CInt(response.StatusCode), respBody))
            End If
            Dim result As TResponse = JsonConvert.DeserializeObject(Of TResponse)(respBody, settings)
            Return result
        End Using
    End Function

    ' SayHelloAsync calls the SayHello RPC method
    Public Async Function SayHelloAsync(request As HelloRequest, Optional cancellationToken As CancellationToken = Nothing) As Task(Of HelloReply)
        Dim url As String = Me.BaseUrl & "/helloworld/say-hello/" & "v1"
        Return Await PostJsonAsync(Of HelloReply)(url, request, cancellationToken)
    End Function

End Class

End Namespace
