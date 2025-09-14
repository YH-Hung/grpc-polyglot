Option Strict On
Option Explicit On
Option Infer On

Imports System
Imports System.Net.Http
Imports System.Net.Http.Headers
Imports System.Threading
Imports System.Threading.Tasks
Imports System.Text
Imports System.Collections.Generic
Imports Newtonsoft.Json
Imports Newtonsoft.Json.Serialization

Namespace Common

' Ticker represents the Ticker enum from the proto definition
Public Enum Ticker As Integer
    Ticker_UNKNOWN = 0
    Ticker_APPLE = 1
    Ticker_GOOGLE = 2
    Ticker_AMAZON = 3
    Ticker_MICROSOFT = 4
End Enum

End Namespace
