@echo off
:start
echo Starting the server...
python main.py
echo Server stopped, restarting in 5 seconds...
timeout /t 5
goto start