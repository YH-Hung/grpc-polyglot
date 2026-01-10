Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace TestSpecial

    Public Class OuterMessage
        <JsonProperty("outerField")>
        Public Property OuterField As String

        <JsonProperty("header")>
        Public Property Header As OuterMessage.msgHdr

        Public Class msgHdr
            <JsonProperty("NestedField")>
            Public Property NestedField As String

            <JsonProperty("another_field")>
            Public Property AnotherField As String

        End Class
    End Class

    Public Class msgHdr
        <JsonProperty("userId")>
        Public Property UserId As String

        <JsonProperty("FirstName")>
        Public Property FirstName As String

        <JsonProperty("user_age")>
        Public Property UserAge As Integer

        <JsonProperty("MixedCase_Field")>
        Public Property MixedCaseField As String

    End Class

    Public Class RegularMessage
        <JsonProperty("userId")>
        Public Property UserId As String

        <JsonProperty("firstName")>
        Public Property FirstName As String

        <JsonProperty("accountNumber")>
        Public Property AccountNumber As Integer

    End Class

    Public Class MsgHdrTestServiceClient
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

        Public Function SendHeaderAsync(request As test.special.msgHdr) As Task(Of RegularMessage)
            Return SendHeaderAsync(request, CancellationToken.None)
        End Function

        Public Function SendHeaderAsync(request As test.special.msgHdr, cancellationToken As CancellationToken) As Task(Of RegularMessage)
            Return SendHeaderAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function SendHeaderAsync(request As test.special.msgHdr, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of RegularMessage)
            Return Await PostJsonAsync(Of test.special.msgHdr, RegularMessage)("/test_msghdr/send-header/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function GetHeaderAsync(request As RegularMessage) As Task(Of test.special.msgHdr)
            Return GetHeaderAsync(request, CancellationToken.None)
        End Function

        Public Function GetHeaderAsync(request As RegularMessage, cancellationToken As CancellationToken) As Task(Of test.special.msgHdr)
            Return GetHeaderAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetHeaderAsync(request As RegularMessage, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of test.special.msgHdr)
            Return Await PostJsonAsync(Of RegularMessage, test.special.msgHdr)("/test_msghdr/get-header/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace