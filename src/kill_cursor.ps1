Get-Process | Where-Object {$_.ProcessName -like "Cursor"} | Stop-Process -Force
