$ChildPID = Get-Process -ProcessName TestServer.UWP | Select-Object -Expand Id
kill $ChildPID