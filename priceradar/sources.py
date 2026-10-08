"""文献数据源。

架构（按 2026 年各接口的真实现状设计）：

1. **Crossref**（主干，免费、无需 Key、几乎无限）
   按 ISSN + `from-created-date` 抓每本期刊窗口内的全部新记录。
   覆盖 17 本期刊的标题 / 作者 / DOI / 被引 / 部分摘要。
   局限：Elsevier 系（Energy Economics、JEEM、J. Commodity Markets、
   J. Econometrics、Int. J. Forecasting、Food Policy）不提交摘要与在线日期。

2. **ScienceDirect TOC RSS**（Elsevier 专用补充，免费）
   补上精确的在线日期与原文链接；RSS 不含摘要。

3. **Semantic Scholar 批量接口**（摘要 / OA 全文补充，免费）
   一次 POST 可查 200 个 DOI，用于补齐 Crossref 缺的摘要与免费全文链接。

4. **OpenAlex**（可选增强，按额度计费）
   摘要质量最高，但匿名请求共用同 IP 的每日免费额度（约 100 次请求）。
   配置 `OPENALEX_API_KEY` 后额度独立；额度用尽会自动熔断，不影响其余流程。
"""

from __future__ import annotations

import datetime as dt
import json
import math
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from .config import CACHE_PATH, DATA_DIR, Config, Journal
from .http import (
    BudgetExhausted,
    HttpError,
    RateLimited,
    get_json,
    post_json,
)

CROSSREF = "https://api.crossref.org"
OPENALEX = "https://api.openalex.org"
S2 = "https://api.semanticscholar.org/graph/v1"
UNPAYWALL = "https://api.unpaywall.org"
SD_RSS = "https://rss.sciencedirect.com/publication/science"

WORK_SELECT = (
    "id,doi,display_name,publication_date,created_date,primary_location,"
    "cited_by_count,abstract_inverted_index,authorships,type,is_oa,"
    "best_oa_location,topics,language"
)

MONTHS = {
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6,
    "july": 7, "august": 8, "september": 9, "october": 10, "november": 11,
    "december": 12,
}


# --------------------------------------------------------------------------- #
# 文本工具
# --------------------------------------------------------------------------- #
def reconstruct_abstract(inverted: dict | None) -> str:
    if not inverted:
        return ""
    positions: list[tuple[int, str]] = []
    for word, idxs in inverted.items():
        for idx in idxs:
            positions.append((idx, word))
    positions.sort(key=lambda x: x[0])
    return " ".join(word for _, word in positions)


def strip_tags(text: str | None) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", " ", text)
    text = (
        text.replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        .replace("&quot;", '"').replace("&#x2019;", "'").replace("&#8217;", "'")
        .replace("&nbsp;", " ").replace("&#x2013;", "-")
    )
    return re.sub(r"\s+", " ", text).strip()


def clean_doi(doi: str | None) -> str:
    if not doi:
        return ""
    return re.sub(r"^https?://(dx\.)?doi\.org/", "", doi.strip(), flags=re.I)


def title_key(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:90]


def _norm(text: str) -> str:
    text = re.sub(r"[^a-z0-9]+", " ", (text or "").lower()).strip()
    # 忽略开头的 "the"：The Journal of Finance == Journal of Finance
    return re.sub(r"^the\s+", "", text)


# --------------------------------------------------------------------------- #
# 期刊解析：名称 → ISSN / 出版社 / RSS
# --------------------------------------------------------------------------- #
def _cache_path() -> Path:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    return CACHE_PATH


def load_cache() -> dict:
    path = _cache_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def save_cache(cache: dict) -> None:
    _cache_path().write_text(
        json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def search_crossref_journals(name: str, cfg: Config, rows: int = 20) -> list[dict]:
    data = get_json(
        f"{CROSSREF}/journals",
        {"query": name, "rows": rows},
        mailto=cfg.mailto,
        timeout=cfg.http_timeout,
        interval=cfg.request_interval,
    )
    return (data.get("message") or {}).get("items", [])


def pick_best_journal(name: str, items: list[dict]) -> dict | None:
    """按名称重合度为主、期刊规模为辅挑最匹配的期刊。

    规模必须参与排序：像「Journal of Finance」这种名字，Crossref 里存在多家
    同名或近名的小刊（例如 Apex Publishing 的 Journal of Finance），
    真正想订阅的是 Wiley 的 The Journal of Finance（上万篇 DOI）。
    """
    if not items:
        return None
    target = _norm(name)
    target_words = set(target.split())
    best, best_score = None, -1.0
    for item in items:
        label = _norm(item.get("title", ""))
        if not label or not item.get("ISSN"):
            continue
        label_words = set(label.split())
        # F1 而非简单重合：多出来的词要扣分，否则
        # "Journal of Banking & Finance" 会和 "The Journal of Finance" 打平。
        common = len(target_words & label_words)
        overlap = 2.0 * common / max(len(target_words) + len(label_words), 1)
        total = int((item.get("counts") or {}).get("total-dois") or 0)
        score = overlap * 100.0
        score += math.log10(total + 1) * 8.0
        if label == target:
            score += 3.0
        if score > best_score:
            best, best_score = item, score
    return best


def rss_url_for(issn: str) -> str:
    return f"{SD_RSS}/{issn.replace('-', '')}"


def resolve_journals(cfg: Config, refresh: bool = False, verbose=print) -> dict:
    """把 config.toml 的期刊名解析成 ISSN / 出版社，写到 data/sources_cache.json。"""
    cache = load_cache()
    changed = False

    for journal in cfg.journals:
        if not journal.enabled:
            continue
        key = journal.name
        entry = cache.get(key)

        if entry and entry.get("issn") and not refresh:
            _apply(journal, entry)
            verbose(f"[cache] {key} -> {entry.get('crossref_name')} ({entry['issn'][0]})")
            continue
        if journal.issn and not refresh:
            entry = {
                "name": key,
                "issn": journal.issn,
                "crossref_name": journal.name,
                "publisher": journal.publisher,
                "pinned": True,
            }
            if journal.publisher.lower().startswith("elsevier"):
                entry["rss_url"] = journal.rss_url or rss_url_for(journal.issn[0])
            cache[key] = entry
            changed = True
            _apply(journal, entry)
            verbose(f"[pin  ] {key} -> {journal.issn}")
            continue

        try:
            candidates = search_crossref_journals(key, cfg)
        except HttpError as exc:
            verbose(f"[fail ] {key} :: {exc}")
            continue
        best = pick_best_journal(key, candidates)
        if not best:
            verbose(f"[miss ] {key} :: Crossref 未找到候选期刊")
            continue

        issns = list(best.get("ISSN") or [])
        publisher = best.get("publisher") or ""
        entry = {
            "name": key,
            "crossref_name": best.get("title") or key,
            "issn": issns,
            "publisher": publisher,
            "total_dois": (best.get("counts") or {}).get("total-dois"),
            "other_candidates": [
                {"name": c.get("title"), "issn": c.get("ISSN"), "pub": c.get("publisher")}
                for c in candidates
                if c.get("title") != best.get("title")
            ][:4],
        }
        if "elsevier" in publisher.lower():
            entry["rss_url"] = rss_url_for(issns[0])
        cache[key] = entry
        changed = True
        _apply(journal, entry)
        warn = ""
        total = entry.get("total_dois") or 0
        if total and total < 800:
            warn = f"   ⚠ 该刊仅 {total} 篇 DOI，请确认是否匹配正确"
        verbose(
            f"[find ] {key} -> {entry['crossref_name']} "
            f"({issns[0]}, {publisher}, {total} 篇){warn}"
        )

    if changed:
        save_cache(cache)
    return cache


def _apply(journal: Journal, entry: dict) -> None:
    if not journal.issn:
        journal.issn = list(entry.get("issn") or [])
    if not journal.publisher:
        journal.publisher = entry.get("publisher", "")
    if not journal.openalex_name:
        journal.openalex_name = entry.get("crossref_name", "") or ""
    if not journal.rss_url:
        journal.rss_url = entry.get("rss_url", "")


def attach_resolved(cfg: Config) -> None:
    cache = load_cache()
    for journal in cfg.journals:
        entry = cache.get(journal.name)
        if entry:
            _apply(journal, entry)
        if not journal.openalex_id and entry:
            journal.openalex_id = entry.get("openalex_id", "")


# --------------------------------------------------------------------------- #
# 数据源 1：Crossref
# --------------------------------------------------------------------------- #
def fetch_crossref(journal: Journal, cfg: Config, today: dt.date) -> list[dict]:
    if not journal.issn:
        return []
    date_from = (today - dt.timedelta(days=cfg.lookback_days)).isoformat()
    date_to = (today + dt.timedelta(days=1)).isoformat()

    data = get_json(
        f"{CROSSREF}/journals/{journal.issn[0]}/works",
        {
            "filter": f"from-created-date:{date_from},until-created-date:{date_to}",
            "rows": cfg.crossref_rows,
            "sort": "created",
            "order": "desc",
            "select": (
                "DOI,title,abstract,container-title,published-online,published-print,"
                "issued,created,author,is-referenced-by-count,type,URL,subject,link"
            ),
        },
        mailto=cfg.mailto,
        timeout=cfg.http_timeout,
        interval=cfg.request_interval,
    )
    items = (data.get("message") or {}).get("items", [])
    return [_normalize_crossref(item, journal) for item in items]


def _date_parts(obj: dict | None) -> str:
    if not obj:
        return ""
    parts = (obj.get("date-parts") or [[]])[0]
    if not parts:
        return ""
    if len(parts) == 1:
        return f"{parts[0]:04d}-01-01"
    if len(parts) == 2:
        return f"{parts[0]:04d}-{parts[1]:02d}-01"
    return f"{parts[0]:04d}-{parts[1]:02d}-{parts[2]:02d}"


def _normalize_crossref(item: dict, journal: Journal) -> dict:
    titles = item.get("title") or []
    doi = clean_doi(item.get("DOI"))
    created = (item.get("created") or {}).get("date-time", "")[:10]
    online = _date_parts(item.get("published-online"))
    print_date = _date_parts(item.get("published-print"))
    issued = _date_parts(item.get("issued"))

    authors = [
        " ".join(filter(None, [a.get("given"), a.get("family")])).strip()
        or (a.get("name") or "")
        for a in (item.get("author") or [])[:20]
    ]
    return {
        "id": f"crossref:{doi}" if doi else f"crossref:{title_key(titles[0] if titles else '')}",
        "doi": doi,
        "title": strip_tags(titles[0]) if titles else "",
        "abstract": strip_tags(item.get("abstract")),
        # 在线优先的精确日期（只有部分出版社提供）
        "publication_date": online,
        # DOI 创建时间 ≈ 文章上线时间，是判断「新不新」最可靠的锚点
        "created_date": created,
        # 纸质期号日期，Elsevier 常给出未来月份，只作展示
        "issue_date": issued or print_date,
        "journal": journal.name,
        "journal_display": journal.label or journal.name,
        "group": journal.group,
        "tier": journal.tier,
        "cited_by_count": item.get("is-referenced-by-count") or 0,
        "authors": [a for a in authors if a],
        "author_count": len(item.get("author") or []),
        "type": item.get("type") or "",
        "is_oa": False,
        "oa_url": "",
        "landing_page": item.get("URL") or "",
        "topics": list(item.get("subject") or [])[:3],
        "language": "",
        "source_origin": "crossref",
        "abstract_source": "crossref" if item.get("abstract") else "",
    }


# --------------------------------------------------------------------------- #
# 数据源 2：ScienceDirect RSS（Elsevier）
# --------------------------------------------------------------------------- #
def fetch_rss(journal: Journal, cfg: Config, today: dt.date) -> list[dict]:
    if not journal.rss_url:
        return []
    import urllib.request

    from .http import USER_AGENT

    req = urllib.request.Request(
        journal.rss_url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml"}
    )
    try:
        with urllib.request.urlopen(req, timeout=cfg.http_timeout) as resp:
            payload = resp.read()
    except Exception as exc:
        raise HttpError(f"RSS 抓取失败：{journal.rss_url} :: {exc}") from exc

    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise HttpError(f"RSS 解析失败：{journal.rss_url} :: {exc}") from exc

    cutoff = today - dt.timedelta(days=cfg.lookback_days + 30)
    out = []
    for item in root.iter("item"):
        title = strip_tags((item.findtext("title") or "").strip())
        if not title:
            continue
        link = (item.findtext("link") or "").split("?")[0]
        desc = strip_tags(item.findtext("description") or "")
        pub_date = _parse_rss_date(desc)
        if pub_date:
            try:
                if dt.date.fromisoformat(pub_date) < cutoff:
                    continue
            except ValueError:
                pass
        authors = _parse_rss_authors(desc)
        out.append(
            {
                "id": "rss:" + (item.findtext("guid") or link or title_key(title)),
                "doi": "",
                "title": title,
                "abstract": "",
                "publication_date": pub_date or "",
                "created_date": today.isoformat(),
                "issue_date": "",
                "journal": journal.name,
                "journal_display": journal.label or journal.name,
                "group": journal.group,
                "tier": journal.tier,
                "cited_by_count": 0,
                "authors": authors,
                "author_count": len(authors),
                "type": "journal-article",
                "is_oa": False,
                "oa_url": "",
                "landing_page": link,
                "topics": [],
                "language": "",
                "source_origin": "rss",
                "abstract_source": "",
            }
        )
    return out


def _parse_rss_date(desc: str) -> str:
    m = re.search(r"Available online\s+(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", desc)
    if m:
        day, month_name, year = m.groups()
        month = MONTHS.get(month_name.lower())
        if month:
            return f"{int(year):04d}-{month:02d}-{int(day):02d}"
    m = re.search(r"Publication date:\s*([A-Za-z]+)\s+(\d{4})", desc)
    if m:
        month_name, year = m.groups()
        month = MONTHS.get(month_name.lower())
        if month:
            return f"{int(year):04d}-{month:02d}-01"
    m = re.search(r"(\d{4})-(\d{2})-(\d{2})", desc)
    if m:
        return m.group(0)
    return ""


def _parse_rss_authors(desc: str) -> list[str]:
    m = re.search(r"Author\(s\):\s*(.+)$", desc)
    if not m:
        return []
    return [a.strip() for a in m.group(1).split(",") if a.strip()][:20]


# --------------------------------------------------------------------------- #
# 合并与增强
# --------------------------------------------------------------------------- #
def merge_supplement(primary: list[dict], supplement: list[dict]) -> list[dict]:
    """把 RSS 的日期/链接补进 Crossref 记录，并把 RSS 独有的条目追加进来。"""
    index = {title_key(w["title"]): w for w in primary if w.get("title")}
    extra = []
    for item in supplement:
        key = title_key(item["title"])
        if not key:
            continue
        target = index.get(key)
        if target is None:
            extra.append(item)
            continue
        if not target.get("publication_date") and item.get("publication_date"):
            target["publication_date"] = item["publication_date"]
        if len(item.get("publication_date", "")) == 10 and len(
            target.get("publication_date", "")
        ) < 10:
            target["publication_date"] = item["publication_date"]
        if not target.get("landing_page"):
            target["landing_page"] = item.get("landing_page", "")
        if not target.get("authors"):
            target["authors"] = item.get("authors", [])
    return primary + extra


def enrich_with_semantic_scholar(works: list[dict], cfg: Config, log=print) -> int:
    """用 Semantic Scholar 批量接口补摘要 / OA 全文。一次请求可查 200 个 DOI。"""
    if not cfg.use_semanticscholar or not cfg.enrich_missing_abstract:
        return 0
    targets = [w for w in works if w.get("doi") and not w.get("abstract")]
    if not targets:
        return 0

    headers = {}
    if cfg.s2_api_key:
        headers["x-api-key"] = cfg.s2_api_key
    fields = "title,abstract,publicationDate,externalIds,openAccessPdf,citationCount,venue"

    by_doi = {w["doi"].lower(): w for w in targets}
    filled = 0
    batch = max(1, cfg.s2_batch_size)
    for start in range(0, len(targets), batch):
        chunk = targets[start : start + batch]
        ids = ["DOI:" + w["doi"] for w in chunk]
        try:
            result = post_json(
                f"{S2}/paper/batch?fields={fields}",
                {"ids": ids},
                headers=headers,
                timeout=120,
                interval=cfg.s2_interval,
                retries=5,
            )
        except BudgetExhausted as exc:
            log(f"Semantic Scholar 熔断：{exc}")
            break
        except RateLimited as exc:
            log(f"Semantic Scholar 被限流，跳过剩余批次（{exc}）")
            break
        except HttpError as exc:
            log(f"Semantic Scholar 失败，跳过剩余批次（{exc}）")
            break
        if not isinstance(result, list):
            break
        for paper in result:
            if not paper:
                continue
            doi = ((paper.get("externalIds") or {}).get("DOI") or "").lower()
            work = by_doi.get(doi)
            if work is None:
                continue
            if paper.get("abstract") and not work.get("abstract"):
                work["abstract"] = strip_tags(paper["abstract"])
                work["abstract_source"] = "semanticscholar"
                filled += 1
            pdf = (paper.get("openAccessPdf") or {}).get("url")
            if pdf and not work.get("oa_url"):
                work["oa_url"] = pdf
                work["is_oa"] = True
            if not work.get("cited_by_count") and paper.get("citationCount"):
                work["cited_by_count"] = paper["citationCount"]
    return filled


def enrich_with_unpaywall(works: list[dict], cfg: Config, log=print) -> int:
    """用 Unpaywall（免费、无 Key、需 email）为入选候选找合法免费全文。

    只对打分靠前的少数文章发起请求，避免为几百条候选各打一次。
    """
    if not cfg.use_unpaywall:
        return 0
    if not cfg.mailto or "@example.com" in cfg.mailto or "." not in cfg.mailto:
        log("Unpaywall 需要一个真实邮箱（Unpaywall 明确拒绝 example.com），已跳过")
        return 0
    targets = [w for w in works if w.get("doi") and not w.get("oa_url")]
    targets = targets[: max(0, cfg.unpaywall_max)]
    found = 0
    for work in targets:
        try:
            data = get_json(
                f"{UNPAYWALL}/v2/{work['doi']}",
                {"email": cfg.mailto},
                timeout=cfg.http_timeout,
                interval=0.05,
                retries=1,
            )
        except HttpError:
            continue
        if not isinstance(data, dict):
            continue
        best = data.get("best_oa_location") or {}
        url = best.get("url_for_pdf") or best.get("url")
        # Unpaywall 有时只回一个 doi.org 落地页，那和「DOI / 原文」链接重复，没必要显示两次
        if url and not (
            "doi.org/" in url and work.get("doi") and work["doi"].lower() in url.lower()
        ):
            work["oa_url"] = url
        if data.get("is_oa"):
            work["is_oa"] = True
            found += 1
    return found


def enrich_with_openalex(works: list[dict], cfg: Config, log=print) -> tuple[int, str]:
    """用 OpenAlex 批量补摘要（按 DOI 一次查 50 篇）。额度用尽自动熔断。"""
    if not cfg.use_openalex or not cfg.enrich_missing_abstract:
        return 0, "已关闭"
    targets = [w for w in works if w.get("doi") and not w.get("abstract")]
    if not targets:
        return 0, "无需补充"

    filled = 0
    calls = 0
    chunk_size = 50
    for start in range(0, len(targets), chunk_size):
        if calls >= cfg.openalex_max_calls:
            return filled, f"达到本次调用上限 {cfg.openalex_max_calls}"
        chunk = targets[start : start + chunk_size]
        filt = "doi:" + "|".join(w["doi"] for w in chunk)
        params = {
            "filter": filt,
            "per-page": len(chunk),
            "select": "doi,abstract_inverted_index,cited_by_count,is_oa,best_oa_location",
        }
        if cfg.openalex_api_key:
            params["api_key"] = cfg.openalex_api_key
        try:
            data = get_json(
                f"{OPENALEX}/works",
                params,
                mailto=cfg.mailto,
                timeout=cfg.http_timeout,
                interval=cfg.request_interval,
            )
            calls += 1
        except BudgetExhausted as exc:
            return filled, f"额度用尽已熔断（{exc}）"
        except HttpError as exc:
            return filled, f"请求失败（{exc}）"

        by_doi = {w["doi"].lower(): w for w in chunk}
        for raw in (data.get("results") or []):
            doi = clean_doi(raw.get("doi")).lower()
            work = by_doi.get(doi)
            if work is None:
                continue
            abstract = reconstruct_abstract(raw.get("abstract_inverted_index"))
            if abstract and not work.get("abstract"):
                work["abstract"] = abstract
                work["abstract_source"] = "openalex"
                filled += 1
            if not work.get("cited_by_count"):
                work["cited_by_count"] = raw.get("cited_by_count") or 0
            best_oa = raw.get("best_oa_location") or {}
            if best_oa.get("pdf_url") and not work.get("oa_url"):
                work["oa_url"] = best_oa["pdf_url"]
                work["is_oa"] = True
    return filled, f"调用 {calls} 次"
