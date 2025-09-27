Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Test

    Public Class GetUserV2Request
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("includeDetails")>
        Public Property IncludeDetails As Boolean

    End Class

    Public Class GetUserResponse
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("name")>
        Public Property Name As String

    End Class

    Public Class GetUserV2Response
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("name")>
        Public Property Name As String

        <JsonProperty("email")>
        Public Property Email As String

        <JsonProperty("age")>
        Public Property Age As Integer

    End Class

    Public Class GetUserRequest
        <JsonProperty("userId")>
        Public Property UserId As Integer

    End Class

    Public Class UserServiceClient
        Private ReadOnly _http As HttpClient
        Private ReadOnly _baseUrl As String

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _http = http
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken) As Task(Of TResp)
            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))
            Dim url As String = String.Format("{0}/{1}", _baseUrl, relativePath.TrimStart("/"c))
            Dim json As String = JsonConvert.SerializeObject(request)
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)
                If Not response.IsSuccessStatusCode Then
                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                    Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                End If
                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                Return JsonConvert.DeserializeObject(Of TResp)(respJson)
            End Using
        End Function

        Public Function GetUserAsync(request As GetUserRequest) As Task(Of GetUserResponse)
            Return GetUserAsync(request, CancellationToken.None)
        End Function
        Public Async Function GetUserAsync(request As GetUserRequest, cancellationToken As CancellationToken) As Task(Of GetUserResponse)
            Return Await PostJsonAsync(Of GetUserRequest, GetUserResponse)("/test_versioned/get-user/v1", request, cancellationToken).ConfigureAwait(False)
        End Function

        Public Function GetUserV2Async(request As GetUserV2Request) As Task(Of GetUserV2Response)
            Return GetUserV2Async(request, CancellationToken.None)
        End Function
        Public Async Function GetUserV2Async(request As GetUserV2Request, cancellationToken As CancellationToken) As Task(Of GetUserV2Response)
            Return Await PostJsonAsync(Of GetUserV2Request, GetUserV2Response)("/test_versioned/get-user/v2", request, cancellationToken).ConfigureAwait(False)
        End Function

        Public Function GetUserV3Async(request As GetUserV2Request) As Task(Of GetUserV2Response)
            Return GetUserV3Async(request, CancellationToken.None)
        End Function
        Public Async Function GetUserV3Async(request As GetUserV2Request, cancellationToken As CancellationToken) As Task(Of GetUserV2Response)
            Return Await PostJsonAsync(Of GetUserV2Request, GetUserV2Response)("/test_versioned/get-user/v3", request, cancellationToken).ConfigureAwait(False)
        End Function

    End Class

End Namespace