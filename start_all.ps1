# OpenGold — 1-Click Startup
# Starts: Gold API, Forex API, Gold Bot, Forex Bot, Next.js Dashboard
# Usage: Right-click → "Run with PowerShell"  OR  .\start_all.ps1

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$venv   = "$PSScriptRoot\.venv\Scripts\python.exe"
$uvicorn = "$PSScriptRoot\.venv\Scripts\uvicorn.exe"
$psql   = 'C:\Program Files\PostgreSQL\18\bin\psql.exe'

# ── Banner ────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  ██████╗ ██████╗ ███████╗███╗   ██╗ ██████╗  ██████╗ ██╗     ██████╗ " -ForegroundColor Yellow
Write-Host " ██╔═══██╗██╔══██╗██╔════╝████╗  ██║██╔════╝ ██╔═══██╗██║     ██╔══██╗" -ForegroundColor Yellow
Write-Host " ██║   ██║██████╔╝█████╗  ██╔██╗ ██║██║  ███╗██║   ██║██║     ██║  ██║" -ForegroundColor Yellow
Write-Host " ██║   ██║██╔═══╝ ██╔══╝  ██║╚██╗██║██║   ██║██║   ██║██║     ██║  ██║" -ForegroundColor Yellow
Write-Host " ╚██████╔╝██║     ███████╗██║ ╚████║╚██████╔╝╚██████╔╝███████╗██████╔╝" -ForegroundColor Yellow
Write-Host "  ╚═════╝ ╚═╝     ╚══════╝╚═╝  ╚═══╝ ╚═════╝  ╚═════╝ ╚══════╝╚═════╝ " -ForegroundColor Yellow
Write-Host ""
Write-Host "  AI-Powered Gold & Forex Trading Bot" -ForegroundColor DarkYellow
Write-Host ""

# ── Helpers ───────────────────────────────────────────────────────────────────
function Start-Service($title, $cmd, $args, $env) {
    $psi = New-Object System.Diagnostics.ProcessStartInfo
    $psi.FileName = $cmd
    $psi.Arguments = $args
    $psi.UseShellExecute = $true
    $psi.CreateNoWindow = $false
    if ($env) {
        foreach ($kv in $env.GetEnumerator()) {
            $psi.EnvironmentVariables[$kv.Key] = $kv.Value
        }
    }
    # Open in a new terminal window with a title
    $wrapped = "powershell -NoExit -Command `"& { `$host.UI.RawUI.WindowTitle='$title'; $cmd $args }`""
    Start-Process powershell -ArgumentList "-NoExit", "-Command", "`$host.UI.RawUI.WindowTitle='$title'; Set-Location '$PSScriptRoot'; $cmd $args"
}

# ── 1. Gold API ───────────────────────────────────────────────────────────────
Write-Host "[1/5] Starting Gold API  (port 8000)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
`$host.UI.RawUI.WindowTitle = 'gold api'
Set-Location '$PSScriptRoot'
& '$PSScriptRoot\.venv\Scripts\Activate.ps1'
`$env:ENV_FILE = 'gold.env'
uvicorn src.api.app:app --host 127.0.0.1 --port 8000
"@
Start-Sleep -Seconds 3

# ── 2. Forex API ──────────────────────────────────────────────────────────────
Write-Host "[2/5] Starting Forex API (port 8001)..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
`$host.UI.RawUI.WindowTitle = 'forex api'
Set-Location '$PSScriptRoot'
& '$PSScriptRoot\.venv\Scripts\Activate.ps1'
`$env:ENV_FILE = 'forex.env'
uvicorn src.api.app:app --host 127.0.0.1 --port 8001
"@
Start-Sleep -Seconds 3

# ── 3. Gold Bot ───────────────────────────────────────────────────────────────
Write-Host "[3/5] Starting Gold Bot  (XAUUSDM M1)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
`$host.UI.RawUI.WindowTitle = 'gold bot'
Set-Location '$PSScriptRoot'
& '$PSScriptRoot\.venv\Scripts\Activate.ps1'
python main.py --env gold.env
"@
Start-Sleep -Seconds 2

# ── 4. Forex Bot ──────────────────────────────────────────────────────────────
Write-Host "[4/5] Starting Forex Bot (GBPUSD M5)..." -ForegroundColor Green
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
`$host.UI.RawUI.WindowTitle = 'forex bot'
Set-Location '$PSScriptRoot'
& '$PSScriptRoot\.venv\Scripts\Activate.ps1'
python main.py --env forex.env
"@
Start-Sleep -Seconds 2

# ── 5. Dashboard ──────────────────────────────────────────────────────────────
Write-Host "[5/5] Starting Dashboard (http://localhost:3000)..." -ForegroundColor Magenta
Start-Process powershell -ArgumentList "-NoExit", "-Command", @"
`$host.UI.RawUI.WindowTitle = 'dashboard'
Set-Location '$PSScriptRoot\dashboard'
npm run dev
"@

# ── Done ──────────────────────────────────────────────────────────────────────
Write-Host ""
Write-Host "  All services starting in separate windows." -ForegroundColor White
Write-Host "  Dashboard → http://localhost:3000" -ForegroundColor Yellow
Write-Host "  Gold API  → http://localhost:8000/docs" -ForegroundColor DarkYellow
Write-Host "  Forex API → http://localhost:8001/docs" -ForegroundColor DarkYellow
Write-Host ""
Write-Host "  To stop: close each terminal window individually." -ForegroundColor DarkGray
Write-Host ""

# Keep this window open briefly so user can read the output
Start-Sleep -Seconds 5
