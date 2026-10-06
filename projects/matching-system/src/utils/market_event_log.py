"""市場データ分析用イベントログ

案件掲載・経歴書登録の履歴を、CRUD状態（jobs.json/resumes.json）とは独立に
追記専用（JSONL）で保持する。案件が後から編集・削除されても、
過去に発生した需要・供給のシグナルを市場データ分析から失わないための仕組み。
"""
from __future__ import annotations

import json
import threading
from pathlib import Path
from typing import Any, Optional

import config

EVENTS_FILE = Path(config.DATA_DIR) / "market_events" / "events.jsonl"
_write_lock = threading.Lock()


def _skill_ids(skills: list) -> list[str]:
    ids = []
    for s in skills:
        sid = s.get("skill_id") if isinstance(s, dict) else getattr(s, "skill_id", None)
        if sid:
            ids.append(sid)
    return ids


def _append(event: dict[str, Any]) -> None:
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    with _write_lock:
        with open(EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")


def record_job_posted(job: dict[str, Any]) -> None:
    """案件掲載イベントを記録する（新規作成・サンプル読込時）"""
    skill_ids = _skill_ids(job.get("structured_required_skills", [])) + \
        _skill_ids(job.get("structured_preferred_skills", []))
    _append({
        "event_type": "job_posted",
        "date": job.get("posted_date") or "",
        "entity_id": job.get("id"),
        "skill_ids": skill_ids,
        "unit_price_min": job.get("unit_price_min", 0),
        "unit_price_max": job.get("unit_price_max", 0),
        "industry": job.get("industry", ""),
        "job_type": job.get("job_type", ""),
    })


def record_job_closed(job_id: str) -> None:
    """案件終了（削除）イベントを記録する"""
    _append({"event_type": "job_closed", "entity_id": job_id})


def record_resume_registered(resume: dict[str, Any]) -> None:
    """経歴書登録イベントを記録する（新規作成・サンプル読込時）"""
    skill_ids = _skill_ids(resume.get("structured_skills", []))
    _append({
        "event_type": "resume_registered",
        "date": resume.get("registered_at") or "",
        "entity_id": resume.get("id"),
        "skill_ids": skill_ids,
    })


def read_events(event_type: Optional[str] = None) -> list[dict[str, Any]]:
    """イベントログを全件読み込む（読み取り専用、キャッシュなし）"""
    if not EVENTS_FILE.exists():
        return []
    events = []
    with open(EVENTS_FILE, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event_type is None or ev.get("event_type") == event_type:
                events.append(ev)
    return events
