@echo off
chcp 65001 >nul
cd /d "D:\WorkBuddy\Claw\2026-07-16-08-52-07"
python "更新A股行情.py"
echo.
echo 已执行完毕。上方会显示本次更新时间和 8 家公司行情。
echo 也可以打开 "行情更新日志.txt" 查看结果。
pause
