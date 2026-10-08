"""主流程：抓取 → 合并 → 去重 → 补摘要 → 打分 → 选 10 篇 → 存档 → 渲染。"""

from __future__ import annotations

import datetime as dt
import json
import time
from pathlib import Path

from .config import Config, OUT_DIR, load_config
from .render import write_outputs
from .score import Scored, Scorer, dedupe, passes_gate
from .sources import (
    attach_resolved,
    enrich_with_openalex,
    enrich_with_semantic_scholar,
    fetch_crossref,
    fetch_rss,
    merge_supplement,
    resolve_journals,
)
from .store import Store, title_fingerprint


def log(msg: str) -> None:
    print(msg, flush=True)


# --------------------------------------------------------------------------- #
# 选片
# --------------------------------------------------------------------------- #
def select_top(
    scored: list[Scored], cfg: Config, size: int, max_per_journal: int
) -> tuple[list[Scored], dict]:
    """严格门槛 + 每刊限额优先；凑不满时逐级放宽，保证每天都发得出来。"""
    scored = [s for s in scored if not s.excluded]
    scored.sort(
        key=lambda s: (
            -s.score,
            -int(s.work.get("cited_by_count") or 0),
            s.work.get("title", ""),
        )
    )

    notes: dict = {"strict_pool": 0, "cap_relaxed": False, "relaxed": False, "filled": False}

    strict = [s for s in scored if passes_gate(s, cfg, strict=True)]
    relaxed = [s for s in scored if passes_gate(s, cfg, strict=False)]
    notes["strict_pool"] = len(strict)
    notes["relaxed_pool"] = len(relaxed)

    chosen: list[Scored] = []
    used: set[str] = set()

    def take(pool: list[Scored], cap: int) -> None:
        per_journal: dict[str, int] = {}
        for s in chosen:
            j = s.work.get("journal", "")
            per_journal[j] = per_journal.get(j, 0) + 1
        for s in pool:
            if len(chosen) >= size:
                return
            wid = s.work.get("id")
            if wid in used:
                continue
            journal = s.work.get("journal", "")
            if per_journal.get(journal, 0) >= cap:
                continue
            chosen.append(s)
            used.add(wid)
            per_journal[journal] = per_journal.get(journal, 0) + 1

    take(strict, max_per_journal)                       # 1. 严格 + 限额
    if len(chosen) < size:
        before = len(chosen)
        take(strict, 999)                               # 2. 严格 + 去限额
        notes["cap_relaxed"] = len(chosen) > before
    if len(chosen) < size:
        before = len(chosen)
        take(relaxed, 999)                              # 3. 放宽门槛
        notes["relaxed"] = len(chosen) > before
    if len(chosen) < size:
        before = len(chosen)
        take(scored, 999)                               # 4. 有什么推什么
        notes["filled"] = len(chosen) > before

    chosen.sort(key=lambda s: -s.score)
    return chosen[:size], notes


# --------------------------------------------------------------------------- #
# 抓取
# --------------------------------------------------------------------------- #
def collect(cfg: Config, today: dt.date) -> tuple[list[dict], dict]:
    journals = [j for j in cfg.journals if j.enabled and (j.issn or j.rss_url)]
    if not journals:
        raise SystemExit("没有可用期刊。请先运行：python -m priceradar resolve")

    all_works: list[dict] = []
    per_journal: dict[str, dict] = {}
    total = len(journals)

    for idx, journal in enumerate(journals, 1):
        works: list[dict] = []
        note = ""
        if cfg.use_crossref and journal.issn:
            try:
                works = fetch_crossref(journal, cfg, today)
            except Exception as exc:
                note = f"Crossref 失败：{exc}"
        if cfg.use_rss and journal.rss_url:
            try:
                rss = fetch_rss(journal, cfg, today)
                works = merge_supplement(works, rss) if works else rss
            except Exception as exc:
                note = (note + "；" if note else "") + f"RSS 失败：{exc}"
        if not works and not note:
            note = "窗口内无新记录"

        log(
            f"  [{idx:>2}/{total}] {journal.name:<46} {len(works):>3} 篇"
            + (f"   ⚠ {note}" if note else "")
        )
        per_journal[journal.name] = {
            "display": journal.label or journal.name,
            "group": journal.group,
            "publisher": journal.publisher,
            "fetched": len(works),
            "error": note,
        }
        all_works.extend(works)
        time.sleep(0.02)
    return all_works, per_journal


# --------------------------------------------------------------------------- #
# 主入口
# --------------------------------------------------------------------------- #
def run(
    *,
    run_date: dt.date | None = None,
    limit: int | None = None,
    config_path: Path | None = None,
    out_dir: Path | None = None,
    no_dedup: bool = False,
    dry_run: bool = False,
    no_fetch: bool = False,
    no_enrich: bool = False,
    force: bool = False,
    cache_candidates: Path | None = None,
    open_after: bool = False,
) -> dict:
    cfg = load_config(config_path)
    today = run_date or dt.date.today()
    size = limit or cfg.digest_size
    out_dir = out_dir or OUT_DIR

    log(f"===== PriceRadar {today.isoformat()} =====")
    attach_resolved(cfg)

    if "@example.com" in cfg.mailto:
        log("⚠ 还没填真实邮箱：config.toml → [general] mailto")
        log("  Crossref 靠它进入 polite pool；Unpaywall 会直接拒绝 example.com，")
        log("  免费全文链接因此查不到。填上你自己的邮箱即可解决。")

    # 一天只出一期：当天日报已经生成过就直接退出，避免重跑把内容覆盖成空的
    existing = out_dir / f"{today.isoformat()}.json"
    if existing.exists() and not force and not dry_run:
        try:
            prev = json.loads(existing.read_text(encoding="utf-8"))
        except Exception:
            prev = {}
        if prev.get("items"):
            log(
                f"{today.isoformat()} 的日报已存在（{len(prev['items'])} 篇），跳过。"
                "要重新生成请加 --force。"
            )
            return prev

    if no_fetch:
        if not cache_candidates or not cache_candidates.exists():
            raise SystemExit("--no-fetch 需要配合 --candidates <json> 使用")
        all_works = json.loads(cache_candidates.read_text(encoding="utf-8"))
        per_journal = {}
        log(f"离线模式：载入候选 {len(all_works)} 篇")
    else:
        if any(not (j.issn or j.rss_url) for j in cfg.journals if j.enabled):
            log("发现未解析的期刊，先解析一次…")
            resolve_journals(cfg, verbose=lambda m: log("  " + m))
        log(
            f"窗口：近 {cfg.lookback_days} 天（出版/入库）"
            f" ｜ 数据源：Crossref{'+RSS' if cfg.use_rss else ''}"
            f"{'+S2' if cfg.use_semanticscholar else ''}"
            f"{'+OpenAlex' if cfg.use_openalex else ''}"
        )
        log("抓取中…")
        all_works, per_journal = collect(cfg, today)

    log(f"原始记录 {len(all_works)} 条，去重中…")
    candidates = dedupe(all_works)
    log(f"去重后候选 {len(candidates)} 篇")

    store = Store() if not dry_run else None
    if store and not no_dedup:
        seen_ids, seen_titles = store.pushed_keys()
        fresh = []
        for work in candidates:
            if work.get("id") in seen_ids:
                continue
            fp = title_fingerprint(work.get("title", ""))
            if fp and fp in seen_titles:
                continue
            fresh.append(work)
        log(f"排除历史已推 {len(candidates) - len(fresh)} 篇 → 新候选 {len(fresh)} 篇")
        candidates = fresh

    enrich_stats = {"s2_filled": 0, "openalex_filled": 0, "openalex_note": "已跳过"}
    if candidates and not dry_run and not no_enrich:
        missing = [w for w in candidates if not w.get("abstract")]
        log(f"补充摘要：{len(missing)} 篇缺摘要…")
        if missing:
            enrich_stats["s2_filled"] = enrich_with_semantic_scholar(
                candidates, cfg, log=lambda m: log("  " + m)
            )
            filled, note = enrich_with_openalex(candidates, cfg, log=lambda m: log("  " + m))
            enrich_stats["openalex_filled"] = filled
            enrich_stats["openalex_note"] = note
            log(
                f"  补到摘要：Semantic Scholar {enrich_stats['s2_filled']} 篇 ｜ "
                f"OpenAlex {filled} 篇（{note}）"
            )

    scraper = Scorer(cfg, today=today)
    scored = [scraper.score(w) for w in candidates]
    for s in scored:
        # 把分数写回 work，进入 SQLite 后 stats / 历史才有真实分数
        s.work["score"] = round(s.score, 2)

    # OA 全文链接只对打分靠前的少数文章去查（Unpaywall 是逐篇接口）
    if scored and not dry_run and not no_enrich and cfg.use_unpaywall:
        from .sources import enrich_with_unpaywall

        pool = max(size * 4, cfg.unpaywall_max)
        top = sorted(scored, key=lambda s: -s.score)[:pool]
        found = enrich_with_unpaywall([s.work for s in top], cfg)
        if found:
            scored = [scraper.score(w) for w in candidates]
            for s in scored:
                s.work["score"] = round(s.score, 2)
        log(f"Unpaywall：为前 {len(top)} 篇查到 {found} 个免费全文链接")

    chosen, notes = select_top(scored, cfg, size, cfg.max_per_journal)
    log(
        f"严格命中 {notes['strict_pool']} 篇（放宽后可得 {notes.get('relaxed_pool', 0)} 篇）"
        f" → 入选 {len(chosen)} 篇"
    )

    items = [s.to_dict(rank=i + 1) for i, s in enumerate(chosen)]
    for item in items:
        item["pushed_date"] = today.isoformat()

    with_abstract = sum(1 for w in candidates if w.get("abstract"))
    stats = {
        "journals": len([j for j in cfg.journals if j.enabled]),
        "fetched": len(all_works),
        "candidates": len(candidates),
        "pushed": len(items),
        "digest_size": size,
        "per_journal": per_journal,
        "selection_notes": notes,
        "abstract_coverage": round(with_abstract / len(candidates), 3) if candidates else 0.0,
        "enrich": enrich_stats,
    }
    digest = {
        "date": today.isoformat(),
        "generated_at": dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "stats": stats,
        "items": items,
    }

    if dry_run:
        log("--dry-run：不写库、不出文件。全部入选预览：")
        for item in items:
            log(
                f"  {item['rank']:>2}. [{item['score']:>5.1f}] "
                f"{item['title'][:70]:<70} | {item['journal'][:28]:<28} "
                f"| 摘要 {'有' if item.get('abstract') else '无'}"
            )
        return digest

    if not no_fetch and cache_candidates:
        cache_candidates.parent.mkdir(parents=True, exist_ok=True)
        cache_candidates.write_text(
            json.dumps(all_works, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        log(f"候选池已缓存：{cache_candidates}")

    if store:
        if not no_dedup:
            store.record_seen(candidates, today=today)
            store.mark_pushed(items, today.isoformat())
            store.record_run(today.isoformat(), len(all_works), len(candidates), len(items))
        history = [
            {"date": row["run_date"], "pushed": row["pushed"] or 0} for row in store.runs(60)
        ]
        store.close()
    else:
        history = []

    paths = write_outputs(
        digest,
        out_dir,
        history,
        public_url=cfg.public_url,
        site_title=cfg.site_title,
    )
    log("输出：")
    for key in ("md", "html", "index", "feed", "json"):
        if key in paths:
            log(f"  {key:<9} {paths[key]}")
    if open_after:
        import webbrowser

        webbrowser.open(paths["html"].as_uri())
    return digest
