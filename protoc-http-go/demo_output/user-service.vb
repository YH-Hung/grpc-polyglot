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

Namespace User

' TradeAction represents the TradeAction enum from the proto definition
Public Enum TradeAction As Integer
    TradeAction_BUY = 0
    TradeAction_SELL = 1
End Enum

' StockTradeResponse represents the StockTradeResponse message from the proto definition
Public Class StockTradeResponse
    <JsonProperty("userId")>
    Public Property UserId As Integer
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
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

' UserInformationRequest represents the UserInformationRequest message from the proto definition
Public Class UserInformationRequest
    <JsonProperty("userId")>
    Public Property UserId As Integer
End Class

' UserInformation represents the UserInformation message from the proto definition
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

' Holding represents the Holding message from the proto definition
Public Class Holding
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
    <JsonProperty("quantity")>
    Public Property Quantity As Integer
End Class

' StockTradeRequest represents the StockTradeRequest message from the proto definition
Public Class StockTradeRequest
    <JsonProperty("userId")>
    Public Property UserId As Integer
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
    <JsonProperty("price")>
    Public Property Price As Integer
    <JsonProperty("quantity")>
    Public Property Quantity As Integer
    <JsonProperty("action")>
    Public Property Action As TradeAction
End Class

' UserServiceClient is an HTTP client for the UserService service
Public Class UserServiceClient
    Private ReadOnly _httpUtility As ComplexHttpUtility

    Public Sub New(httpClient As HttpClient, baseUrl As String)
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New ComplexHttpUtility(httpClient, baseUrl)
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
