"""相关性打分：判断一篇文章到底是不是「价格研究」。

设计原则是**可解释**——每一分都记录来源，最终写进日报的「为什么推荐」栏，
方便你判断规则是否合适并随时调整 config.toml 里的关键词。
"""

from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass, field

from .config import Config


# --------------------------------------------------------------------------- #
# 关键词匹配
# --------------------------------------------------------------------------- #
def _term_pattern(term: str) -> str | None:
    tokens = [re.escape(w) for w in re.split(r"[^a-z0-9]+", term.lower()) if w]
    if not tokens:
        return None
    # 末词允许复数：price -> prices, hedge -> hedges
    tokens[-1] = tokens[-1] + "s?"
    return r"[\s\-]+".join(tokens)


def compile_terms(terms: list[str]) -> list[tuple[str, re.Pattern]]:
    out = []
    for term in terms:
        pattern = _term_pattern(term)
        if not pattern:
            continue
        out.append((term, re.compile(r"(?<![a-z0-9])(?:" + pattern + r")(?![a-z0-9])")))
    return out


_HYPHENS = dict.fromkeys(map(ord, "\u2010\u2011\u2012\u2013\u2014\u2212"), "-")


def normalize_text(text: str) -> str:
    if not text:
        return ""
    return text.translate(_HYPHENS).lower()


def hits(compiled: list[tuple[str, re.Pattern]], text: str) -> list[str]:
    found = []
    for term, pattern in compiled:
        if pattern.search(text):
            found.append(term)
    return found


# --------------------------------------------------------------------------- #
# 打分
# --------------------------------------------------------------------------- #
@dataclass
class Scored:
    work: dict
    score: float = 0.0
    relevance_raw: float = 0.0
    core_title: list[str] = field(default_factory=list)
    core_abstract: list[str] = field(default_factory=list)
    context_title: list[str] = field(default_factory=list)
    context_abstract: list[str] = field(default_factory=list)
    method_hits: list[str] = field(default_factory=list)
    excluded: str = ""
    days_old: int = 0
    relevance_level: str = "weak"  # strong / medium / weak
    reasons: list[str] = field(default_factory=list)

    @property
    def keywords(self) -> list[str]:
        seen, out = set(), []
        for term in (
            self.core_title + self.core_abstract
            + self.context_title + self.context_abstract
        ):
            if term not in seen:
                seen.add(term)
                out.append(term)
        return out

    def to_dict(self, rank: int = 0) -> dict:
        work = dict(self.work)
        work.update(
            {
                "rank": rank,
                "score": round(self.score, 2),
                "relevance_raw": round(self.relevance_raw, 2),
                "relevance_level": self.relevance_level,
                "keywords": self.keywords,
                "reasons": self.reasons,
                "days_old": self.days_old,
                "matched": {
                    "core_title": self.core_title,
                    "core_abstract": self.core_abstract,
                    "context_title": self.context_title,
                    "context_abstract": self.context_abstract,
                    "method": self.method_hits,
                },
            }
        )
        return work


RELEVANCE_CAP = 14.0


class Scorer:
    def __init__(self, cfg: Config, today: dt.date | None = None):
        self.cfg = cfg
        self.today = today or dt.date.today()
        self.core = compile_terms(cfg.core_terms)
        self.context = compile_terms(cfg.context_terms)
        self.method = compile_terms(cfg.method_terms)
        self.exclude = compile_terms(cfg.exclude_terms)

    def score(self, work: dict) -> Scored:
        title = normalize_text(work.get("title", ""))
        abstract = normalize_text(work.get("abstract", ""))

        s = Scored(work=work)

        excluded = hits(self.exclude, title)
        if excluded:
            s.excluded = "标题命中排除词：" + "、".join(excluded)
            s.relevance_level = "excluded"
            return s

        s.core_title = hits(self.core, title)
        s.core_abstract = hits(self.core, abstract)
        s.context_title = hits(self.context, title)
        s.context_abstract = hits(self.context, abstract)
        s.method_hits = hits(self.method, title + " " + abstract)

        s.relevance_raw = (
            3.0 * len(s.core_title)
            + 0.8 * len(s.core_abstract)
            + 2.5 * len(s.context_title)
            + 0.6 * len(s.context_abstract)
        )
        if len(s.core_title) == 0 and (len(s.core_abstract) >= 2 or len(s.context_title)):
            s.relevance_level = "medium"
        elif len(s.core_title) == 0 and len(s.core_abstract) == 1:
            s.relevance_level = "weak"
        else:
            s.relevance_level = "strong"

        # --- 时效 ---
        # 锚点优先用「上线/入库日期」：Elsevier 的期号日期常是未来月份，
        # 用它算时效会得到负数，把最老的期号文章排到最前面。
        anchor = (
            work.get("created_date")
            or work.get("publication_date")
            or work.get("issue_date")
            or ""
        )
        try:
            anchor_date = dt.date.fromisoformat(str(anchor)[:10])
            s.days_old = max(0, (self.today - anchor_date).days)
        except ValueError:
            s.days_old = self.cfg.lookback_days

        relevance_norm = min(s.relevance_raw, RELEVANCE_CAP) / RELEVANCE_CAP

        journal = None
        for j in self.cfg.journals:
            if j.name == work.get("journal"):
                journal = j
                break
        weight = journal.weight if journal else 1.0
        journal_norm = max(0.0, min(1.0, (weight - 0.8) / 0.6))

        window = max(self.cfg.lookback_days, 1)
        recency_norm = max(0.0, min(1.0, 1.0 - s.days_old / window))
        method_norm = min(len(s.method_hits), 4) / 4.0
        abstract_bonus = 1.0 if work.get("abstract") else 0.0
        oa_bonus = 0.5 if work.get("oa_url") else 0.0

        s.score = 100.0 * (
            0.50 * relevance_norm
            + 0.20 * journal_norm
            + 0.15 * recency_norm
            + 0.10 * method_norm
            + 0.05 * abstract_bonus
        ) + 1.5 * oa_bonus

        s.reasons = [
            f"相关性 {relevance_norm * 100:.0f}/100（价格词 ×{len(s.core_title)}题名 /"
            f" ×{len(s.core_abstract)}摘要；商品期货词 ×{len(s.context_title)}题名）",
            f"期刊权重 {journal_norm * 100:.0f}/100（{work.get('journal')}）",
            f"时效 {recency_norm * 100:.0f}/100（上线 {s.days_old} 天前）",
            f"方法匹配 {method_norm * 100:.0f}/100"
            + (f"（{'、'.join(s.method_hits[:4])}）" if s.method_hits else ""),
        ]
        if work.get("abstract"):
            s.reasons.append("有摘要，可快速判断")
        if work.get("oa_url"):
            s.reasons.append("有开放获取全文")
        return s

    def passes_gate(self, s: "Scored", strict: bool = True) -> bool:
        return passes_gate(s, self.cfg, strict=strict)


def passes_gate(s: Scored, cfg: Config, strict: bool = True) -> bool:
    """门槛：严格模式要求价格词出现在标题；放宽模式允许只出现在摘要。"""
    if s.excluded:
        return False
    if not cfg.require_price_relevance:
        return True
    if strict:
        return len(s.core_title) >= 1
    signal = (
        len(s.core_title)
        + 0.5 * len(s.core_abstract)
        + 0.5 * len(s.context_title)
    )
    return signal >= 1.0


def dedupe(works: list[dict]) -> list[dict]:
    """同一篇文章可能同时从 OpenAlex 与 Crossref 回来，按 DOI / 标题指纹去重。"""
    by_key: dict[str, dict] = {}
    for work in works:
        keys = []
        if work.get("doi"):
            keys.append("doi:" + work["doi"].lower())
        if work.get("id"):
            keys.append("id:" + work["id"])
        title_fp = re.sub(r"[^a-z0-9]+", "", (work.get("title") or "").lower())[:80]
        if title_fp:
            keys.append("t:" + title_fp)
        if not keys:
            continue
        for key in keys:
            if key in by_key:
                # 保留信息更全的一条（有摘要 / OA 链接优先）
                old = by_key[key]
                if _richness(work) > _richness(old):
                    by_key[key] = work
                break
        else:
            by_key[keys[0]] = work
    return list(by_key.values())


def _richness(work: dict) -> int:
    return (
        (2 if work.get("abstract") else 0)
        + (1 if work.get("doi") else 0)
        + (1 if work.get("oa_url") else 0)
        + min(int(work.get("cited_by_count") or 0), 5)
    )
