Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace TestN2

    Public Class N2Request
        <JsonProperty("data")>
        Public Property Data As String

    End Class

    Public Class N2Response
        <JsonProperty("result")>
        Public Property Result As String

    End Class

    Public Class N2TestServiceClient
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

        Public Function GetN2DataAsync(request As N2Request) As Task(Of N2Response)
            Return GetN2DataAsync(request, CancellationToken.None)
        End Function

        Public Function GetN2DataAsync(request As N2Request, cancellationToken As CancellationToken) As Task(Of N2Response)
            Return GetN2DataAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetN2DataAsync(request As N2Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of N2Response)
            Return Await PostJsonAsync(Of N2Request, N2Response)("/test_n2_kebab/get-n2-data/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function N2ToN2SyncAsync(request As N2Request) As Task(Of N2Response)
            Return N2ToN2SyncAsync(request, CancellationToken.None)
        End Function

        Public Function N2ToN2SyncAsync(request As N2Request, cancellationToken As CancellationToken) As Task(Of N2Response)
            Return N2ToN2SyncAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function N2ToN2SyncAsync(request As N2Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of N2Response)
            Return Await PostJsonAsync(Of N2Request, N2Response)("/test_n2_kebab/n2-to-n2-sync/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function N2FetchAsync(request As N2Request) As Task(Of N2Response)
            Return N2FetchAsync(request, CancellationToken.None)
        End Function

        Public Function N2FetchAsync(request As N2Request, cancellationToken As CancellationToken) As Task(Of N2Response)
            Return N2FetchAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function N2FetchAsync(request As N2Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of N2Response)
            Return Await PostJsonAsync(Of N2Request, N2Response)("/test_n2_kebab/n2-fetch/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function GetN3DataAsync(request As N2Request) As Task(Of N2Response)
            Return GetN3DataAsync(request, CancellationToken.None)
        End Function

        Public Function GetN3DataAsync(request As N2Request, cancellationToken As CancellationToken) As Task(Of N2Response)
            Return GetN3DataAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetN3DataAsync(request As N2Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of N2Response)
            Return Await PostJsonAsync(Of N2Request, N2Response)("/test_n2_kebab/get-n-3-data/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function GetN1DataAsync(request As N2Request) As Task(Of N2Response)
            Return GetN1DataAsync(request, CancellationToken.None)
        End Function

        Public Function GetN1DataAsync(request As N2Request, cancellationToken As CancellationToken) As Task(Of N2Response)
            Return GetN1DataAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetN1DataAsync(request As N2Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of N2Response)
            Return Await PostJsonAsync(Of N2Request, N2Response)("/test_n2_kebab/get-n-1-data/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace