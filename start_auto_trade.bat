@echo off
chcp 65001 > nul
cd /d D:\Claude\invest\claude-investment-sim

echo ====================================================
echo   Claude Trading Terminal - Schedule Reminder
echo ====================================================
echo.

rem スケジュール状況を確認・表示
.venv\Scripts\python.exe scripts\trade_scheduler.py status

echo.
echo ====================================================
echo   次のステップ:
echo   1. Claude Code を開く
echo   2. /trade と入力して実行する
echo   3. 実行後、スケジューラーが自動で記録します
echo ====================================================
echo.
echo   このバッチはWindows タスクスケジューラーに登録して
echo   毎日 15:30 に実行すると便利です。
echo.
echo   タスクスケジューラー登録コマンド（管理者として実行）:
echo   schtasks /create /tn "Claude Trade Reminder" /tr "D:\Claude\invest\claude-investment-sim\start_auto_trade.bat" /sc WEEKLY /d MON,TUE,WED,THU,FRI /st 15:30
echo.
pause
