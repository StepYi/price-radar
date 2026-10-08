# =============================================================================
#  PriceRadar 局域网分享（Windows PowerShell）
#
#  作用：在你的电脑上起一个网页服务器，同事在同一个 WiFi / 办公网里
#        用浏览器打开 http://你的IP:8080 就能看到日报，不用装任何东西。
#
#  用法：
#     .\share.ps1              # 默认 8080 端口
#     .\share.ps1 -Port 9000   # 换端口
#     .\share.ps1 -Local       # 只有本机能访问
#
#  停止：按 Ctrl+C
#  注意：脚本会尝试自动放行防火墙；如果提示失败，请用【管理员】PowerShell
#        跑一次它打印出来的 netsh 命令。
# =============================================================================

[CmdletBinding()]
param(
    [int]$Port = 8080,
    [switch]$Local
)

$ErrorActionPreference = "Stop"
$env:PYTHONIOENCODING = "utf-8"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$root = $PSScriptRoot
Set-Location $root

if (-not (Test-Path (Join-Path $root "data\out\index.html"))) {
    Write-Host "还没有日报，先生成一份…" -ForegroundColor Yellow
    & python -m priceradar run
}

if (-not $Local) {
    # 尝试放行防火墙（需要管理员权限；失败就只给出手动命令，不影响启动）
    $ruleName = "PriceRadar $Port"
    $existing = Get-NetFirewallRule -DisplayName $ruleName -ErrorAction SilentlyContinue
    if (-not $existing) {
        try {
            New-NetFirewallRule -DisplayName $ruleName -Direction Inbound `
                -Action Allow -Protocol TCP -LocalPort $Port -Profile Private -ErrorAction Stop | Out-Null
            Write-Host "已自动放行防火墙端口 $Port（仅专用网络）" -ForegroundColor Green
        } catch {
            Write-Host "自动放行防火墙失败（需要管理员权限）。如同事打不开，请用管理员 PowerShell 执行：" -ForegroundColor Yellow
            Write-Host ('  netsh advfirewall firewall add rule name="' + $ruleName + '" dir=in action=allow protocol=TCP localport=' + $Port) -ForegroundColor Yellow
        }
    }
}

$pyArgs = @("-m", "priceradar", "serve", "--port", $Port, "--open")
if ($Local) { $pyArgs += "--local" }
& python @pyArgs
