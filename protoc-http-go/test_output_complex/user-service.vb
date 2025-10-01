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

Namespace User

' TradeAction represents the TradeAction enum from the proto definition
Public Enum TradeAction As Integer
    TradeAction_BUY = 0
    TradeAction_SELL = 1
End Enum

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

' UserServiceClient is an HTTP client for the UserService service
Public Class UserServiceClient
    Private ReadOnly _httpUtility As ComplexHttpUtility

    Public Sub New(baseUrl As String)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        _httpUtility = New ComplexHttpUtility(baseUrl)
    End Sub

    Public Function GetUserInformation(request As UserInformationRequest) As UserInformation
        Return GetUserInformation(request, Nothing, Nothing)
    End Function

    Public Function GetUserInformation(request As UserInformationRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As UserInformation
        Return _httpUtility.PostJson(Of UserInformationRequest, UserInformation)("/user-service/get-user-information/v1", request, timeoutMs, authHeaders)
    End Function

    Public Function TradeStock(request As StockTradeRequest) As StockTradeResponse
        Return TradeStock(request, Nothing, Nothing)
    End Function

    Public Function TradeStock(request As StockTradeRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As StockTradeResponse
        Return _httpUtility.PostJson(Of StockTradeRequest, StockTradeResponse)("/user-service/trade-stock/v1", request, timeoutMs, authHeaders)
    End Function

End Class

End Namespace
