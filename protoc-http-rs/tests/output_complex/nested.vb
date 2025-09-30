Imports System
Imports System.Net.Http
Imports System.Text
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Collections.Generic
Imports Newtonsoft.Json

Namespace DemoNested

    Public Class UsesNested
        <JsonProperty("value")>
        Public Property Value As DemoNestedOuter.Inner

        <JsonProperty("values")>
        Public Property Values As List(Of DemoNestedOuter.Inner)

    End Class

    Public Class Outer
        <JsonProperty("inner")>
        Public Property Inner As DemoNestedOuter.Inner

        <JsonProperty("items")>
        Public Property Items As List(Of DemoNestedOuter.Inner)

        Public Class Inner
            <JsonProperty("name")>
            Public Property Name As String

            <JsonProperty("count")>
            Public Property Count As Integer

        End Class
    End Class

End Namespace