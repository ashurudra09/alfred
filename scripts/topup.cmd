@echo off
rem Hourly top-up of the synthetic dataset on Groq's free tier (gpt-oss-120b, 200k tokens/day, refills continuously).
rem Scheduled by: schtasks /Create /SC HOURLY /TN AlfredTopup /TR "<repo>\scripts\topup.cmd"
rem Each run generates until the daily quota stops it. When no batch is left, it rebuilds data\out (validate + mix,
rem needs Ollama running) and deletes its own scheduled task.
cd /d "%~dp0.."
set PYTHONIOENCODING=utf-8
set UV=%LOCALAPPDATA%\Microsoft\WinGet\Links\uv.exe
echo ==== %date% %time% >> data\out\topup_sched.log
"%UV%" run python -u -m data.gen.teacher --providers groq > data\out\topup_last.log 2>&1
type data\out\topup_last.log >> data\out\topup_sched.log
findstr /c:"generating 0 with" data\out\topup_last.log >nul || exit /b 0
echo all batches done, rebuilding dataset >> data\out\topup_sched.log
"%UV%" run python -m data.validate data\out\synthetic.jsonl >> data\out\topup_sched.log 2>&1
"%UV%" run python -m data.mix >> data\out\topup_sched.log 2>&1
"%UV%" run python -m data.dedup --check >> data\out\topup_sched.log 2>&1
schtasks /Delete /TN AlfredTopup /F >> data\out\topup_sched.log 2>&1
