"""输出渲染：Markdown（存档 / 邮件正文）+ HTML（本地看板，可搜索）。"""

from __future__ import annotations

import datetime as dt
import html
import json
from pathlib import Path

TIER_LABEL = {1: "T1", 2: "T2", 3: "T3"}


def _date_line(item: dict) -> str:
    """把「上线 / 在线 / 期号」三个日期讲清楚，避免把未来期号当成出版日。"""
    created = (item.get("created_date") or "")[:10]
    pub = (item.get("publication_date") or "")[:10]
    issue = (item.get("issue_date") or "")[:10]
    days = item.get("days_old")
    parts = []
    if created:
        suffix = f"（{days} 天前）" if isinstance(days, int) and days >= 0 else ""
        parts.append(f"上线 {created}{suffix}")
    if pub and pub != created:
        parts.append(f"在线 {pub}")
    if issue and issue[:7] not in {created[:7], pub[:7]}:
        parts.append(f"期号 {issue[:7]}")
    return " · ".join(parts) if parts else "日期未知"


def _authors(item: dict, limit: int = 4) -> str:
    authors = item.get("authors") or []
    if not authors:
        return "作者信息缺失"
    if len(authors) <= limit:
        return "、".join(authors)
    return "、".join(authors[:limit]) + f" 等 {item.get('author_count') or len(authors)} 人"


def _links(item: dict) -> list[tuple[str, str]]:
    out = []
    if item.get("doi"):
        out.append(("DOI / 原文", "https://doi.org/" + item["doi"]))
    elif item.get("landing_page"):
        out.append(("原文页面", item["landing_page"]))
    if item.get("oa_url"):
        out.append(("开放获取全文", item["oa_url"]))
    if item.get("id", "").startswith("https://openalex.org/"):
        out.append(("OpenAlex", item["id"]))
    return out


# --------------------------------------------------------------------------- #
# Markdown
# --------------------------------------------------------------------------- #
def render_markdown(digest: dict) -> str:
    date = digest["date"]
    stats = digest["stats"]
    lines = [
        f"# 价格研究日报 · {date}",
        "",
        (
            f"> 覆盖 {stats['journals']} 本顶刊 ｜ 抓取 {stats['fetched']} 篇 ｜ "
            f"新候选 {stats['candidates']} 篇 ｜ 本期推送 {stats['pushed']} 篇 ｜ "
            f"生成于 {digest['generated_at']}"
        ),
        "",
    ]

    if not digest["items"]:
        lines += [
            "今日没有符合条件的新文章。可能是抓取窗口内确实没有新上线论文，"
            "也可能需要放宽 `config.toml` 中的 `lookback_days`。",
            "",
        ]

    for idx, item in enumerate(digest["items"], 1):
        level = {"strong": "强相关", "medium": "中等相关", "weak": "弱相关"}.get(
            item.get("relevance_level", ""), ""
        )
        lines.append(f"## {idx}. {item['title']}")
        lines.append("")
        lines.append(
            f"**{item.get('journal_display') or item.get('journal')}**"
            f" · {_date_line(item)}"
            f" · {TIER_LABEL.get(item.get('tier'), '')}"
            f" · {_authors(item)}"
            f" · 综合分 **{item.get('score', 0):.1f}**"
            + (f" · {level}" if level else "")
        )
        lines.append("")
        if not item.get("abstract"):
            lines.append("> ⚠ 该刊未向 Crossref/OpenAlex 提供摘要，本条基于标题判相关性，建议点开原文确认。")
            lines.append("")
        if item.get("keywords"):
            lines.append("标签：" + " ".join(f"`{k}`" for k in item["keywords"][:10]))
            lines.append("")
        abstract = (item.get("abstract") or "").strip()
        if abstract:
            lines.append("**摘要**")
            lines.append("")
            lines.append(abstract)
            lines.append("")
        if item.get("reasons"):
            lines.append("**为什么推荐**")
            lines.append("")
            for reason in item["reasons"]:
                lines.append(f"- {reason}")
            lines.append("")
        links = _links(item)
        if links:
            lines.append(" ｜ ".join(f"[{label}]({url})" for label, url in links))
            lines.append("")
        lines.append("---")
        lines.append("")

    lines.append(_section_coverage(digest))
    return "\n".join(lines).rstrip() + "\n"


def _section_coverage(digest: dict) -> str:
    per_journal = digest["stats"].get("per_journal") or {}
    if not per_journal:
        return ""
    rows = ["## 抓取覆盖情况", "", "| 期刊 | 方向 | 窗口内新文 | 本期入选 |", "| --- | --- | --- | --- |"]
    picked: dict[str, int] = {}
    for item in digest["items"]:
        picked[item["journal"]] = picked.get(item["journal"], 0) + 1
    for name, info in sorted(per_journal.items(), key=lambda kv: -kv[1]["fetched"]):
        rows.append(
            f"| {info.get('display') or name} | {info.get('group', '')} | "
            f"{info['fetched']} | {picked.get(name, 0)} |"
        )
    rows.append("")
    rows.append(f"数据源：OpenAlex（主）+ Crossref（兜底）。抓取时间 {digest['generated_at']}。")
    rows.append("")
    return "\n".join(rows)


# --------------------------------------------------------------------------- #
# HTML
# --------------------------------------------------------------------------- #
CSS = """
:root{
  --bg:#0f1115; --panel:#171a21; --panel2:#1e222b; --line:#2a2f3a;
  --fg:#e8ecf3; --muted:#98a2b3; --accent:#4f9cf9; --accent2:#22c55e;
  --warn:#f59e0b; --chip:#242a35;
}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);
  font:15px/1.65 -apple-system,BlinkMacSystemFont,"Segoe UI","Microsoft YaHei",sans-serif}
a{color:var(--accent);text-decoration:none}
a:hover{text-decoration:underline}
header{padding:28px 32px 18px;border-bottom:1px solid var(--line);
  background:linear-gradient(180deg,#171a21,#0f1115)}
h1{margin:0 0 8px;font-size:24px;letter-spacing:.5px}
.sub{color:var(--muted);font-size:13.5px}
.wrap{display:flex;gap:22px;padding:22px 32px 60px;align-items:flex-start}
main{flex:1;min-width:0}
aside{width:250px;flex:none;position:sticky;top:22px}
.toolbar{display:flex;gap:10px;flex-wrap:wrap;margin-bottom:16px;align-items:center}
input[type=search]{flex:1;min-width:220px;padding:10px 13px;border-radius:9px;
  border:1px solid var(--line);background:var(--panel);color:var(--fg);font-size:14px}
.chip{background:var(--chip);border:1px solid var(--line);color:var(--muted);
  padding:6px 12px;border-radius:999px;font-size:12.5px;cursor:pointer;user-select:none}
.chip.on{background:#1d3a5c;border-color:#2f6ea8;color:#cfe4ff}
.card{background:var(--panel);border:1px solid var(--line);border-radius:14px;
  padding:18px 20px;margin-bottom:14px}
.card:hover{border-color:#38414f}
.rank{display:inline-flex;align-items:center;justify-content:center;width:26px;height:26px;
  border-radius:8px;background:#1d3a5c;color:#cfe4ff;font-size:13px;font-weight:600;margin-right:9px}
.title{font-size:17px;font-weight:600;line-height:1.45;color:#f2f6fc}
.meta{color:var(--muted);font-size:12.8px;margin:9px 0 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center}
.badge{background:#1c2430;border:1px solid var(--line);border-radius:6px;padding:2px 7px;font-size:11.5px}
.badge.t1{background:#2a2113;border-color:#5b421a;color:#f0c674}
.badge.score{background:#0f2e1c;border-color:#1f5c3a;color:#7ee2a8;font-weight:600}
.badge.oa{background:#122a3d;border-color:#245273;color:#8ec9f0}
.badge.rel-strong{background:#3a1a1a;border-color:#7a3030;color:#ffb3b3}
.badge.noabs{background:#2b260f;border-color:#5c521f;color:#e0d08a}
.abs{color:#c6cddb;font-size:13.8px;margin:12px 0 0}
details.absbox{margin-top:12px}
details.absbox summary{cursor:pointer;color:var(--accent);font-size:13px;outline:none}
.chips{display:flex;gap:6px;flex-wrap:wrap;margin-top:12px}
.kw{background:var(--chip);border:1px solid var(--line);border-radius:999px;
  padding:2px 9px;font-size:11.5px;color:#a9b4c6}
.why{margin-top:12px;border-left:2px solid #2f4a6b;padding-left:12px;
  color:var(--muted);font-size:12.6px}
.why ul{margin:4px 0 0;padding-left:16px}
.links{margin-top:13px;display:flex;gap:14px;flex-wrap:wrap;font-size:13px}
.hist{background:var(--panel);border:1px solid var(--line);border-radius:14px;padding:14px 16px}
.hist h3{margin:0 0 10px;font-size:13px;color:var(--muted);font-weight:600;letter-spacing:.6px}
.hist a{display:flex;justify-content:space-between;font-size:13px;padding:5px 0;
  border-bottom:1px dashed #232833;color:#c6cddb}
.hist a:last-child{border-bottom:none}
.hist .n{color:var(--muted);font-size:12px}
.empty{color:var(--muted);padding:30px;text-align:center;background:var(--panel);
  border:1px dashed var(--line);border-radius:14px}
footer{color:var(--muted);font-size:12.4px;padding:0 32px 40px}
table{border-collapse:collapse;width:100%;font-size:13px;margin-top:10px}
th,td{border-bottom:1px solid var(--line);padding:7px 9px;text-align:left}
th{color:var(--muted);font-weight:600}
code{background:#20242e;border-radius:5px;padding:1px 6px;font-size:12.6px}
"""

JS = """
const q=document.getElementById('q'), cards=[...document.querySelectorAll('.card')];
const chips=[...document.querySelectorAll('.chip[data-group]')];
let active=new Set();
function apply(){
  const term=(q.value||'').trim().toLowerCase();
  cards.forEach(c=>{
    const okText=!term||c.dataset.blob.includes(term);
    const g=c.dataset.group||'';
    const okGroup=active.size===0||active.has(g);
    c.style.display=(okText&&okGroup)?'':'none';
  });
  const vis=cards.filter(c=>c.style.display!=='none').length;
  const counter=document.getElementById('counter');
  if(counter) counter.textContent=vis+' / '+cards.length+' 篇';
}
if(q){q.addEventListener('input',apply)}
chips.forEach(ch=>ch.addEventListener('click',()=>{
  const g=ch.dataset.group;
  if(active.has(g)){active.delete(g);ch.classList.remove('on')}
  else{active.add(g);ch.classList.add('on')}
  apply();
}));
document.addEventListener('keydown',e=>{if(e.key==='/'&&q){e.preventDefault();q.focus()}});
"""


def _e(text: str) -> str:
    return html.escape(text or "", quote=True)


def render_html(digest: dict, history: list[dict], *, is_index: bool = False) -> str:
    date = digest["date"]
    stats = digest["stats"]
    groups = sorted({i.get("group", "") for i in digest["items"] if i.get("group")})

    cards = []
    for idx, item in enumerate(digest["items"], 1):
        blob = " ".join(
            [
                item.get("title", ""),
                item.get("abstract", ""),
                item.get("journal", ""),
                " ".join(item.get("keywords", [])),
                " ".join(item.get("authors", [])),
            ]
        ).lower()

        meta = [
            f'<span class="badge">{_e(item.get("journal_display") or item.get("journal"))}</span>',
            f'<span class="badge">{_e(_date_line(item))}</span>',
        ]
        tier = item.get("tier")
        if tier:
            meta.append(f'<span class="badge t1">{TIER_LABEL.get(tier, "")}</span>')
        meta.append(f'<span class="badge score">{item.get("score", 0):.1f} 分</span>')
        if item.get("relevance_level") == "strong":
            meta.append('<span class="badge rel-strong">强相关</span>')
        if item.get("oa_url"):
            meta.append('<span class="badge oa">开放获取</span>')
        if not item.get("abstract"):
            meta.append('<span class="badge noabs">无摘要</span>')
        meta.append(f'<span>{_e(_authors(item, 3))}</span>')

        chips = "".join(
            f'<span class="kw">{_e(k)}</span>' for k in item.get("keywords", [])[:12]
        )

        abstract = (item.get("abstract") or "").strip()
        abs_html = ""
        if abstract:
            if len(abstract) > 460:
                abs_html = (
                    '<div class="abs">' + _e(abstract[:460]) + "…"
                    '<details class="absbox"><summary>展开完整摘要</summary>'
                    f'<div class="abs">{_e(abstract)}</div></details></div>'
                )
            else:
                abs_html = f'<div class="abs">{_e(abstract)}</div>'

        why = ""
        if item.get("reasons"):
            why = (
                '<div class="why"><strong>为什么推荐</strong><ul>'
                + "".join(f"<li>{_e(r)}</li>" for r in item["reasons"])
                + "</ul></div>"
            )

        links = "".join(
            f'<a href="{_e(url)}" target="_blank" rel="noopener">{_e(label)} ↗</a>'
            for label, url in _links(item)
        )
        links_html = f'<div class="links">{links}</div>' if links else ""

        cards.append(
            f'<article class="card" data-group="{_e(item.get("group", ""))}" '
            f'data-blob="{_e(blob)}">'
            f'<div><span class="rank">{idx}</span>'
            f'<a class="title" href="{_e((_links(item)[0][1] if _links(item) else "#"))}" '
            f'target="_blank" rel="noopener">{_e(item.get("title"))}</a></div>'
            f'<div class="meta">{"".join(meta)}</div>'
            f"{abs_html}"
            + (f'<div class="chips">{chips}</div>' if chips else "")
            + why
            + links_html
            + "</article>"
        )

    if not cards:
        cards.append(
            '<div class="empty">今日没有符合条件的新文章。'
            "可以尝试放宽 <code>lookback_days</code> 或调整关键词。</div>"
        )

    group_chips = "".join(
        f'<span class="chip" data-group="{_e(g)}">{_e(g)}</span>' for g in groups
    )

    hist_html = "".join(
        f'<a href="{_e(h["date"])}.html"><span>{_e(h["date"])}</span>'
        f'<span class="n">{h.get("pushed", 0)} 篇</span></a>'
        for h in history[:30]
    ) or '<div class="n">暂无历史</div>'

    coverage = _coverage_table(digest)

    return f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>价格研究日报 · {_e(date)}</title>
<style>{CSS}</style></head>
<body>
<header>
  <h1>📈 价格研究日报 · {_e(date)}</h1>
  <div class="sub">
    覆盖 {stats['journals']} 本顶刊 ｜ 抓取 {stats['fetched']} 篇 ｜ 新候选 {stats['candidates']} 篇 ｜
    本期推送 {stats['pushed']} 篇 ｜ 生成于 {_e(digest['generated_at'])}
  </div>
</header>
<div class="wrap">
  <main>
    <div class="toolbar">
      <input id="q" type="search" placeholder="搜索标题 / 摘要 / 作者 / 关键词…（按 / 聚焦）">
      {group_chips}
      <span class="chip" id="counter">{len(digest['items'])} / {len(digest['items'])} 篇</span>
    </div>
    {''.join(cards)}
    {coverage}
  </main>
  <aside>
    <div class="hist"><h3>历史日报</h3>{hist_html}</div>
    <div class="hist" style="margin-top:14px">
      <h3>怎么用</h3>
      <div class="sub" style="font-size:12.6px;line-height:1.7">
        每天自动生成。<code>index.html</code> 永远是最新一期。<br>
        点标题直达 DOI 原文；有「开放获取」标记的可免费读全文。
      </div>
    </div>
  </aside>
</div>
<footer>
  数据源 OpenAlex / Crossref ｜ 打分规则见 <code>config.toml</code> 与 <code>priceradar/score.py</code> ｜
  每日推送上限 {stats.get('digest_size', 10)} 篇
</footer>
<script>{JS}</script>
</body></html>
"""


def _coverage_table(digest: dict) -> str:
    per_journal = digest["stats"].get("per_journal") or {}
    if not per_journal:
        return ""
    picked: dict[str, int] = {}
    for item in digest["items"]:
        picked[item["journal"]] = picked.get(item["journal"], 0) + 1
    rows = []
    for name, info in sorted(per_journal.items(), key=lambda kv: -kv[1]["fetched"]):
        rows.append(
            f"<tr><td>{_e(info.get('display') or name)}</td>"
            f"<td>{_e(info.get('group', ''))}</td>"
            f"<td>{info['fetched']}</td><td>{picked.get(name, 0)}</td></tr>"
        )
    return (
        '<div class="card"><h3 style="margin:0 0 6px;font-size:15px">抓取覆盖情况</h3>'
        "<table><thead><tr><th>期刊</th><th>方向</th><th>窗口内新文</th><th>本期入选</th></tr>"
        f"</thead><tbody>{''.join(rows)}</tbody></table></div>"
    )


# --------------------------------------------------------------------------- #
# RSS：让别人可以「订阅」而不是每天来点你的链接
# --------------------------------------------------------------------------- #
def _rfc822(date_str: str) -> str:
    from email.utils import formatdate

    try:
        stamp = dt.datetime.fromisoformat(str(date_str)[:10]).replace(
            tzinfo=dt.timezone.utc
        ).timestamp()
    except ValueError:
        stamp = dt.datetime.now(tz=dt.timezone.utc).timestamp()
    return formatdate(stamp, usegmt=True)


def _cdata(text: str) -> str:
    return "<![CDATA[" + (text or "").replace("]]>", "]]&gt;") + "]]>"


def render_feed(
    out_dir: Path,
    *,
    public_url: str = "",
    site_title: str = "价格研究日报",
    limit: int = 20,
    per_day: int = 10,
) -> str:
    """把最近若干期日报合成一个 RSS 2.0 feed。

    同事用任何阅读器（Feedly / Inoreader / 甚至邮件客户端）订阅一个地址就够了。
    """
    base = (public_url or "http://localhost:8080/").rstrip("/") + "/"
    entries: list[tuple[str, dict]] = []  # (digest_date, item)
    for date in list(reversed(_existing_dates(out_dir)))[:limit]:
        try:
            data = json.loads((out_dir / f"{date}.json").read_text(encoding="utf-8"))
        except Exception:
            continue
        for item in (data.get("items") or [])[:per_day]:
            entries.append((date, item))

    entries.sort(
        key=lambda pair: (pair[1].get("created_date") or pair[1].get("publication_date") or pair[0]),
        reverse=True,
    )

    items_xml = []
    for date, item in entries:
        link = ""
        if item.get("doi"):
            link = "https://doi.org/" + item["doi"]
        link = link or item.get("landing_page") or (base + f"{date}.html")
        body = (
            f"<p><strong>{html.escape(item.get('journal_display') or item.get('journal') or '')}</strong>"
            f" ｜ 综合分 {item.get('score', 0):.1f}"
            f" ｜ {html.escape(_date_line(item))}</p>"
        )
        if item.get("abstract"):
            body += f"<p>{html.escape(item['abstract'])}</p>"
        else:
            body += "<p><em>该刊未提供摘要，基于标题判相关性。</em></p>"
        if item.get("oa_url"):
            body += f'<p><a href="{html.escape(item["oa_url"])}">开放获取全文</a></p>'
        items_xml.append(
            "    <item>\n"
            f"      <title>{_cdata(item.get('title', ''))}</title>\n"
            f"      <link>{html.escape(link)}</link>\n"
            f"      <guid isPermaLink=\"false\">{html.escape(item.get('id') or link)}</guid>\n"
            f"      <pubDate>{_rfc822(item.get('created_date') or item.get('publication_date') or date)}</pubDate>\n"
            f"      <category>{_cdata(item.get('journal') or '')}</category>\n"
            f"      <description>{_cdata(body)}</description>\n"
            "    </item>"
        )

    now = dt.datetime.now(tz=dt.timezone.utc)
    from email.utils import formatdate

    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">\n'
        "  <channel>\n"
        f"    <title>{html.escape(site_title)}</title>\n"
        f"    <link>{html.escape(base)}</link>\n"
        f'    <atom:link href="{html.escape(base)}feed.xml" rel="self" type="application/rss+xml"/>\n'
        "    <description>每日顶刊价格研究文献精选（大宗商品 / 期货 / 能源 / 农产品价格）</description>\n"
        "    <language>zh-CN</language>\n"
        f"    <lastBuildDate>{formatdate(now.timestamp(), usegmt=True)}</lastBuildDate>\n"
        f"{chr(10).join(items_xml)}\n"
        "  </channel>\n"
        "</rss>\n"
    )


# --------------------------------------------------------------------------- #
# 落盘
# --------------------------------------------------------------------------- #
DATE_GLOB = "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]"


def _existing_dates(out_dir: Path) -> list[str]:
    return sorted(p.stem for p in out_dir.glob(f"{DATE_GLOB}.json"))


def _history_from_files(out_dir: Path) -> list[dict]:
    """从磁盘上的日报反推历史列表，保证侧栏和实际文件一致。"""
    rows = []
    for date in reversed(_existing_dates(out_dir)):
        try:
            data = json.loads((out_dir / f"{date}.json").read_text(encoding="utf-8"))
            pushed = data.get("stats", {}).get("pushed", 0)
        except Exception:
            pushed = 0
        rows.append({"date": date, "pushed": pushed})
    return rows


def write_outputs(
    digest: dict,
    out_dir: Path,
    history: list[dict] | None = None,
    *,
    public_url: str = "",
    site_title: str = "价格研究日报",
) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    date = digest["date"]

    paths = {}
    md_path = out_dir / f"{date}.md"
    md_path.write_text(render_markdown(digest), encoding="utf-8")
    paths["md"] = md_path

    json_path = out_dir / f"{date}.json"
    json_path.write_text(json.dumps(digest, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["json"] = json_path

    # 历史侧栏：以磁盘上的日报为准，与 pipeline 传来的记录合并
    merged: dict[str, dict] = {h["date"]: h for h in (history or [])}
    for row in _history_from_files(out_dir):
        merged.setdefault(row["date"], row)
    merged[date] = {"date": date, "pushed": digest["stats"]["pushed"]}
    history = sorted(merged.values(), key=lambda h: h["date"], reverse=True)

    # 本次不是最新一期时，用已有的最新一期来渲染 index，避免被旧日期覆盖
    dates = _existing_dates(out_dir)
    latest = dates[-1] if dates else date
    if latest != date:
        try:
            digest_for_index = json.loads(
                (out_dir / f"{latest}.json").read_text(encoding="utf-8")
            )
        except Exception:
            digest_for_index = digest
    else:
        digest_for_index = digest

    html_path = out_dir / f"{date}.html"
    html_path.write_text(render_html(digest, history), encoding="utf-8")
    paths["html"] = html_path

    latest_md = out_dir / "latest.md"
    latest_md.write_text(render_markdown(digest_for_index), encoding="utf-8")
    paths["latest_md"] = latest_md

    index = out_dir / "index.html"
    index.write_text(render_html(digest_for_index, history, is_index=True), encoding="utf-8")
    paths["index"] = index

    # RSS：方便别人订阅，也方便接到飞书/Slack/邮件网关
    feed = out_dir / "feed.xml"
    feed.write_text(
        render_feed(out_dir, public_url=public_url, site_title=site_title),
        encoding="utf-8",
    )
    paths["feed"] = feed
    return paths
