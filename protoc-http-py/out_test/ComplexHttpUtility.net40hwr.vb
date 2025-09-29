Imports System
Imports System.Net
Imports System.IO
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace Complex

    Public Class ComplexHttpUtility
        Private ReadOnly _baseUrl As String

        Public Sub New(baseUrl As String)
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _baseUrl = baseUrl.TrimEnd("/"c)
        End Sub

        Public Function PostJson(Of TReq, TResp)(relativePath As String, request As TReq, Optional timeoutMs As Integer? = Nothing, Optional authHeaders As Dictionary(Of String, String) = Nothing) As TResp
            If request Is Nothing Then Throw New ArgumentNullException("request")
            Dim url As String = String.Format("{0}/{1}", _baseUrl, relativePath.TrimStart("/"c))
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
    End Class

End Namespace