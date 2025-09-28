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
    Public Property BaseUrl As String

    Public Sub New(baseUrl As String)
        If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
        Me.BaseUrl = baseUrl.TrimEnd("/"c)
    End Sub

    Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp
        If request Is Nothing Then Throw New ArgumentNullException("request")
        Dim url As String = String.Format("{0}/{1}", Me.BaseUrl, relativePath.TrimStart("/"c))
        Dim json As String = JsonConvert.SerializeObject(request)
        Dim data As Byte() = Encoding.UTF8.GetBytes(json)
        Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)
        req.Method = "POST"
        req.ContentType = "application/json"
        req.ContentLength = data.Length
        If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value
        
        ' Add authorization headers if provided
        If authHeaders IsNot Nothing Then
            For Each kvp In authHeaders
                req.Headers.Add(kvp.Key, kvp.Value)
            Next
        End If
        
        Using reqStream As Stream = req.GetRequestStream()
            reqStream.Write(data, 0, data.Length)
        End Using
        Try
            Using resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)
                Using respStream As Stream = resp.GetResponseStream()
                    Using reader As New StreamReader(respStream, Encoding.UTF8)
                        Dim respJson As String = reader.ReadToEnd()
                        If String.IsNullOrWhiteSpace(respJson) Then
                            Throw New InvalidOperationException("Received empty response from server")
                        End If
                        Return JsonConvert.DeserializeObject(Of TResp)(respJson)
                    End Using
                End Using
            End Using
        Catch ex As WebException
            If TypeOf ex.Response Is HttpWebResponse Then
                Using errorResp As HttpWebResponse = CType(ex.Response, HttpWebResponse)
                    Using errorStream As Stream = errorResp.GetResponseStream()
                        If errorStream IsNot Nothing Then
                            Using errorReader As New StreamReader(errorStream, Encoding.UTF8)
                                Dim errorBody As String = errorReader.ReadToEnd()
                                Throw New WebException($"Request failed with status {(CInt(errorResp.StatusCode))} ({errorResp.StatusDescription}): {errorBody}")
                            End Using
                        Else
                            Throw New WebException($"Request failed with status {(CInt(errorResp.StatusCode))} ({errorResp.StatusDescription})")
                        End If
                    End Using
                End Using
            Else
                Throw New WebException($"Request failed: {ex.Message}", ex)
            End If
        End Try
    End Function

    Public Function GetUserInformation(request As UserInformationRequest) As UserInformation
        Return GetUserInformation(request, Nothing, Nothing)
    End Function

    Public Function GetUserInformation(request As UserInformationRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As UserInformation
        Return PostJson(Of UserInformationRequest, UserInformation)("/user-service/get-user-information/v1", request, timeoutMs, authHeaders)
    End Function

    Public Function TradeStock(request As StockTradeRequest) As StockTradeResponse
        Return TradeStock(request, Nothing, Nothing)
    End Function

    Public Function TradeStock(request As StockTradeRequest, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As StockTradeResponse
        Return PostJson(Of StockTradeRequest, StockTradeResponse)("/user-service/trade-stock/v1", request, timeoutMs, authHeaders)
    End Function

End Class

End Namespace
