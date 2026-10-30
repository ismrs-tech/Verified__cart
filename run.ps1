Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  Verifiedcart - Grounded Shopping Assistant" -ForegroundColor Green
Write-Host "  5,000 Products · Zero Hallucination Pipeline" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Starting Web Server at http://127.0.0.1:8000/ ..." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8000/"
py server.py 8000

