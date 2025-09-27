Imports System
Imports System.Net
Imports System.IO
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Helloworld

    Public Class HelloReply
        <JsonProperty("message")>
        Public Property Message As String

    End Class

    Public Class HelloRequest
        <JsonProperty("name")>
        Public Property Name As String

    End Class

    Public Class GreeterClient
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

        Public Function SayHello(request As HelloRequest) As HelloReply
            Return PostJson(Of HelloRequest, HelloReply)("/helloworld/say-hello/v1", request)
        End Function

    End Class

End Namespace