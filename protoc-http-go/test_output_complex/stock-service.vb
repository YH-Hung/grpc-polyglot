Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization
Imports System.Net
Imports System.IO

Namespace Stock

' StockPriceRequest represents the StockPriceRequest message from the proto definition
Public Class StockPriceRequest
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
End Class

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

' StockServiceClient is an HTTP client for the StockService service
Public Class StockServiceClient
    Private ReadOnly _httpUtility As ComplexHttpUtility

    Public Sub New(baseUrl As String)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New ComplexHttpUtility(baseUrl)
    End Sub

    Public Function GetStockPrice(request As StockPriceRequest) As StockPriceResponse
        Return GetStockPrice(request, Nothing, Nothing)
    End Function

    Public Function GetStockPrice(request As StockPriceRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As StockPriceResponse
        Return _httpUtility.PostJson(Of StockPriceRequest, StockPriceResponse)("/stock-service/get-stock-price/v1", request, timeoutMs, authHeaders)
    End Function

End Class

End Namespace
