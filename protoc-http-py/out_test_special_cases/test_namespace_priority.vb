Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace ComExamplePriority

    Public Class NamespaceTest
        <JsonProperty("field")>
        Public Property Field As String

    End Class

    Public Class NamespaceServiceClient
        Private ReadOnly _httpUtility As TestSpecialCasesHttpUtility

        Public Sub New(http As HttpClient, baseUrl As String)
            If http Is Nothing Then Throw New ArgumentNullException(NameOf(http))
            If String.IsNullOrWhiteSpace(baseUrl) Then Throw New ArgumentException("baseUrl cannot be null or empty")
            _httpUtility = New TestSpecialCasesHttpUtility(http, baseUrl)
        End Sub

        Public Function TestCallAsync(request As NamespaceTest) As Task(Of NamespaceTest)
            Return TestCallAsync(request, CancellationToken.None)
        End Function

        Public Function TestCallAsync(request As NamespaceTest, cancellationToken As CancellationToken) As Task(Of NamespaceTest)
            Return TestCallAsync(request, cancellationToken, Nothing)
        End Function

        Public Async Function TestCallAsync(request As NamespaceTest, cancellationToken As CancellationToken, Optional timeoutMs As Integer? = Nothing) As Task(Of NamespaceTest)
            Return Await _httpUtility.PostJsonAsync(Of NamespaceTest, NamespaceTest)("/test_namespace_priority/test-call/v1", request, cancellationToken, timeoutMs).ConfigureAwait(False)
        End Function

    End Class

End Namespace