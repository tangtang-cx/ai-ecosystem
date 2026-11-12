<#
  Keep the two public demo links alive (supervisor).

    qoder      : http://127.0.0.1:8601 -> https://<random>.trycloudflare.com
    modelscope : http://127.0.0.1:8602 -> https://<random>.trycloudflare.com

  Every process is created through WMI (Win32_Process.Create) so that it is not
  a child of the calling shell: otherwise the whole tree is killed when the
  session that started it goes away.  The absolute python path is used because
  WMI-created processes do not inherit the interactive PATH.

  The app folders are reached through ASCII junctions (tools/app_qoder,
  tools/app_modelscope) because this file is ASCII-only and Windows PowerShell
  5.1 decodes .ps1 files as ANSI unless a BOM is present.

  Start detached:
    powershell -ExecutionPolicy Bypass -NoProfile -WindowStyle Hidden -File tools/serve_public_links.ps1

  Stop everything:
    powershell -ExecutionPolicy Bypass -NoProfile -File tools/serve_public_links.ps1 -Stop
#>
param(
  [switch]$Stop
)

$ErrorActionPreference = "Continue"
$Root = Split-Path -Parent $PSScriptRoot
$LogDir = Join-Path $env:TEMP "opencode"
$LinksFile = Join-Path $Root "tools\public_links.txt"
$Cloudflared = Join-Path $LogDir "cloudflared.exe"
$Python = "D:\python222\python.exe"

if (-not (Test-Path -LiteralPath $LogDir)) { New-Item -ItemType Directory -Path $LogDir | Out-Null }

$Apps = @(
  @{ Name = "qoder";      Dir = "$Root\tools\app_qoder";      Port = 8601 },
  @{ Name = "modelscope"; Dir = "$Root\tools\app_modelscope"; Port = 8602 }
)

function Wmi-Start($commandLine) {
  try {
    $null = Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $commandLine}
  } catch {
    Write-Output "spawn failed: $($_.Exception.Message)"
  }
}

function Stop-All {
  Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
    Where-Object { $_.CommandLine -match "streamlit run app.py" } |
    ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
  Write-Output "stopped"
}

if ($Stop) { Stop-All; exit 0 }

foreach ($app in $Apps) {
  if (-not (Test-Path -LiteralPath (Join-Path $app.Dir "app.py"))) {
    Write-Output "missing app dir: $($app.Dir) (create the junction first)"
    exit 1
  }
}
if (-not (Test-Path -LiteralPath $Cloudflared)) {
  Write-Output "cloudflared missing at $Cloudflared"
  exit 1
}
if (-not (Test-Path -LiteralPath $Python)) {
  Write-Output "python missing at $Python"
  exit 1
}

function Start-App($app) {
  # NOTE: no quotes around the executable/log paths. "cmd /c" strips the outer
  # quotes of the whole command line, which breaks a quoted executable path.
  $log = Join-Path $LogDir "$($app.Name)_app.log"
  $cmd = "cmd.exe /c cd /d $($app.Dir) && $Python -m streamlit run app.py " +
         "--server.headless true --server.port $($app.Port) --browser.gatherUsageStats false > $log 2>&1"
  Wmi-Start $cmd
}

function Start-Tunnel($app) {
  $log = Join-Path $LogDir "$($app.Name)_cf.log"
  $cmd = "cmd.exe /c $Cloudflared tunnel --url http://127.0.0.1:$($app.Port) --no-autoupdate > $log 2>&1"
  Wmi-Start $cmd
}

function Get-TunnelUrl($name) {
  $log = Join-Path $LogDir "${name}_cf.log"
  if (-not (Test-Path -LiteralPath $log)) { return $null }
  $hit = Select-String -Path $log -Pattern "https://[a-z0-9-]+\.trycloudflare\.com" -ErrorAction SilentlyContinue |
    Select-Object -Last 1
  if ($hit) { return $hit.Matches[0].Value }
  return $null
}

function Test-Local($port) {
  try {
    $null = Invoke-WebRequest -Uri "http://127.0.0.1:$port" -UseBasicParsing -TimeoutSec 5
    return $true
  } catch { return $false }
}

foreach ($app in $Apps) {
  if (-not (Test-Local $app.Port)) { Start-App $app }
}
Start-Sleep -Seconds 14
foreach ($app in $Apps) { Start-Tunnel $app }

while ($true) {
  foreach ($app in $Apps) {
    if (-not (Test-Local $app.Port)) {
      Write-Output "$(Get-Date -Format HH:mm:ss) restarting app $($app.Name)"
      Start-App $app
      Start-Sleep -Seconds 12
    }
    $tunnels = Get-CimInstance Win32_Process -Filter "Name='cloudflared.exe'" |
      Where-Object { $_.CommandLine -match "$($app.Port)" }
    if (-not $tunnels) {
      Write-Output "$(Get-Date -Format HH:mm:ss) restarting tunnel $($app.Name)"
      Start-Tunnel $app
      Start-Sleep -Seconds 8
    }
  }

  $lines = foreach ($app in $Apps) {
    $url = Get-TunnelUrl $app.Name
    if ($url) { "$($app.Name)`t$url`thttp://127.0.0.1:$($app.Port)" }
  }
  if ($lines) { Set-Content -LiteralPath $LinksFile -Value $lines -Encoding UTF8 }
  Start-Sleep -Seconds 20
}
