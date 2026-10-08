"""配置加载与路径管理。"""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONFIG_PATH = ROOT / "config.toml"
DATA_DIR = ROOT / "data"
OUT_DIR = DATA_DIR / "out"
CACHE_PATH = DATA_DIR / "sources_cache.json"
DB_PATH = DATA_DIR / "priceradar.sqlite3"


@dataclass
class Journal:
    name: str
    group: str = "其他"
    tier: int = 2
    weight: float = 1.0
    issn: list[str] = field(default_factory=list)
    openalex_id: str = ""
    openalex_name: str = ""
    publisher: str = ""
    rss_url: str = ""
    enabled: bool = True

    @property
    def label(self) -> str:
        return self.openalex_name or self.name


@dataclass
class Config:
    digest_size: int = 10
    lookback_days: int = 14
    indexed_lookback_days: int = 4
    max_per_journal: int = 3
    require_price_relevance: bool = True
    mailto: str = ""
    http_timeout: int = 45
    request_interval: float = 0.2
    per_page: int = 100
    public_url: str = ""
    site_title: str = "价格研究日报"

    # --- 数据源开关 ---
    use_crossref: bool = True
    use_rss: bool = True
    use_semanticscholar: bool = True
    use_openalex: bool = True
    use_unpaywall: bool = True
    unpaywall_max: int = 40
    enrich_missing_abstract: bool = True
    crossref_rows: int = 200
    s2_batch_size: int = 200
    s2_interval: float = 3.5
    openalex_max_calls: int = 60
    openalex_api_key: str = ""
    s2_api_key: str = ""

    core_terms: list[str] = field(default_factory=list)
    context_terms: list[str] = field(default_factory=list)
    method_terms: list[str] = field(default_factory=list)
    exclude_terms: list[str] = field(default_factory=list)
    journals: list[Journal] = field(default_factory=list)

    def journal_by_name(self, name: str) -> Journal | None:
        low = name.strip().lower()
        for j in self.journals:
            if j.name.lower() == low or j.openalex_name.lower() == low:
                return j
        return None


DEFAULT_CORE = [
    "price", "prices", "pricing", "priced", "price level", "price levels",
    "markup", "markups", "pass through", "inflation", "deflation",
    "asset price", "asset prices", "house price", "housing price",
    "stock price", "share price", "bond price", "commodity price",
    "oil price", "gas price", "electricity price", "power price",
    "carbon price", "food price", "energy price", "relative price",
    "price discovery", "price setting", "price dispersion", "price rigidity",
    "price expectation", "price expectations", "price shock", "price shocks",
    "real price", "nominal price", "market price", "shadow price",
    "price impact", "price efficiency", "price informativeness",
    "price formation", "price bubble", "price bubbles",
    "terms of trade", "exchange rate", "interest rate", "wage",
    "rent", "rents", "cost of capital", "yield", "yields",
]

DEFAULT_CONTEXT = [
    "commodity", "commodities", "futures", "future", "forward", "forwards",
    "spot", "spot market", "derivative", "derivatives", "option", "options",
    "crude", "crude oil", "petroleum", "brent", "wti", "oil", "oil market",
    "natural gas", "gasoline", "diesel", "heating oil", "coal", "lng",
    "electricity", "power market", "wholesale electricity", "carbon",
    "emission", "emissions", "allowance", "renewable", "solar", "wind",
    "agricultural", "agriculture", "grain", "wheat", "corn", "maize",
    "soybean", "rice", "coffee", "cocoa", "sugar", "cotton", "cattle",
    "hog", "livestock", "fertilizer", "metal", "metals", "copper",
    "aluminium", "aluminum", "gold", "silver", "iron ore", "steel",
    "lithium", "rare earth", "uranium",
    "hedging", "hedge", "basis", "convenience yield", "term structure",
    "contango", "backwardation", "storage", "inventory", "inventories",
    "opec", "shale", "speculation", "speculators", "financialization",
    "roll yield", "price discovery", "open interest", "commodity market",
    "commodity markets", "supply shock", "supply shocks", "demand shock",
    "cartel", "export ban", "sanction", "sanctions", "tariff", "tariffs",
    "scarcity", "shortage", "glut",
]

DEFAULT_METHOD = [
    "forecast", "forecasting", "predict", "prediction", "predictive",
    "garch", "stochastic volatility", "implied volatility", "volatility",
    "var", "svar", "vecm", "cointegration", "error correction",
    "high frequency", "intraday", "realized volatility", "jump",
    "machine learning", "neural network", "nowcasting", "state space",
    "structural", "identification", "instrumental variable", "event study",
    "difference in differences", "regression discontinuity", "panel",
    "causal", "elasticity", "equilibrium", "general equilibrium", "dsge",
    "natural experiment", "decomposition", "counterfactual", "welfare",
    "arbitrage", "no arbitrage", "risk premium", "risk premia",
]

DEFAULT_EXCLUDE = [
    "prize", "priceless", "pricey", "nobel", "erratum", "corrigendum",
    "correction to", "editorial", "introduction to the special issue",
    "book review", "call for papers", "front matter", "back matter",
]

WORK_TYPES = {"article", "review"}


def _env(name: str, default: str = "") -> str:
    return os.environ.get(name, default).strip()


def load_config(path: Path | None = None) -> Config:
    path = path or CONFIG_PATH
    with open(path, "rb") as fh:
        raw = tomllib.load(fh)

    general = raw.get("general", {})
    kw = raw.get("keywords", {})
    journals_raw = raw.get("journal", [])
    sources = raw.get("sources", {})

    def src(name: str, default: bool = True) -> bool:
        return bool(sources.get(name, default))

    cfg = Config(
        digest_size=int(general.get("digest_size", 10)),
        lookback_days=int(general.get("lookback_days", 14)),
        indexed_lookback_days=int(general.get("indexed_lookback_days", 4)),
        max_per_journal=int(general.get("max_per_journal", 3)),
        require_price_relevance=bool(general.get("require_price_relevance", True)),
        mailto=_env("PRICERADAR_MAILTO", str(general.get("mailto", ""))),
        http_timeout=int(general.get("http_timeout", 45)),
        request_interval=float(general.get("request_interval", 0.2)),
        per_page=int(general.get("per_page", 100)),
        public_url=_env("PRICERADAR_PUBLIC_URL", str(general.get("public_url", ""))),
        site_title=str(general.get("site_title", "价格研究日报")),
        use_crossref=src("crossref", True),
        use_rss=src("science_direct_rss", True),
        use_semanticscholar=src("semantic_scholar", True),
        use_openalex=src("openalex", True),
        use_unpaywall=src("unpaywall", True),
        unpaywall_max=int(sources.get("unpaywall_max", 40)),
        enrich_missing_abstract=bool(sources.get("enrich_missing_abstract", True)),
        crossref_rows=int(sources.get("crossref_rows", 200)),
        s2_batch_size=int(sources.get("s2_batch_size", 200)),
        s2_interval=float(sources.get("s2_interval", 3.5)),
        openalex_max_calls=int(sources.get("openalex_max_calls", 60)),
        openalex_api_key=_env("OPENALEX_API_KEY", str(sources.get("openalex_api_key", ""))),
        s2_api_key=_env("SEMANTIC_SCHOLAR_API_KEY", str(sources.get("s2_api_key", ""))),
        core_terms=list(kw.get("core", DEFAULT_CORE)),
        context_terms=list(kw.get("context", DEFAULT_CONTEXT)),
        method_terms=list(kw.get("method", DEFAULT_METHOD)),
        exclude_terms=list(kw.get("exclude", DEFAULT_EXCLUDE)),
    )

    for entry in journals_raw:
        cfg.journals.append(
            Journal(
                name=str(entry.get("name", "")).strip(),
                group=str(entry.get("group", "其他")).strip(),
                tier=int(entry.get("tier", 2)),
                weight=float(entry.get("weight", 1.0)),
                issn=[str(x) for x in entry.get("issn", [])],
                openalex_id=str(entry.get("openalex_id", "")).strip(),
                openalex_name=str(entry.get("openalex_name", "")).strip(),
                publisher=str(entry.get("publisher", "")).strip(),
                rss_url=str(entry.get("rss_url", "")).strip(),
                enabled=bool(entry.get("enabled", True)),
            )
        )

    if not cfg.mailto:
        cfg.mailto = "price-radar@example.com"
    return cfg
