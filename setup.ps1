# Первичная установка на Windows: аналог `make setup`, потому что make в Windows обычно нет.
# Повторный запуск безопасен: уже установленное просто обновится.
$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

function Need($cmd, $hint) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) {
    Write-Host "Не найден $cmd. $hint" -ForegroundColor Red
    exit 1
  }
}

Need 'py' 'Установите Python 3.12: winget install Python.Python.3.12'
Need 'npm' 'Установите Node.js: winget install OpenJS.NodeJS.LTS'
if (-not (Get-Command ollama -ErrorAction SilentlyContinue)) {
  Write-Host 'Ollama не найдена — локальная модель работать не будет, только внешние провайдеры' -ForegroundColor Yellow
}

if (-not (Test-Path .env)) { Copy-Item .env.example .env; Write-Host 'Создан .env' }
New-Item -ItemType Directory -Force data, data\browser, data\screenshots, data\backups, data\exports | Out-Null

$py = 'backend\.venv\Scripts\python.exe'
Write-Host '-> Python-окружение'
if (-not (Test-Path $py)) { py -3.12 -m venv backend\.venv }
& $py -m pip install -q --upgrade pip
& $py -m pip install -q -r backend\requirements.txt

# Chromium нужен только как запасной вариант: на Windows бот берёт установленный Chrome или Edge
Write-Host '-> Chromium для Playwright'
& $py -m playwright install chromium

Write-Host '-> Зависимости фронтенда'
npm ci --prefix frontend --silent

Write-Host '-> Миграции'
Push-Location backend
& .\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location

Write-Host ''
Write-Host 'Готово. Запуск: .\start.ps1' -ForegroundColor Green
