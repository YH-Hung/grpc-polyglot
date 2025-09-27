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

    Public Class UserInformationRequest
        <JsonProperty("userId")>
        Public Property UserId As Integer

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

    Public Class UserServiceClient
        Private ReadOnly _http As HttpClient
        Private ReadOnly _baseUrl As String

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _http = http
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Private Async Function PostJsonAsync(Of TReq, TResp)(relativePath As String, request As TReq, cancellationToken As CancellationToken) As Task(Of TResp)
            If request Is Nothing Then Throw New ArgumentNullException(NameOf(request))
            Dim url As String = String.Format("{0}/{1}", _baseUrl, relativePath.TrimStart("/"c))
            Dim json As String = JsonConvert.SerializeObject(request)
            Using content As New StringContent(json, Encoding.UTF8, "application/json")
                Dim response As HttpResponseMessage = Await _http.PostAsync(url, content, cancellationToken).ConfigureAwait(False)
                If Not response.IsSuccessStatusCode Then
                    Dim body As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                    Throw New HttpRequestException($"Request failed with status {(CInt(response.StatusCode))} ({response.ReasonPhrase}): {body}")
                End If
                Dim respJson As String = Await response.Content.ReadAsStringAsync().ConfigureAwait(False)
                Return JsonConvert.DeserializeObject(Of TResp)(respJson)
            End Using
        End Function

        Public Function GetUserInformationAsync(request As UserInformationRequest) As Task(Of UserInformation)
            Return GetUserInformationAsync(request, CancellationToken.None)
        End Function

        Public Async Function GetUserInformationAsync(request As UserInformationRequest, cancellationToken As CancellationToken) As Task(Of UserInformation)
            Return Await PostJsonAsync(Of UserInformationRequest, UserInformation)("/user-service/get-user-information/v1", request, cancellationToken).ConfigureAwait(False)
        End Function

        Public Function TradeStockAsync(request As StockTradeRequest) As Task(Of StockTradeResponse)
            Return TradeStockAsync(request, CancellationToken.None)
        End Function

        Public Async Function TradeStockAsync(request As StockTradeRequest, cancellationToken As CancellationToken) As Task(Of StockTradeResponse)
            Return Await PostJsonAsync(Of StockTradeRequest, StockTradeResponse)("/user-service/trade-stock/v1", request, cancellationToken).ConfigureAwait(False)
        End Function

    End Class

End Namespace