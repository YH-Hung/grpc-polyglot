Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Stock

    Public Class StockPriceResponse
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

    End Class

    Public Class PriceUpdate
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

    End Class

    Public Class StockPriceRequest
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

    End Class

    Public Class StockServiceClient
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
            Dim effectiveToken As CancellationToken = cancellationToken
            If timeoutMs.HasValue Then
                Using timeoutCts As New CancellationTokenSource(timeoutMs.Value)
                    effectiveToken = CancellationTokenSource.CreateLinkedTokenSource(cancellationToken, timeoutCts.Token).Token
                End Using
            End If
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, effectiveToken).ConfigureAwait(False)
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
        End Function

        Public Function GetStockPriceAsync(request As StockPriceRequest) As Task(Of StockPriceResponse)
            Return GetStockPriceAsync(request, CancellationToken.None)
        End Function

        Public Function GetStockPriceAsync(request As StockPriceRequest, cancellationToken As CancellationToken) As Task(Of StockPriceResponse)
            Return GetStockPriceAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetStockPriceAsync(request As StockPriceRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of StockPriceResponse)
            Return Await PostJsonAsync(Of StockPriceRequest, StockPriceResponse)("/stock-service/get-stock-price/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace