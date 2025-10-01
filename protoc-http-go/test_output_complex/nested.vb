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

Namespace Demo.Nested

' Outer represents the Outer message from the proto definition
Public Class Outer
    <JsonProperty("name")>
    Public Property Name As String
    <JsonProperty("count")>
    Public Property Count As Integer
    <JsonProperty("inner")>
    Public Property Inner As Inner
    <JsonProperty("items")>
    Public Property Items As List(Of Inner)
End Class

' Outer_Inner represents the Inner message from the proto definition
Public Class Outer_Inner
    <JsonProperty("name")>
    Public Property Name As String
    <JsonProperty("count")>
    Public Property Count As Integer
End Class

' Inner represents the Inner message from the proto definition
Public Class Inner
    <JsonProperty("name")>
    Public Property Name As String
    <JsonProperty("count")>
    Public Property Count As Integer
End Class

' UsesNested represents the UsesNested message from the proto definition
Public Class UsesNested
    <JsonProperty("value")>
    Public Property Value As Outer_Inner
    <JsonProperty("values")>
    Public Property Values As List(Of Outer_Inner)
End Class

End Namespace
