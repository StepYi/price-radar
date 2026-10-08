# =============================================================================
#  PriceRadar 每日一键运行（Windows PowerShell）
#
#  用法：
#     .\run_daily.ps1              # 生成今天的日报
#     .\run_daily.ps1 -Open        # 生成并打开看板
#     .\run_daily.ps1 -Limit 15    # 临时改成 15 篇
#     .\run_daily.ps1 -Email       # 生成后发邮件（需配置 SMTP 环境变量）
#
#  注册成每天 08:30 自动运行（普通 PowerShell 执行一次即可）：
#     $p = "$PWD\run_daily.ps1"
#     schtasks /create /tn "PriceRadar" /tr "powershell -NoProfile -ExecutionPolicy Bypass -File `"$p`"" /sc daily /st 08:30
#  删除：
#     schtasks /delete /tn "PriceRadar" /f
# =============================================================================

[CmdletBinding()]
param(
    [int]$Limit = 0,
    [switch]$Open,
    [switch]$Email,
    [switch]$NoDedup,
    [string]$Date = ""
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root = $PSScriptRoot
Set-Location $root

$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "找不到 python，请先安装 Python 3.11+ 并加入 PATH。" -ForegroundColor Red
    exit 1
}

# 日志文件：方便排查「昨天为什么没推送」
$logDir = Join-Path $root "data\logs"
New-Item -ItemType Directory -Force -Path $logDir | Out-Null
$logFile = Join-Path $logDir ("run-{0}.log" -f (Get-Date -Format "yyyy-MM-dd"))

Write-Host "== PriceRadar 每日运行 $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') ==" -ForegroundColor Cyan

# 首次运行：自动解析期刊
if (-not (Test-Path (Join-Path $root "data\sources_cache.json"))) {
    Write-Host "首次运行，正在解析期刊列表…" -ForegroundColor Yellow
    & python -m priceradar resolve 2>&1 | Tee-Object -FilePath $logFile -Append
    if ($LASTEXITCODE -ne 0) {
        Write-Host "期刊解析失败，请检查网络后重试。" -ForegroundColor Red
        exit 1
    }
}

$pyArgs = @("-m", "priceradar", "run")
if ($Limit -gt 0) { $pyArgs += @("--limit", $Limit) }
if ($Date)        { $pyArgs += @("--date", $Date) }
if ($NoDedup)     { $pyArgs += "--no-dedup" }
if ($Email)       { $pyArgs += "--email" }

& python @pyArgs 2>&1 | Tee-Object -FilePath $logFile -Append
$code = $LASTEXITCODE

if ($code -eq 0) {
    $index = Join-Path $root "data\out\index.html"
    Write-Host ""
    Write-Host "完成 — 看板：$index" -ForegroundColor Green
    if ($Open -and (Test-Path $index)) { Start-Process $index }
} else {
    Write-Host ""
    Write-Host "运行失败（退出码 $code），日志：$logFile" -ForegroundColor Red
}
exit $code
