@echo off
title Verifiedcart - Grounded Shopping Assistant
echo ========================================================
echo   Verifiedcart - The Conversational Shopping Assistant
echo   100%% Grounded Multi-Stage Architecture
echo ========================================================
echo.
echo Starting Web Server at http://127.0.0.1:8000/ ...
start "" "http://127.0.0.1:8000/"
py server.py 8000
pause

