Imports System
Imports System.Net
Imports System.IO
Imports System.Text
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
        Private ReadOnly _httpUtility As DemoNestedHttpUtility

        Public Sub New(baseUrl As String)
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _httpUtility = New DemoNestedHttpUtility(baseUrl)
        End Sub

        Public Function GetStockPrice(request As StockPriceRequest) As StockPriceResponse
            Return GetStockPrice(request, Nothing, Nothing)
        End Function

        Public Function GetStockPrice(request As StockPriceRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As StockPriceResponse
            Return _httpUtility.PostJson(Of StockPriceRequest, StockPriceResponse)("/stock-service/get-stock-price/v1", request, timeoutMs, authHeaders)
        End Function

    End Class

End Namespace