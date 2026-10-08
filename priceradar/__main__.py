"""命令行入口。

    python -m priceradar resolve      # 解析期刊 → OpenAlex ID（首次必跑）
    python -m priceradar doctor       # 体检：网络、解析、抓取是否正常
    python -m priceradar run          # 生成今天的日报
    python -m priceradar run --open   # 生成并直接打开看板
    python -m priceradar serve        # 起一个本地服务器，分享给局域网同事
    python -m priceradar stats        # 看历史推送记录
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

from . import __version__
from .config import OUT_DIR, load_config
from .pipeline import log, run
from .sources import attach_resolved, resolve_journals
from .store import Store


def cmd_resolve(args: argparse.Namespace) -> int:
    cfg = load_config()
    log(f"解析 {len(cfg.journals)} 本期刊（refresh={args.refresh}）…")
    cache = resolve_journals(
        cfg, refresh=args.refresh, verbose=lambda m: log("  " + m)
    )
    missing = [j.name for j in cfg.journals if j.name not in cache]
    log(f"完成：成功 {len(cache)} / {len(cfg.journals)}")
    if missing:
        log("未解析：" + "、".join(missing))
        log("可在 config.toml 里手动填 issn 钉住正确期刊。")
    return 0 if not missing else 2


def cmd_doctor(args: argparse.Namespace) -> int:
    cfg = load_config()
    attach_resolved(cfg)
    log(f"PriceRadar v{__version__}")
    log(
        f"期刊 {len(cfg.journals)} 本 ｜ 每日 {cfg.digest_size} 篇 ｜ 窗口 {cfg.lookback_days} 天\n"
        f"数据源：Crossref={cfg.use_crossref} RSS={cfg.use_rss} "
        f"S2={cfg.use_semanticscholar} OpenAlex={cfg.use_openalex}"
        + ("（已配 Key）" if cfg.openalex_api_key else "（未配 Key，额度受限）")
    )
    problems = 0
    for journal in cfg.journals:
        ok = bool(journal.issn or journal.rss_url)
        if not ok:
            problems += 1
        rss = " +RSS" if journal.rss_url else ""
        log(
            f"  [{'OK ' if ok else '未解析'}] {journal.name:<46} "
            f"{(journal.issn[0] if journal.issn else '-'):<11}{rss:<6} {journal.publisher}"
        )
    if args.fetch:
        from .sources import fetch_crossref

        log(f"\n试抓取最近 {cfg.lookback_days} 天（只看数量）：")
        today = dt.date.today()
        for journal in cfg.journals[: args.fetch]:
            if not journal.issn:
                continue
            try:
                works = fetch_crossref(journal, cfg, today)
                withabs = sum(1 for w in works if w.get("abstract"))
                log(f"  {journal.name:<46} {len(works):>3} 篇（含摘要 {withabs}）")
            except Exception as exc:
                log(f"  {journal.name:<46} 失败：{exc}")
                problems += 1
    if problems:
        log(f"\n发现 {problems} 个问题，先跑 `python -m priceradar resolve`。")
        return 2
    log("\n一切正常。")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    run_date = dt.date.fromisoformat(args.date) if args.date else dt.date.today()
    digest = run(
        run_date=run_date,
        limit=args.limit,
        out_dir=Path(args.out) if args.out else OUT_DIR,
        no_dedup=args.no_dedup,
        dry_run=args.dry_run,
        no_fetch=args.no_fetch,
        no_enrich=args.no_enrich,
        force=args.force,
        cache_candidates=Path(args.candidates) if args.candidates else None,
        open_after=args.open,
    )
    if args.email:
        from .mailer import send_digest

        ok, message = send_digest(digest, OUT_DIR)
        log(("邮件已发送：" if ok else "邮件未发送：") + message)
    if args.json_out:
        print(json.dumps(digest, ensure_ascii=False, indent=2))
    return 0


def cmd_stats(args: argparse.Namespace) -> int:
    store = Store()
    log("最近运行：")
    for row in store.runs(args.limit):
        log(
            f"  {row['run_date']}  抓取 {row['fetched']:>4}  候选 {row['candidates']:>4}  "
            f"推送 {row['pushed']:>2}"
        )
    log("\n最近推送：")
    for row in store.history(args.limit * 3):
        log(f"  {row['pushed_date']}  [{row['score']:>5.1f}]  {row['journal']:<42} {row['title'][:64]}")
    store.close()
    return 0


def cmd_serve(args: argparse.Namespace) -> int:
    """启动本地静态服务器，让同局域网的同事也能打开看板。"""
    from .server import serve

    out_dir = Path(args.out) if args.out else OUT_DIR
    serve(
        out_dir,
        port=args.port,
        bind_all=not args.local,
        open_browser=args.open,
        log=log,
    )
    return 0


def cmd_rebuild(args: argparse.Namespace) -> int:
    """用已存档的 JSON 重新渲染 HTML（改了样式/模板后不用重新抓取）。"""
    from .render import write_outputs

    out_dir = Path(args.out) if args.out else OUT_DIR
    jsons = sorted(out_dir.glob("[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9].json"))
    if not jsons:
        log("没有找到任何日报 JSON。")
        return 1
    store = Store()
    history = [
        {"date": r["run_date"], "pushed": r["pushed"] or 0} for r in store.runs(60)
    ]
    store.close()
    cfg = load_config()
    for path in jsons:
        digest = json.loads(path.read_text(encoding="utf-8"))
        write_outputs(
            digest,
            out_dir,
            history,
            public_url=cfg.public_url,
            site_title=cfg.site_title,
        )
        log(f"重建 {path.name}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="priceradar",
        description="每日顶刊价格研究文献雷达",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--version", action="version", version=__version__)
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("resolve", help="解析期刊名 → OpenAlex source id")
    p.add_argument("--refresh", action="store_true", help="忽略缓存，强制重新解析")
    p.set_defaults(func=cmd_resolve)

    p = sub.add_parser("doctor", help="环境与解析体检")
    p.add_argument("--fetch", type=int, default=0, help="顺带试抓取前 N 本期刊")
    p.set_defaults(func=cmd_doctor)

    p = sub.add_parser("run", help="生成日报")
    p.add_argument("--date", help="指定日期 YYYY-MM-DD（默认今天）")
    p.add_argument("--limit", type=int, help="推送篇数，默认取 config 的 digest_size")
    p.add_argument("--out", help="输出目录")
    p.add_argument("--no-dedup", action="store_true", help="忽略历史库，允许重复推送")
    p.add_argument("--dry-run", action="store_true", help="只预览，不写库不出文件")
    p.add_argument("--open", action="store_true", help="生成后用浏览器打开")
    p.add_argument("--email", action="store_true", help="生成后发送邮件（需配置环境变量）")
    p.add_argument("--json-out", action="store_true", help="把日报 JSON 打到标准输出")
    p.add_argument("--no-fetch", action="store_true", help="不抓取，配合 --candidates 用离线候选池")
    p.add_argument("--no-enrich", action="store_true", help="跳过摘要补充（Semantic Scholar / OpenAlex）")
    p.add_argument("--force", action="store_true", help="即使当天已生成过日报也重新生成（会覆盖）")
    p.add_argument("--candidates", help="候选池 JSON 路径（写入或读取）")
    p.set_defaults(func=cmd_run)

    p = sub.add_parser("stats", help="查看历史")
    p.add_argument("--limit", type=int, default=14)
    p.set_defaults(func=cmd_stats)

    p = sub.add_parser("serve", help="启动本地服务器，分享给局域网同事")
    p.add_argument("-p", "--port", type=int, default=8080, help="端口，默认 8080")
    p.add_argument("-l", "--local", action="store_true", help="只允许本机访问（默认允许局域网）")
    p.add_argument("-o", "--open", action="store_true", help="同时用浏览器打开")
    p.add_argument("--out", help="日报目录")
    p.set_defaults(func=cmd_serve)

    p = sub.add_parser("rebuild", help="用存档 JSON 重新渲染 HTML")
    p.add_argument("--out", help="输出目录")
    p.set_defaults(func=cmd_rebuild)

    args = parser.parse_args(argv)
    if not getattr(args, "func", None):
        parser.print_help()
        return 1
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
