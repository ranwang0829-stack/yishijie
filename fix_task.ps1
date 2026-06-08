$py = $env:LOCALAPPDATA + "\Programs\Python\Python312\python.exe"
$script = (Get-Item ".\run_pc.py").FullName
$workDir = (Get-Item ".").FullName

Write-Host "Python: $py"
Write-Host "Script: $script"
Write-Host "WorkDir: $workDir"

schtasks /delete /tn "IsekaiDailyPush" /f 2>$null

# Escape properly: the /tr value needs embedded quotes around paths with spaces
$action = '""' + $py + '" "' + $script + '""'
schtasks /create /tn "IsekaiDailyPush" /tr $action /sc minute /mo 10 /f

Write-Host "---"
schtasks /query /tn "IsekaiDailyPush" /fo list | findstr "TaskName"
schtasks /run /tn "IsekaiDailyPush"
Write-Host "Task triggered."
