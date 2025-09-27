Imports System
Imports System.Net
Imports System.IO
Imports System.Text
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
        Private ReadOnly _baseUrl As String

        Public Sub New(baseUrl As String)
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing) As TResp
            If request Is Nothing Then Throw New ArgumentNullException("request")
            Dim url As String = String.Format("{0}/{1}", _baseUrl, relativePath.TrimStart("/"c))
            Dim json As String = JsonConvert.SerializeObject(request)
            Dim data As Byte() = Encoding.UTF8.GetBytes(json)
            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)
            req.Method = "POST"
            req.ContentType = "application/json"
            req.ContentLength = data.Length
            If timeoutMs.HasValue Then req.Timeout = timeoutMs.Value
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
            Return GetUserInformation(request, Nothing)
        End Function

        Public Function GetUserInformation(request As UserInformationRequest, Optional timeoutMs As Integer? = Nothing) As UserInformation
            Return PostJson(Of UserInformationRequest, UserInformation)("/user-service/get-user-information/v1", request, timeoutMs)
        End Function

        Public Function TradeStock(request As StockTradeRequest) As StockTradeResponse
            Return TradeStock(request, Nothing)
        End Function

        Public Function TradeStock(request As StockTradeRequest, Optional timeoutMs As Integer? = Nothing) As StockTradeResponse
            Return PostJson(Of StockTradeRequest, StockTradeResponse)("/user-service/trade-stock/v1", request, timeoutMs)
        End Function

    End Class

End Namespace