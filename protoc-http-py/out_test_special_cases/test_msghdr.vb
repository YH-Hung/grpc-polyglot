Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace MsghdrTest

    Public Class msgHdr
        <JsonProperty("user_id")>
        Public Property UserId As String

        <JsonProperty("first_name")>
        Public Property FirstName As String

        <JsonProperty("account_number")>
        Public Property AccountNumber As Integer

    End Class

    Public Class RegularMessage
        <JsonProperty("userId")>
        Public Property UserId As String

        <JsonProperty("firstName")>
        Public Property FirstName As String

        <JsonProperty("accountNumber")>
        Public Property AccountNumber As Integer

    End Class

    Public Class OuterMessage
        <JsonProperty("header")>
        Public Property Header As OuterMessage.msgHdr

        <JsonProperty("regularField")>
        Public Property RegularField As String

        Public Class msgHdr
            <JsonProperty("inner_field")>
            Public Property InnerField As String

        End Class

    End Class

    Public Class TestServiceClient
        Private ReadOnly _httpUtility As TestSpecialCasesHttpUtility

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _httpUtility = New TestSpecialCasesHttpUtility(http, baseUrl)
        End Sub

        Public Function ProcessHeaderAsync(request As msgHdr) As Task(Of RegularMessage)
            Return ProcessHeaderAsync(request, CancellationToken.None)
        End Function

        Public Function ProcessHeaderAsync(request As msgHdr, cancellationToken As CancellationToken) As Task(Of RegularMessage)
            Return ProcessHeaderAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function ProcessHeaderAsync(request As msgHdr, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of RegularMessage)
            Return Await _httpUtility.PostJsonAsync(Of msgHdr, RegularMessage)("/test_msghdr/process-header/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace