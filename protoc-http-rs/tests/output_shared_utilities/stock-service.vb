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

    Public Class StockPriceRequest
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

    End Class

    Public Class StockPriceResponse
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

    End Class

    Public Class StockServiceClient
        Private ReadOnly _httpUtility As DemoNestedHttpUtility

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _httpUtility = New DemoNestedHttpUtility(http, baseUrl)
        End Sub

        Public Function GetStockPriceAsync(request As StockPriceRequest) As Task(Of StockPriceResponse)
            Return GetStockPriceAsync(request, CancellationToken.None)
        End Function

        Public Function GetStockPriceAsync(request As StockPriceRequest, cancellationToken As CancellationToken) As Task(Of StockPriceResponse)
            Return GetStockPriceAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetStockPriceAsync(request As StockPriceRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of StockPriceResponse)
            Return Await _httpUtility.PostJsonAsync(Of StockPriceRequest, StockPriceResponse)("/stock-service/get-stock-price/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace