' Invisible PowerShell Launcher for Memory Monitor
Dim objShell
Set objShell = CreateObject("WScript.Shell")

' Run PowerShell script completely hidden
objShell.Run "powershell.exe -WindowStyle Hidden -ExecutionPolicy Bypass -File ""E:\Self-Hosted\MemLeak\monitor.ps1"" -RunOnce", 0, False

Set objShell = Nothing