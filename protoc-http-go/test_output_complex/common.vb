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

Namespace Common

' Ticker represents the Ticker enum from the proto definition
Public Enum Ticker As Integer
    Ticker_MICROSOFT = 4
    Ticker_UNKNOWN = 0
    Ticker_APPLE = 1
    Ticker_GOOGLE = 2
    Ticker_AMAZON = 3
End Enum

End Namespace
