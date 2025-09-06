Imports System
Imports GrpcHttpProxyClient.Helloworld

Module Program
    Sub Main(args As String())
        Dim baseUrl As String = "http://localhost:8080"
        Dim name As String = If(args IsNot Nothing AndAlso args.Length > 0 AndAlso Not String.IsNullOrWhiteSpace(args(0)), args(0), "world")

        Dim client As New GreeterClient(baseUrl)
        Dim request As New HelloRequest With {.Name = name}

        Try
            Dim reply As HelloReply = client.SayHelloAsync(request).GetAwaiter().GetResult()
            If reply IsNot Nothing AndAlso Not String.IsNullOrEmpty(reply.Message) Then
                Console.WriteLine(reply.Message)
            Else
                Console.WriteLine("<empty response>")
            End If
        Catch ex As Exception
            Console.Error.WriteLine($"Request failed: {ex.Message}")
            Environment.ExitCode = 1
        End Try
    End Sub
End Module
