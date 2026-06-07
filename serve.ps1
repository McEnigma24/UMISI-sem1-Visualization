Set-Location $PSScriptRoot
Write-Host "Serwer: http://localhost:8000/index.html"
python -m http.server 8000
