Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace TestVersionedDemo

    Public Class PaymentResponse
        <JsonProperty("transactionId")>
        Public Property TransactionId As Integer

        <JsonProperty("success")>
        Public Property Success As Boolean

    End Class

    Public Class PaymentRequest
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("amount")>
        Public Property Amount As Integer

    End Class

    Public Class UserRequest
        <JsonProperty("userId")>
        Public Property UserId As Integer

    End Class

    Public Class UserResponse
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("name")>
        Public Property Name As String

        <JsonProperty("email")>
        Public Property Email As String

    End Class

    Public Class DemoServiceClient
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

        Public Function GetUserAsync(request As UserRequest) As Task(Of UserResponse)
            Return GetUserAsync(request, CancellationToken.None)
        End Function

        Public Function GetUserAsync(request As UserRequest, cancellationToken As CancellationToken) As Task(Of UserResponse)
            Return GetUserAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetUserAsync(request As UserRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of UserResponse)
            Return Await PostJsonAsync(Of UserRequest, UserResponse)("/test_versioned_demo/get-user/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function ProcessPaymentAsync(request As PaymentRequest) As Task(Of PaymentResponse)
            Return ProcessPaymentAsync(request, CancellationToken.None)
        End Function

        Public Function ProcessPaymentAsync(request As PaymentRequest, cancellationToken As CancellationToken) As Task(Of PaymentResponse)
            Return ProcessPaymentAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function ProcessPaymentAsync(request As PaymentRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of PaymentResponse)
            Return Await PostJsonAsync(Of PaymentRequest, PaymentResponse)("/test_versioned_demo/process-payment/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function GetUserV2Async(request As UserRequest) As Task(Of UserResponse)
            Return GetUserV2Async(request, CancellationToken.None)
        End Function

        Public Function GetUserV2Async(request As UserRequest, cancellationToken As CancellationToken) As Task(Of UserResponse)
            Return GetUserV2Async(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetUserV2Async(request As UserRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of UserResponse)
            Return Await PostJsonAsync(Of UserRequest, UserResponse)("/test_versioned_demo/get-user/v2", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function ProcessPaymentV2Async(request As PaymentRequest) As Task(Of PaymentResponse)
            Return ProcessPaymentV2Async(request, CancellationToken.None)
        End Function

        Public Function ProcessPaymentV2Async(request As PaymentRequest, cancellationToken As CancellationToken) As Task(Of PaymentResponse)
            Return ProcessPaymentV2Async(request, cancellationToken, Nothing)
        End Function

        Public Async Function ProcessPaymentV2Async(request As PaymentRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of PaymentResponse)
            Return Await PostJsonAsync(Of PaymentRequest, PaymentResponse)("/test_versioned_demo/process-payment/v2", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function GetUserV3Async(request As UserRequest) As Task(Of UserResponse)
            Return GetUserV3Async(request, CancellationToken.None)
        End Function

        Public Function GetUserV3Async(request As UserRequest, cancellationToken As CancellationToken) As Task(Of UserResponse)
            Return GetUserV3Async(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetUserV3Async(request As UserRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of UserResponse)
            Return Await PostJsonAsync(Of UserRequest, UserResponse)("/test_versioned_demo/get-user/v3", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function ProcessPaymentV10Async(request As PaymentRequest) As Task(Of PaymentResponse)
            Return ProcessPaymentV10Async(request, CancellationToken.None)
        End Function

        Public Function ProcessPaymentV10Async(request As PaymentRequest, cancellationToken As CancellationToken) As Task(Of PaymentResponse)
            Return ProcessPaymentV10Async(request, cancellationToken, Nothing)
        End Function

        Public Async Function ProcessPaymentV10Async(request As PaymentRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of PaymentResponse)
            Return Await PostJsonAsync(Of PaymentRequest, PaymentResponse)("/test_versioned_demo/process-payment/v10", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace