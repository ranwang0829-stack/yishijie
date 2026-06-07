@echo off
echo ==================================
echo 异世界日常系统 - 安装定时任务
echo 每30分钟自动推送（带语音播报）
echo ==================================
echo.

schtasks /create /tn "IsekaiDailyPush" /tr "\"C:\Users\王\Desktop\my web\start_pc_daemon.bat\"" /sc minute /mo 30 /f

echo.
echo 安装完成！
echo 运行 taskschd.msc 可查看定时任务。
echo 运行 schtasks /delete /tn "IsekaiDailyPush" /f 可删除。
pause
