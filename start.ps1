# Запуск на Windows: аналог `make dev`. Бэкенд и фронтенд открываются в отдельных окнах,
# закрытие окна останавливает соответствующую часть.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

if (-not (Test-Path backend\.venv\Scripts\python.exe) -or -not (Test-Path frontend\node_modules)) {
  Write-Host 'Сначала выполните установку: .\setup.ps1' -ForegroundColor Red
  exit 1
}
if (-not (Test-Path .env)) { Copy-Item .env.example .env }

# Ollama нужна, только если в «Моделях и провайдерах» выбрана локальная модель,
# но поднять её заранее дешевле, чем потом разбираться, почему анализ висит
try {
  Invoke-RestMethod http://localhost:11434/api/tags -TimeoutSec 5 | Out-Null
  Write-Host 'Ollama уже работает'
} catch {
  if (Get-Command ollama -ErrorAction SilentlyContinue) {
    Write-Host 'Запускаю Ollama...'
    Start-Process ollama -ArgumentList 'serve' -WindowStyle Minimized
  } else {
    Write-Host 'Ollama не установлена — работать будут только внешние провайдеры' -ForegroundColor Yellow
  }
}

Start-Process powershell -WorkingDirectory "$PSScriptRoot\backend" -ArgumentList '-NoExit', '-Command',
  '$Host.UI.RawUI.WindowTitle = ''JobPilot backend''; .\.venv\Scripts\python.exe -m alembic upgrade head; .\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000'

Start-Process powershell -WorkingDirectory "$PSScriptRoot\frontend" -ArgumentList '-NoExit', '-Command',
  '$Host.UI.RawUI.WindowTitle = ''JobPilot frontend''; npm run dev'

Write-Host 'Жду, пока поднимется интерфейс...'
for ($i = 0; $i -lt 60; $i++) {
  try {
    Invoke-WebRequest http://localhost:5173 -UseBasicParsing -TimeoutSec 2 | Out-Null
    Start-Process http://localhost:5173
    Write-Host 'Готово: http://localhost:5173' -ForegroundColor Green
    exit 0
  } catch { Start-Sleep -Seconds 1 }
}
Write-Host 'Интерфейс не ответил за минуту — посмотрите окна JobPilot backend / frontend' -ForegroundColor Yellow
