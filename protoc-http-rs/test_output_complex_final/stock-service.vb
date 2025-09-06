Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Stock

    Public Class PriceUpdate
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

    End Class

    Public Class StockPriceResponse
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
        Private Shared ReadOnly _http As HttpClient = New HttpClient()
        Private ReadOnly _baseUrl As String

        Public Sub New(baseUrl As String)
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Public Function GetStockPriceAsync(request As StockPriceRequest) As Task(Of StockPriceResponse)
            Return GetStockPriceAsync(request, CancellationToken.None)
        End Function
        Public Async Function GetStockPriceAsync(request As StockPriceRequest, cancellationToken As CancellationToken) As Task(Of StockPriceResponse)
            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))
            Dim url As String = String.Format("{0}/stock-service/get-stock-price", _baseUrl)
            Dim json As String = JsonConvert.SerializeObject(request)
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)
                If Not response.IsSuccessStatusCode Then
                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                    Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                End If
                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                Return JsonConvert.DeserializeObject(Of StockPriceResponse)(respJson)
            End Using
        End Function

    End Class

End Namespace