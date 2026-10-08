#!/usr/bin/env bash
# =============================================================================
#  PriceRadar 每日一键运行（Linux / macOS / Git Bash）
#
#  用法：
#     ./run_daily.sh            # 生成今天的日报
#     ./run_daily.sh --open     # 生成并打开看板
#     LIMIT=15 ./run_daily.sh   # 临时改成 15 篇
#
#  crontab 每天 08:30（服务器/树莓派）：
#     30 8 * * * cd /path/to/price-radar && ./run_daily.sh >> data/logs/cron.log 2>&1
# =============================================================================
set -euo pipefail

export PYTHONIOENCODING=utf-8
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PY="${PYTHON:-python3}"
command -v "$PY" >/dev/null 2>&1 || { echo "找不到 $PY，请安装 Python 3.11+"; exit 1; }

mkdir -p data/logs
LOG="data/logs/run-$(date +%F).log"

echo "== PriceRadar $(date '+%F %T') =="

if [ ! -f data/sources_cache.json ]; then
  echo "首次运行，解析期刊列表…"
  "$PY" -m priceradar resolve 2>&1 | tee -a "$LOG"
fi

ARGS=(-m priceradar run)
[ -n "${DATE:-}" ]  && ARGS+=(--date "$DATE")
[ -n "${LIMIT:-}" ] && ARGS+=(--limit "$LIMIT")
[ "${NO_DEDUP:-}" = "1" ] && ARGS+=(--no-dedup)
[ "${EMAIL:-}" = "1" ]    && ARGS+=(--email)

"$PY" "${ARGS[@]}" 2>&1 | tee -a "$LOG"

echo
echo "完成 ✅ 看板：$ROOT/data/out/index.html"
if [ "${OPEN:-}" = "1" ] && command -v xdg-open >/dev/null 2>&1; then
  xdg-open "$ROOT/data/out/index.html" >/dev/null 2>&1 || true
fi
