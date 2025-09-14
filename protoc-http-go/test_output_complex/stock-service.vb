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

Namespace Stock

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

' StockPriceResponse represents the StockPriceResponse message from the proto definition
Public Class StockPriceResponse
    <JsonProperty("ticker")>
    Public Property Ticker As Common_Ticker
    <JsonProperty("price")>
    Public Property Price As Integer
End Class

' StockServiceClient is an HTTP client for the StockService service
Public Class StockServiceClient
    Public Property BaseUrl As String
    Private ReadOnly _httpClient As HttpClient

    Public Sub New(baseUrl As String, httpClient As HttpClient)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        If httpClient Is Nothing Then Throw New ArgumentNullException(NameOf(httpClient))
        Me.BaseUrl = baseUrl
        Me._httpClient = httpClient
    End Sub

    ' GetStockPriceAsync calls the GetStockPrice RPC method
    Public Async Function GetStockPriceAsync(request As StockPriceRequest, Optional cancellationToken As CancellationToken = Nothing) As Task(Of StockPriceResponse)
        Dim settings As New JsonSerializerSettings() With { .ContractResolver = New CamelCasePropertyNamesContractResolver() }
        Dim reqJson As String = JsonConvert.SerializeObject(request, settings)
        Dim url As String = Me.BaseUrl & "/stock-service/get-stock-price/" & "v1"
        Using httpRequest As New HttpRequestMessage(HttpMethod.Post, url)
            httpRequest.Content = New StringContent(reqJson, Encoding.UTF8, "application/json")
            httpRequest.Headers.Accept.Clear()
            httpRequest.Headers.Accept.Add(New MediaTypeWithQualityHeaderValue("application/json"))
            Dim response As HttpResponseMessage = Await _httpClient.SendAsync(httpRequest, cancellationToken)
            Dim respBody As String = Await response.Content.ReadAsStringAsync()
            If Not response.IsSuccessStatusCode Then
                Throw New HttpRequestException(String.Format("HTTP request failed with status {0}: {1}", CInt(response.StatusCode), respBody))
            End If
            Dim result As StockPriceResponse = JsonConvert.DeserializeObject(Of StockPriceResponse)(respBody, settings)
            Return result
        End Using
    End Function

End Class

End Namespace
