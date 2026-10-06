"""スキル抽出共通サービス（REQ-RE5-01/03）

API / Agent / MCP から同じ関数を利用する。

REQ-RE5-01: RAG候補と確定スキルの分離（rag_suggestions）
REQ-RE5-03: 位置ベース重複防止＋Go専用判定
"""
import re
from typing import Optional


# --- スキルパターン生成（REQ-RE3-03, REQ-RE5-03） ---

# 1文字英字スキルのパターン（R言語, C言語）
_SINGLE_LETTER_PATTERNS = {
    "r": re.compile(r"(?<![A-Za-z0-9])R(?:言語)?(?![A-Za-z0-9])", re.IGNORECASE),
    "c": re.compile(r"(?<![A-Za-z0-9])C(?:言語)?(?![A-Za-z0-9])", re.IGNORECASE),
}

# 短い英字スキル（Go, JS, TS）のパターン
# Go: 大文字Go/Go言語/Golangのみ。英単語goは対象外（REQ-RE5-03）
_SHORT_SKILL_PATTERNS = {
    "go": re.compile(r"(?<![A-Za-z0-9])(?:Go(?:言語)?|Golang|golang)(?![A-Za-z0-9])", re.IGNORECASE),
    "js": re.compile(r"(?<![A-Za-z0-9])JS(?![A-Za-z0-9])", re.IGNORECASE),
    "ts": re.compile(r"(?<![A-Za-z0-9])TS(?![A-Za-z0-9])", re.IGNORECASE),
}

# 記号を含むスキル（C++, C#, .NET）のパターン
_SYMBOL_SKILL_PATTERNS = {
    "c++": re.compile(r"(?<![A-Za-z0-9])C\+\+(?![A-Za-z0-9])", re.IGNORECASE),
    "c#": re.compile(r"(?<![A-Za-z0-9])C\#(?![A-Za-z0-9])", re.IGNORECASE),
    ".net": re.compile(r"(?<![A-Za-z0-9])\.NET(?![A-Za-z0-9])", re.IGNORECASE),
}


def _make_skill_search_regex(norm_name: str) -> re.Pattern:
    """スキル名に応じた検索用正規表現を生成（REQ-RE5-03）"""
    if norm_name in _SINGLE_LETTER_PATTERNS:
        return _SINGLE_LETTER_PATTERNS[norm_name]
    if norm_name in _SHORT_SKILL_PATTERNS:
        return _SHORT_SKILL_PATTERNS[norm_name]
    if norm_name in _SYMBOL_SKILL_PATTERNS:
        return _SYMBOL_SKILL_PATTERNS[norm_name]
    if norm_name.isalpha():
        return re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(norm_name) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
    return re.compile(re.escape(norm_name), re.IGNORECASE)


def _has_skill_in_text(norm_name: str, text_lower: str, pattern_cache: dict) -> bool:
    """テキスト中にスキルが存在するかを単語境界考慮で判定"""
    if norm_name not in pattern_cache:
        pattern_cache[norm_name] = _make_skill_search_regex(norm_name)
    return bool(pattern_cache[norm_name].search(text_lower))


def _find_skill_matches(norm_name: str, text_lower: str, pattern_cache: dict) -> list[tuple[int, int]]:
    """スキルの全マッチ位置を返す（REQ-RE5-03: 位置ベース重複除去用）

    Returns:
        [(start, end), ...] のリスト
    """
    if norm_name not in pattern_cache:
        pattern_cache[norm_name] = _make_skill_search_regex(norm_name)
    pattern = pattern_cache[norm_name]
    return [(m.start(), m.end()) for m in pattern.finditer(text_lower)]


def _is_token_valid_skill(token: str) -> bool:
    """トークンが有効なスキル参照かを単語境界考慮で判定（REQ-RE5-03）

    単一tokenマッチで使用。英単語(go/r/cなど)の誤検出を防止する。
    """
    token_lower = token.lower().strip()
    if not token_lower:
        return False

    from src.utils.skill_dictionary import resolve_skill_id

    sid = resolve_skill_id(token_lower)
    if sid is None:
        return False

    # 1文字スキルまたはGo/JS/TSは専用パターンで再確認
    if token_lower in _SINGLE_LETTER_PATTERNS:
        return bool(_SINGLE_LETTER_PATTERNS[token_lower].search(token))
    if token_lower in _SHORT_SKILL_PATTERNS:
        # Go: 大文字Go・Go言語・Golang/golangのみ許可。小文字go/GOは拒否（REQ-RE6-01）
        if token_lower == "go":
            if token in ("Go", "Go言語"):
                return True
            # Golang/golangは大文字小文字両方可
            if token.lower() == "golang":
                return True
            return False
        return bool(_SHORT_SKILL_PATTERNS[token_lower].search(token))
    if token_lower in _SYMBOL_SKILL_PATTERNS:
        return bool(_SYMBOL_SKILL_PATTERNS[token_lower].search(token))

    if token.isalpha():
        pattern = re.compile(
            r"(?<![A-Za-z0-9])" + re.escape(token) + r"(?![A-Za-z0-9])",
            re.IGNORECASE,
        )
        return bool(pattern.search(token))

    return True


def _dedup_by_position(matches: list[dict]) -> list[dict]:
    """位置ベース重複除去（REQ-RE5-03）

    同じ開始位置→長い表現優先。既採用範囲と重なる短い候補を除外。
    C++>C, C#>C, .NET>NET, ASP.NET>.NET の優先順位を実現。

    Args:
        matches: [{"skill_id": str, "start": int, "end": int, "data": dict}, ...]

    Returns:
        重複除去後のリスト
    """
    # 開始位置→長さ降順にソート（同じ位置では長い方が先）
    sorted_matches = sorted(matches, key=lambda m: (m["start"], -m["end"]))

    result = []
    used_ranges = []  # [(start, end), ...]

    for m in sorted_matches:
        start, end = m["start"], m["end"]
        # 既採用範囲と重なるかチェック
        overlap = False
        for us, ue in used_ranges:
            if start < ue and end > us:
                overlap = True
                break
        if not overlap:
            used_ranges.append((start, end))
            result.append(m)

    # skill_id単位で最終重複除去
    seen_ids = set()
    final = []
    for m in result:
        if m["skill_id"] not in seen_ids:
            seen_ids.add(m["skill_id"])
            final.append(m["data"])
    return final


def _evaluate_rag_confidence(suggestion: dict, input_text: str) -> dict:
    """RAG候補の信頼度評価（REQ-RE6-05: 0.85境界＋直接根拠）"""
    from src.utils.skill_dictionary import get_skill_by_id
    skill = get_skill_by_id(suggestion["skill_id"])
    has_direct_evidence = False
    if skill:
        text_lower = input_text.lower()
        for name_variant in [skill.get("name", "")] + skill.get("aliases", []):
            if name_variant.lower() in text_lower:
                has_direct_evidence = True
                break
    suggestion["has_direct_evidence"] = has_direct_evidence
    suggestion["can_auto_save"] = (suggestion["confidence"] >= 0.85 and has_direct_evidence)
    return suggestion


def extract_skills_service(text: str, use_rag: bool = False, top_k: int = 20) -> dict:
    """テキストからスキルを抽出する（共通サービス）

    REQ-RE5-01: RAG候補はrag_suggestionsへ分離
    REQ-RE5-03: 位置ベース重複除去＋Go専用判定

    Returns:
        {"skills": [...], "rag_suggestions": [...], "rag_sources": [...], "warnings": []}
    """
    from src.utils.text_utils import tokenize_japanese
    from src.utils.skill_dictionary import resolve_skill_id, get_skill_by_name, get_all_skills, get_skill_by_id

    tokens = tokenize_japanese(text)
    dict_skills = get_all_skills()

    # 複合語マッチ用
    name_map = {}
    for s in dict_skills:
        for name_variant in [s["name"]] + s.get("aliases", []):
            norm = name_variant.lower().strip()
            if norm and (norm not in name_map or len(norm) > len(name_map[norm][0])):
                name_map[norm] = (norm, s)

    _pattern_cache = {}

    # --- 複合語マッチ（位置情報収集）---
    text_lower = text.lower()
    all_matches = []  # [{skill_id, start, end, data}, ...]

    for norm_name, (original, skill) in sorted(name_map.items(), key=lambda x: -len(x[0])):
        positions = _find_skill_matches(norm_name, text_lower, _pattern_cache)
        for start, end in positions:
            # Go言語: compound matchは大文字小文字区別なしでマッチするが、
            # 小文字goはREQ-RE6-01で禁止。元のテキストで検証
            if norm_name == "go":
                matched_in_original = text[start:end]
                lower_match = matched_in_original.lower()
                # Golang/golangは大文字小文字両方可
                if lower_match == "golang":
                    pass  # OK: both cases allowed
                # Go/Go言語は大文字G必須
                elif matched_in_original in ("Go", "Go言語"):
                    pass  # OK: capital G
                else:
                    continue  # 小文字go/GOなどは拒否
            all_matches.append({
                "skill_id": skill["id"],
                "start": start,
                "end": end,
                "data": {
                    "raw_text": original,
                    "skill_id": skill["id"],
                    "canonical_name": skill["name"],
                    "confidence": 0.98,
                    "registered": True,
                    "source": "dictionary",
                },
            })

    # --- 単一tokenマッチ（位置情報収集）---
    seen_texts = set()
    for token in tokens:
        token_lower = token.lower().strip()
        if not token_lower or token_lower in seen_texts:
            continue
        seen_texts.add(token_lower)

        if not _is_token_valid_skill(token):
            continue

        sid = resolve_skill_id(token_lower)
        if sid is None:
            continue

        # このtokenがテキスト中のどこに出現するか
        pattern = _make_skill_search_regex(token_lower)
        for m in pattern.finditer(text_lower):
            start, end = m.start(), m.end()
            skill = get_skill_by_name(token)
            all_matches.append({
                "skill_id": sid,
                "start": start,
                "end": end,
                "data": {
                    "raw_text": token,
                    "skill_id": sid,
                    "canonical_name": skill["name"] if skill else sid.capitalize(),
                    "confidence": 0.90,
                    "registered": True,
                    "source": "dictionary",
                },
            })

    # 位置ベース重複除去（REQ-RE5-03）
    skills = _dedup_by_position(all_matches)[:top_k]

    # --- RAG補完（REQ-RE5-01: rag_suggestionsへ分離）---
    rag_sources = []
    rag_suggestions = []
    if use_rag:
        try:
            from config import RAG_ENABLED
            if RAG_ENABLED:
                from src.utils.rag_pipeline import search_skill_context
                from src.utils.skill_dictionary import resolve_skill_id as rs_id, get_skill_by_id as gs_by_id

                skills_seen = {s["skill_id"] for s in skills}

                for token in tokens[:10]:
                    for entry in search_skill_context(token, top_k=1):
                        rid = entry.get("id", "")
                        if rid and rid not in rag_sources:
                            rag_sources.append(rid)

                        # RAG候補収集＋信頼度評価（REQ-RE6-05）
                        for sid in entry.get("skill_ids", []):
                            if isinstance(sid, str) and sid not in skills_seen:
                                skill = gs_by_id(sid)
                                if skill:
                                    sug = _evaluate_rag_confidence({
                                        "skill_id": sid,
                                        "canonical_name": skill["name"],
                                        "confidence": 0.70,
                                        "source_id": rid,
                                        "evidence": f"RAG entry: {entry.get('id', '')}",
                                    }, text)
                                    rag_suggestions.append(sug)
                                    #skills_seen.add(sid)

                        for tag in entry.get("tags", []):
                            if isinstance(tag, str):
                                tag_lower = tag.lower().strip()
                                resolved = rs_id(tag_lower)
                                if resolved and resolved not in skills_seen:
                                    skill = gs_by_id(resolved)
                                    if skill:
                                        sug = _evaluate_rag_confidence({
                                            "skill_id": resolved,
                                            "canonical_name": skill["name"],
                                            "confidence": 0.65,
                                            "source_id": rid,
                                            "evidence": f"RAG tag: {tag}",
                                        }, text)
                                        rag_suggestions.append(sug)
                                        #skills_seen.add(resolved)

                        # content（自由文）→ use_rag=false で辞書抽出（再帰防止）
                        content = entry.get("content", "")
                        if content and len(content) > 3:
                            content_lower = content.lower()
                            for s in dict_skills:
                                if s["id"] in skills_seen:
                                    continue
                                for name_variant in [s["name"]] + s.get("aliases", []):
                                    norm = name_variant.lower().strip()
                                    if norm and _has_skill_in_text(norm, content_lower, _pattern_cache):
                                        sug = _evaluate_rag_confidence({
                                            "skill_id": s["id"],
                                            "canonical_name": s["name"],
                                            "confidence": 0.60,
                                            "source_id": rid,
                                            "evidence": f"RAG content: {norm}",
                                        }, text)
                                        rag_suggestions.append(sug)
                                        #skills_seen.add(s["id"])
                                        break
            # 重複除去: 同一skill_idで最高confidenceを採用（REQ-RE6-05）
            if rag_suggestions:
                best = {}
                for s in rag_suggestions:
                    sid = s["skill_id"]
                    if sid not in best or s["confidence"] > best[sid]["confidence"]:
                        best[sid] = s
                rag_suggestions = list(best.values())

        except Exception as e:
            import logging
            _logger = logging.getLogger(__name__)
            _logger.error(f"RAG skill extraction failed: {e}", exc_info=True)

    # top_k制限（REQ-RE6-05）
    if top_k > 0:
        rag_suggestions = rag_suggestions[:top_k]
        rag_sources = rag_sources[:top_k]

    return {
        "skills": skills,
        "rag_suggestions": rag_suggestions,
        "rag_sources": rag_sources,
        "warnings": [],
    }
