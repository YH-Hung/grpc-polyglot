Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace User

    Public Enum TradeAction
        BUY = 0
        SELL = 1
    End Enum

    Public Class StockTradeResponse
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

        <JsonProperty("quantity")>
        Public Property Quantity As Integer

        <JsonProperty("action")>
        Public Property Action As TradeAction

        <JsonProperty("totalPrice")>
        Public Property TotalPrice As Integer

        <JsonProperty("balance")>
        Public Property Balance As Integer

    End Class

    Public Class UserInformation
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("name")>
        Public Property Name As String

        <JsonProperty("balance")>
        Public Property Balance As Integer

        <JsonProperty("holdings")>
        Public Property Holdings As List(Of Holding)

    End Class

    Public Class Holding
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("quantity")>
        Public Property Quantity As Integer

    End Class

    Public Class UserInformationRequest
        <JsonProperty("userId")>
        Public Property UserId As Integer

    End Class

    Public Class StockTradeRequest
        <JsonProperty("userId")>
        Public Property UserId As Integer

        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

        <JsonProperty("quantity")>
        Public Property Quantity As Integer

        <JsonProperty("action")>
        Public Property Action As TradeAction

    End Class

    Public Class UserServiceClient
        Private ReadOnly _httpUtility As DemoNestedHttpUtility

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _httpUtility = New DemoNestedHttpUtility(http, baseUrl)
        End Sub

        Public Function GetUserInformationAsync(request As UserInformationRequest) As Task(Of UserInformation)
            Return GetUserInformationAsync(request, CancellationToken.None)
        End Function

        Public Function GetUserInformationAsync(request As UserInformationRequest, cancellationToken As CancellationToken) As Task(Of UserInformation)
            Return GetUserInformationAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetUserInformationAsync(request As UserInformationRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of UserInformation)
            Return Await _httpUtility.PostJsonAsync(Of UserInformationRequest, UserInformation)("/user-service/get-user-information/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function TradeStockAsync(request As StockTradeRequest) As Task(Of StockTradeResponse)
            Return TradeStockAsync(request, CancellationToken.None)
        End Function

        Public Function TradeStockAsync(request As StockTradeRequest, cancellationToken As CancellationToken) As Task(Of StockTradeResponse)
            Return TradeStockAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function TradeStockAsync(request As StockTradeRequest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of StockTradeResponse)
            Return Await _httpUtility.PostJsonAsync(Of StockTradeRequest, StockTradeResponse)("/user-service/trade-stock/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace