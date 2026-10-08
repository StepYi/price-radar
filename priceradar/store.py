"""SQLite 去重存储：保证「每天推送的 10 篇」不会和前几天重复。"""

from __future__ import annotations

import datetime as dt
import re
import sqlite3
from pathlib import Path

from .config import DB_PATH

SCHEMA = """
CREATE TABLE IF NOT EXISTS works (
    key          TEXT PRIMARY KEY,
    doi          TEXT,
    journal      TEXT,
    title        TEXT,
    first_seen   TEXT,
    pushed_date  TEXT,
    score        REAL,
    origin       TEXT
);
CREATE INDEX IF NOT EXISTS idx_works_pushed ON works(pushed_date);
CREATE INDEX IF NOT EXISTS idx_works_title  ON works(title);

CREATE TABLE IF NOT EXISTS runs (
    run_date    TEXT PRIMARY KEY,
    fetched     INTEGER,
    candidates  INTEGER,
    pushed      INTEGER,
    created_at  TEXT
);
"""


def title_fingerprint(title: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", (title or "").lower())[:80]


class Store:
    def __init__(self, path: Path | None = None):
        self.path = Path(path or DB_PATH)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.path)
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.conn.commit()

    # -- 查询 ---------------------------------------------------------------
    def pushed_keys(self) -> tuple[set[str], set[str]]:
        """返回 (已推送的 work_id, 已推送的标题指纹)。

        只统计**真正推送过**的文章：当天没挤进前 10 的候选明天可以继续竞争，
        而不是被永久埋掉。
        """
        ids, fps = set(), set()
        for row in self.conn.execute(
            "SELECT key, title FROM works WHERE pushed_date IS NOT NULL"
        ):
            ids.add(row["key"])
            fp = title_fingerprint(row["title"] or "")
            if fp:
                fps.add(fp)
        return ids, fps

    def is_pushed(self, work_id: str) -> bool:
        row = self.conn.execute(
            "SELECT pushed_date FROM works WHERE key = ?", (work_id,)
        ).fetchone()
        return bool(row and row["pushed_date"])

    def history(self, limit: int = 400) -> list[dict]:
        rows = self.conn.execute(
            "SELECT key, doi, journal, title, pushed_date, score, origin "
            "FROM works WHERE pushed_date IS NOT NULL "
            "ORDER BY pushed_date DESC, score DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(r) for r in rows]

    def runs(self, limit: int = 30) -> list[dict]:
        rows = self.conn.execute(
            "SELECT * FROM runs ORDER BY run_date DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

    def run_for(self, run_date: str) -> dict | None:
        row = self.conn.execute(
            "SELECT * FROM runs WHERE run_date = ?", (run_date,)
        ).fetchone()
        return dict(row) if row else None

    # -- 写入 ---------------------------------------------------------------
    def record_seen(self, works: list[dict], today: dt.date | None = None) -> None:
        today = today or dt.date.today()
        now = dt.datetime.now().isoformat(timespec="seconds")
        rows = []
        for work in works:
            key = work.get("id") or ("doi:" + work.get("doi", ""))
            if not key:
                continue
            rows.append(
                (
                    key,
                    work.get("doi", ""),
                    work.get("journal", ""),
                    work.get("title", ""),
                    today.isoformat(),
                    work.get("pushed_date"),
                    float(work.get("score") or 0.0),
                    work.get("source_origin", ""),
                )
            )
        self.conn.executemany(
            "INSERT INTO works(key, doi, journal, title, first_seen, pushed_date, score, origin) "
            "VALUES(?,?,?,?,?,?,?,?) "
            "ON CONFLICT(key) DO UPDATE SET "
            "  score = CASE WHEN works.pushed_date IS NULL "
            "               THEN excluded.score ELSE works.score END,"
            "  pushed_date = COALESCE(works.pushed_date, excluded.pushed_date),"
            "  doi = CASE WHEN works.doi = '' THEN excluded.doi ELSE works.doi END",
            rows,
        )
        self.conn.commit()

    def mark_pushed(self, works: list[dict], run_date: str) -> None:
        keys = [w.get("id") for w in works if w.get("id")]
        if not keys:
            return
        self.conn.executemany(
            "UPDATE works SET pushed_date = ? WHERE key = ?",
            [(run_date, k) for k in keys],
        )
        self.conn.commit()

    def record_run(self, run_date: str, fetched: int, candidates: int, pushed: int) -> None:
        self.conn.execute(
            "INSERT INTO runs(run_date, fetched, candidates, pushed, created_at) "
            "VALUES(?,?,?,?,?) "
            "ON CONFLICT(run_date) DO UPDATE SET fetched=excluded.fetched, "
            "candidates=excluded.candidates, "
            "pushed=MAX(runs.pushed, excluded.pushed)",
            (run_date, fetched, candidates, pushed, dt.datetime.now().isoformat(timespec="seconds")),
        )
        self.conn.commit()

    def close(self) -> None:
        try:
            self.conn.close()
        except Exception:
            pass
