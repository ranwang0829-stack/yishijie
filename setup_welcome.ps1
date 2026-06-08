$action = New-ScheduledTaskAction -Execute "C:\Users\王\AppData\Local\Programs\Python\Python312\python.exe" -Argument "C:\Users\王\Desktop\my web\welcome.py"
$trigger = New-ScheduledTaskTrigger -AtStartup
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable
Register-ScheduledTask -TaskName "IsekaiWelcome" -Action $action -Trigger $trigger -Settings $settings -Description "Isekai startup welcome voice" -Force
Write-Host "Done!"
