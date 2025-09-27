Imports System
Imports System.Net
Imports System.IO
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Stock

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

    Public Class StockPriceResponse
        <JsonProperty("ticker")>
        Public Property Ticker As Common.Ticker

        <JsonProperty("price")>
        Public Property Price As Integer

    End Class

    Public Class StockServiceClient
        Private ReadOnly _baseUrl As String

        Public Sub New(baseUrl As String)
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Private Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq) As TResp
            If request Is Nothing Then Throw New ArgumentNullException("request")
            Dim url As String = String.Format("{0}/{1}", _baseUrl, relativePath.TrimStart("/"c))
            Dim json As String = JsonConvert.SerializeObject(request)
            Dim data As Byte() = Encoding.UTF8.GetBytes(json)
            Dim req As HttpWebRequest = CType(WebRequest.Create(url), HttpWebRequest)
            req.Method = "POST"
            req.ContentType = "application/json"
            req.ContentLength = data.Length
            Using reqStream As Stream = req.GetRequestStream()
                reqStream.Write(data, 0, data.Length)
            End Using
            Dim resp As HttpWebResponse = CType(req.GetResponse(), HttpWebResponse)
            Using respStream As Stream = resp.GetResponseStream()
                Using reader As New StreamReader(respStream, Encoding.UTF8)
                    Dim respJson As String = reader.ReadToEnd()
                    Return JsonConvert.DeserializeObject(Of TResp)(respJson)
                End Using
            End Using
        End Function

        Public Function GetStockPrice(request As StockPriceRequest) As StockPriceResponse
            Return PostJson(Of StockPriceRequest, StockPriceResponse)("/stock-service/get-stock-price/v1", request)
        End Function

    End Class

End Namespace