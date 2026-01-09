Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace N2test

    Public Class Request
        <JsonProperty("field")>
        Public Property Field As String

    End Class

    Public Class Response
        <JsonProperty("result")>
        Public Property Result As String

    End Class

    Public Class N2TestServiceClient
        Private ReadOnly _httpUtility As TestSpecialCasesHttpUtility

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _httpUtility = New TestSpecialCasesHttpUtility(http, baseUrl)
        End Sub

        Public Function GetN2DataAsync(request As Request) As Task(Of Response)
            Return GetN2DataAsync(request, CancellationToken.None)
        End Function

        Public Function GetN2DataAsync(request As Request, cancellationToken As CancellationToken) As Task(Of Response)
            Return GetN2DataAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetN2DataAsync(request As Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of Response)
            Return Await _httpUtility.PostJsonAsync(Of Request, Response)("/test_n2_kebab/get-n2-data/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function N2ServiceCallAsync(request As Request) As Task(Of Response)
            Return N2ServiceCallAsync(request, CancellationToken.None)
        End Function

        Public Function N2ServiceCallAsync(request As Request, cancellationToken As CancellationToken) As Task(Of Response)
            Return N2ServiceCallAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function N2ServiceCallAsync(request As Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of Response)
            Return Await _httpUtility.PostJsonAsync(Of Request, Response)("/test_n2_kebab/n2-service-call/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function FetchN2Async(request As Request) As Task(Of Response)
            Return FetchN2Async(request, CancellationToken.None)
        End Function

        Public Function FetchN2Async(request As Request, cancellationToken As CancellationToken) As Task(Of Response)
            Return FetchN2Async(request, cancellationToken, Nothing)
        End Function

        Public Async Function FetchN2Async(request As Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of Response)
            Return Await _httpUtility.PostJsonAsync(Of Request, Response)("/test_n2_kebab/fetch-n2/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function N2ToN2SyncAsync(request As Request) As Task(Of Response)
            Return N2ToN2SyncAsync(request, CancellationToken.None)
        End Function

        Public Function N2ToN2SyncAsync(request As Request, cancellationToken As CancellationToken) As Task(Of Response)
            Return N2ToN2SyncAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function N2ToN2SyncAsync(request As Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of Response)
            Return Await _httpUtility.PostJsonAsync(Of Request, Response)("/test_n2_kebab/n2-to-n2-sync/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

        Public Function GetN3DataAsync(request As Request) As Task(Of Response)
            Return GetN3DataAsync(request, CancellationToken.None)
        End Function

        Public Function GetN3DataAsync(request As Request, cancellationToken As CancellationToken) As Task(Of Response)
            Return GetN3DataAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function GetN3DataAsync(request As Request, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of Response)
            Return Await _httpUtility.PostJsonAsync(Of Request, Response)("/test_n2_kebab/get-n-3-data/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace