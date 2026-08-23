<#
.SYNOPSIS
    Поднимает локальный стенд TazaBAK: backend и интерфейс.

.DESCRIPTION
    Оба сервера слушают 0.0.0.0, иначе ESP32 из той же сети до них не
    достучится — самая частая причина «HTTP=-1» в мониторе порта.

    Скрипт печатает IP ноутбука: именно его нужно вписать в BACKEND_HOST
    прошивки. Адрес меняется при переподключении к Wi-Fi, поэтому смотреть
    его лучше перед каждым показом, а не помнить.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File scripts\start-local.ps1
#>

$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host ''
Write-Host '  TazaBAK — локальный стенд' -ForegroundColor Green
Write-Host ''

# Адрес в локальной сети. Берём первый работающий адаптер, исключая петлевой
# и виртуальные подсети Docker/WSL — вписав их в прошивку, плата стучалась бы
# в никуда.
$lanIp = (Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -ne '127.0.0.1' -and
        $_.PrefixOrigin -ne 'WellKnown' -and
        $_.IPAddress -notlike '172.1*' -and
        $_.IPAddress -notlike '169.254.*'
    } |
    Select-Object -First 1 -ExpandProperty IPAddress)

if (-not $lanIp) { $lanIp = 'не определён — посмотрите ipconfig' }

$venvPython = Join-Path $root '.venv\Scripts\python.exe'
if (-not (Test-Path $venvPython)) {
    Write-Host '  Виртуальное окружение не найдено: .venv' -ForegroundColor Red
    Write-Host '  Создайте его:  python -m venv .venv'
    Write-Host '  и поставьте зависимости:  .venv\Scripts\pip install -r requirements.txt'
    exit 1
}

if (-not (Test-Path (Join-Path $root 'frontend\node_modules'))) {
    Write-Host '  Ставлю зависимости интерфейса (один раз)...' -ForegroundColor Yellow
    Push-Location (Join-Path $root 'frontend')
    npm install
    Pop-Location
}

Write-Host '  Запускаю backend на порту 8000...' -ForegroundColor Cyan
Start-Process -FilePath $venvPython `
    -ArgumentList '-m', 'uvicorn', 'app.main:app', '--host', '0.0.0.0', '--port', '8000' `
    -WorkingDirectory $root

Write-Host '  Запускаю интерфейс на порту 5173...' -ForegroundColor Cyan
Start-Process -FilePath 'cmd.exe' `
    -ArgumentList '/c', 'npm run dev -- --host 0.0.0.0' `
    -WorkingDirectory (Join-Path $root 'frontend')

Start-Sleep -Seconds 6

Write-Host ''
Write-Host '  Открыть на этом компьютере:' -ForegroundColor Green
Write-Host '    интерфейс   http://localhost:5173'
Write-Host '    API         http://localhost:8000/docs'
Write-Host ''
Write-Host '  Открыть с телефона в той же сети:' -ForegroundColor Green
Write-Host "    http://${lanIp}:5173"
Write-Host ''
Write-Host '  В прошивку ESP32 вписать:' -ForegroundColor Yellow
Write-Host "    constexpr char BACKEND_HOST[] = `"$lanIp`";"
Write-Host '    #define TAZABAK_CLOUD 0'
Write-Host ''
Write-Host '  Вход диспетчера: dispatcher-1 / 123, ключ 123' -ForegroundColor Green
Write-Host '  Проверка стенда: .venv\Scripts\python.exe scripts\check-local.py'
Write-Host ''
