Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization

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
    Public Property BaseUrl As String
    Private ReadOnly _httpClient As HttpClient

    Public Sub New(baseUrl As String)
        Me.BaseUrl = baseUrl
        Me._httpClient = New HttpClient()
    End Sub

    Public Sub New(baseUrl As String, httpClient As HttpClient)
        Me.BaseUrl = baseUrl
        Me._httpClient = httpClient
    End Sub

    ' GetUserInformationAsync calls the GetUserInformation RPC method
    Public Async Function GetUserInformationAsync(request As UserInformationRequest, Optional cancellationToken As CancellationToken = Nothing) As Task(Of UserInformation)
        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }
        Dim reqJson As String = JsonConvert.SerializeObject(request, settings)
        Dim url As String = Me.BaseUrl & "/user-service/get-user-information/" & "v1"
        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)
            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, "application/json")
            httpRequest.Headers.Accept.Clear()
            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue("application/json"))
            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)
            Dim respBody As String = Await response.Content.ReadAsStringAsync()
            If Not response.IsSuccessStatusCode Then
                Throw New HttpRequestException(String.Format("HTTP request failed with status {0}: {1}", CInt(response.StatusCode), respBody))
            End If
            Dim result As UserInformation = JsonConvert.DeserializeObject(Of UserInformation)(respBody, settings)
            Return result
        End Using
    End Function

    ' TradeStockAsync calls the TradeStock RPC method
    Public Async Function TradeStockAsync(request As StockTradeRequest, Optional cancellationToken As CancellationToken = Nothing) As Task(Of StockTradeResponse)
        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }
        Dim reqJson As String = JsonConvert.SerializeObject(request, settings)
        Dim url As String = Me.BaseUrl & "/user-service/trade-stock/" & "v1"
        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)
            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, "application/json")
            httpRequest.Headers.Accept.Clear()
            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue("application/json"))
            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)
            Dim respBody As String = Await response.Content.ReadAsStringAsync()
            If Not response.IsSuccessStatusCode Then
                Throw New HttpRequestException(String.Format("HTTP request failed with status {0}: {1}", CInt(response.StatusCode), respBody))
            End If
            Dim result As StockTradeResponse = JsonConvert.DeserializeObject(Of StockTradeResponse)(respBody, settings)
            Return result
        End Using
    End Function

End Class

End Namespace
