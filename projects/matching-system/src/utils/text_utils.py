"""日本語テキスト処理ユーティリティ"""
import re
from typing import Optional


def normalize_skill_name(name: str) -> str:
    """スキル名を正規化（小文字化、空白除去、略称統一）
    マッチングの精度を高めるための前処理
    """
    # 基本的な正規化
    normalized = name.strip().lower()
    # 全角英数字・記号→半角
    normalized = normalized.translate(str.maketrans(
        "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺ"
        "ａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ"
        "０１２３４５６７８９"
        "＃＠．，：；！？／",
        "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
        "abcdefghijklmnopqrstuvwxyz"
        "0123456789"
        "#@.,:;!?/"
    ))
    # 連続する空白を1つに
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized


def tokenize_japanese(text: str) -> list[str]:
    """Janomeを使った日本語分かち書き（形態素解析）
    Janomeが利用できない場合は簡易文字分割にフォールバック
    """
    try:
        from janome.tokenizer import Tokenizer
        t = Tokenizer()
        tokens = []
        for token in t.tokenize(text):
            # 名詞・動詞・形容詞・未知語のみ抽出
            part = token.part_of_speech.split(",")[0]
            if part in ("名詞", "動詞", "形容詞"):
                base = token.base_form
                if len(base) > 1:  # 1文字は除外
                    tokens.append(base)
        return tokens if tokens else _fallback_tokenize(text)
    except ImportError:
        return _fallback_tokenize(text)


def _fallback_tokenize(text: str) -> list[str]:
    """Janomeが使えない場合の簡易トークン化"""
    # 句読点や記号で分割
    text = re.sub(r"[、。，．,\.\s]+", " ", text)
    # 2文字以上の単語を抽出（簡易）
    words = [w for w in text.split() if len(w) > 1]
    return words


def extract_skills_from_text(text: str, known_skills: Optional[list[str]] = None,
                              use_rag: bool = False) -> list[str]:
    """自由記述テキストからスキルを抽出する
    known_skills: 既知のスキル一覧（これに含まれる語のみ抽出）
    use_rag: RAG ナレッジベースも利用するか（REQ-10）
    """
    tokens = tokenize_japanese(text)
    skills = []

    # 既知スキルリストがあればそれと照合
    if known_skills:
        known_lower = [s.lower() for s in known_skills]
        for token in tokens:
            if token.lower() in known_lower:
                skills.append(token)
        # テキスト全体からも直接検索（複合語対応）
        text_lower = text.lower()
        for skill in known_skills:
            if skill.lower() in text_lower and skill not in skills:
                skills.append(skill)
    else:
        # 既知リストがなければトークンをそのまま返す
        skills = tokens

    # RAG を利用したスキル抽出補完（REQ-10）
    if use_rag:
        try:
            from config import RAG_ENABLED
            if RAG_ENABLED:
                from src.utils.rag_pipeline import search_skill_context
                for token in tokens[:10]:  # 最初の10トークンのみ
                    rag_results = search_skill_context(token, top_k=1)
                    for r in rag_results:
                        content = r.get("content", "")
                        # コンテンツからスキルらしき語句を補完
                        for t in tokenize_japanese(content):
                            if len(t) > 1 and t not in skills:
                                skills.append(t)
        except Exception:
            pass

    return list(dict.fromkeys(skills))  # 重複除去（順序保持）


def compute_text_similarity(text1: str, text2: str) -> float:
    """2つのテキストの類似度を計算（Jaccard係数ベースの簡易版）"""
    words1 = set(tokenize_japanese(text1))
    words2 = set(tokenize_japanese(text2))

    if not words1 or not words2:
        return 0.0

    intersection = words1 & words2
    union = words1 | words2
    return len(intersection) / len(union) if union else 0.0


def standardize_skill_name(name: str) -> str:
    """スキル名を標準化する（辞書ベースの正規化）

    normalize_skill_name に加えて、スキル辞書と同義語マップを使って
    表記ゆれを吸収し、標準的なスキル名に変換する。

    例:
        "JS" -> "JavaScript"
        "py" -> "Python"
        "k8s" -> "Kubernetes"
        "react.js" -> "React"
        "golang" -> "Go"

    Args:
        name: 標準化前のスキル名

    Returns:
        標準化されたスキル名（辞書にない場合は通常の正規化結果）
    """
    # 1. スキル辞書で直接検索（REQ-02: 辞書が唯一の標準化元）
    dict_name = _lookup_dictionary_name(name)
    if dict_name:
        return dict_name

    # 2. 正規化後に再検索
    normalized = normalize_skill_name(name)
    dict_name = _lookup_dictionary_name(normalized)
    if dict_name:
        return dict_name

    # 3. フォールバック: capitalize
    return normalized.capitalize()


def _lookup_dictionary_name(normalized_name: str) -> Optional[str]:
    """スキル辞書から標準名を検索"""
    try:
        from src.utils.skill_dictionary import get_skill_by_name
        skill = get_skill_by_name(normalized_name)
        if skill:
            return skill["name"]
    except (ImportError, FileNotFoundError):
        pass
    return None
