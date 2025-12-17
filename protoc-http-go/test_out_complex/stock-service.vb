Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks

Namespace Stock

' StockPriceResponse represents the StockPriceResponse message from the proto definition
Public Class StockPriceResponse
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
    <JsonProperty("price")>
    Public Property Price As Integer
End Class

' PriceUpdate represents the PriceUpdate message from the proto definition
Public Class PriceUpdate
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
    <JsonProperty("price")>
    Public Property Price As Integer
End Class

' StockPriceRequest represents the StockPriceRequest message from the proto definition
Public Class StockPriceRequest
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
End Class

' StockServiceClient is an HTTP client for the StockService service
Public Class StockServiceClient
    Private ReadOnly _httpUtility As ComplexHttpUtility

    Public Sub New(httpClient As HttpClient, baseUrl As String)
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New ComplexHttpUtility(httpClient, baseUrl)
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
