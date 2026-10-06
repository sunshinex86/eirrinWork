"""テキスト処理＆スキル抽出ユーティリティのテスト"""
import pytest
from src.utils.text_utils import (
    normalize_skill_name,
    tokenize_japanese,
    extract_skills_from_text,
    compute_text_similarity,
)
from src.utils.skill_extractor import (
    normalize_skill,
    match_skills,
    flatten_skills,
)


class TestNormalizeSkillName:
    """スキル名正規化のテスト"""

    def test_lowercase(self):
        assert normalize_skill_name("Python") == "python"

    def test_trim_whitespace(self):
        assert normalize_skill_name("  Python  ") == "python"

    def test_fullwidth_to_halfwidth(self):
        """全角英数字→半角"""
        assert normalize_skill_name("Ｐｙｔｈｏｎ") == "python"
        assert normalize_skill_name("Ｊａｖａ") == "java"

    def test_fullwidth_numbers(self):
        """全角数字→半角"""
        assert normalize_skill_name("Ｃ＃") == "c#"

    def test_multiple_spaces(self):
        """連続空白→1つに"""
        result = normalize_skill_name("AWS   Lambda")
        assert result == "aws lambda"

    def test_empty_string(self):
        assert normalize_skill_name("") == ""


class TestTokenizeJapanese:
    """日本語形態素解析のテスト"""

    def test_basic_tokenization(self):
        """基本的な分かち書き"""
        tokens = tokenize_japanese("PythonとJavaを使ったWeb開発")
        # Janomeが利用可能なら形態素解析、なければフォールバック
        assert len(tokens) > 0

    def test_empty_text(self):
        assert tokenize_japanese("") == []

    def test_single_char_filtered(self):
        """1文字は除外されること（簡易フォールバックの場合）"""
        tokens = tokenize_japanese("A B C")
        # 1文字は除外される
        for t in tokens:
            assert len(t) > 1

    def test_with_special_chars(self):
        """句読点が適切に処理されること"""
        tokens = tokenize_japanese("Python、Java。TypeScript")
        assert len(tokens) >= 3


class TestExtractSkillsFromText:
    """テキストからのスキル抽出テスト"""

    def test_with_known_skills(self):
        """既知スキルリストがある場合"""
        text = "PythonとDjangoを使ったWebアプリケーション開発"
        known = ["Python", "Django", "React", "AWS"]
        skills = extract_skills_from_text(text, known_skills=known)
        assert "Python" in skills
        assert "Django" in skills

    def test_without_known_skills(self):
        """既知スキルリストがない場合（トークンをそのまま返す）"""
        text = "Python開発"
        skills = extract_skills_from_text(text)
        assert len(skills) > 0

    def test_empty_text(self):
        assert extract_skills_from_text("") == []
        assert extract_skills_from_text("", known_skills=["Python"]) == []

    def test_deduplication(self):
        """重複が除去されること"""
        text = "Python Python Django Django"
        known = ["Python", "Django"]
        skills = extract_skills_from_text(text, known_skills=known)
        assert skills.count("Python") == 1
        assert skills.count("Django") == 1


class TestComputeTextSimilarity:
    """テキスト類似度計算のテスト"""

    def test_identical_texts(self):
        assert compute_text_similarity("Python Django", "Python Django") == 1.0

    def test_different_texts(self):
        assert compute_text_similarity("Python", "Java") == 0.0

    def test_partial_overlap(self):
        score = compute_text_similarity("Python Django AWS", "Python Django React")
        assert 0.0 < score < 1.0

    def test_empty_texts(self):
        assert compute_text_similarity("", "Python") == 0.0
        assert compute_text_similarity("", "") == 0.0


class TestSkillExtractor:
    """スキル抽出器のテスト"""

    def test_normalize_skill_synonym(self):
        """シノニムによる正規化"""
        assert normalize_skill("JS") == "javascript"
        assert normalize_skill("js") == "javascript"
        assert normalize_skill("TS") == "typescript"
        assert normalize_skill("PY") == "python"
        assert normalize_skill("k8s") == "kubernetes"

    def test_normalize_skill_no_synonym(self):
        """シノニムがない場合はそのまま"""
        assert normalize_skill("Ruby") == "ruby"

    def test_normalize_skill_with_fullwidth(self):
        """全角文字も正規化される"""
        assert normalize_skill("Ｐｙｔｈｏｎ") == "python"


class TestMatchSkills:
    """スキル一致判定のテスト"""

    def test_all_matched(self):
        """全スキル一致"""
        candidate = ["Python", "Django", "Docker", "Git"]
        required = ["Python", "Docker"]
        matched, missing = match_skills(candidate, required)
        assert set(matched) == {"Python", "Docker"}
        assert missing == []

    def test_partial_match(self):
        """一部不一致"""
        candidate = ["Python", "Django"]
        required = ["Python", "Go", "Rust"]
        matched, missing = match_skills(candidate, required)
        assert matched == ["Python"]
        assert set(missing) == {"Go", "Rust"}

    def test_synonym_match(self):
        """シノニム経由の一致"""
        candidate = ["JS", "TS", "React"]
        required = ["JavaScript", "TypeScript"]
        matched, missing = match_skills(candidate, required)
        # "JS" → "javascript", "TS" → "typescript" に正規化されるので一致する
        assert set(matched) == {"JavaScript", "TypeScript"}

    def test_partial_string_match(self):
        """部分文字列一致"""
        candidate = ["REST API設計経験"]
        required = ["REST API"]
        matched, missing = match_skills(candidate, required)
        assert len(matched) == 1  # "REST API" が "REST API設計経験" に部分一致

    def test_case_insensitive(self):
        """大文字小文字を区別しない"""
        candidate = ["python", "DJANGO"]
        required = ["Python", "django"]
        matched, missing = match_skills(candidate, required)
        assert len(matched) == 2

    def test_empty_lists(self):
        matched, missing = match_skills([], [])
        assert matched == []
        assert missing == []

    def test_no_match(self):
        candidate = ["Ruby", "Rails"]
        required = ["Python", "Django"]
        matched, missing = match_skills(candidate, required)
        assert matched == []
        assert set(missing) == {"Python", "Django"}


class TestFlattenSkills:
    """スキルフラット化のテスト"""

    def test_standard_skill_dict(self):
        skills = {
            "languages": ["Python", "Java"],
            "frameworks": ["Django"],
            "tools": ["Docker"],
            "certifications": ["AWS SAA"],
            "other": ["アジャイル"],
        }
        result = flatten_skills(skills)
        assert len(result) == 6
        assert "Python" in result
        assert "AWS SAA" in result

    def test_empty_skill_dict(self):
        assert flatten_skills({}) == []

    def test_partial_skill_dict(self):
        skills = {"languages": ["Python"], "frameworks": []}
        result = flatten_skills(skills)
        assert result == ["Python"]


class TestStandardizeSkillName:
    """スキル名標準化のテスト"""

    def test_synonym_js_to_javascript(self):
        """JS -> JavaScript"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("JS")
        assert result == "JavaScript"

    def test_synonym_py_to_python(self):
        """py -> Python"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("py")
        assert result == "Python"

    def test_synonym_k8s_to_kubernetes(self):
        """k8s -> Kubernetes"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("k8s")
        assert result == "Kubernetes"

    def test_synonym_golang_to_go(self):
        """golang -> Go"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("golang")
        assert result == "Go"

    def test_dictionary_lookup_full_name(self):
        """辞書にある正式名はそのまま"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("Python")
        assert result == "Python"

    def test_dictionary_lookup_framework(self):
        """フレームワーク名の標準化"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("react.js")
        assert result == "React"

    def test_unknown_skill_fallback(self):
        """辞書にないスキルはcapitalize"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("some-unknown-skill")
        assert result == "Some-unknown-skill"

    def test_fullwidth_characters(self):
        """全角文字も正規化される"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("Ｐｙｔｈｏｎ")
        assert result == "Python"

    def test_django_framework(self):
        """Django フレームワーク"""
        from src.utils.text_utils import standardize_skill_name
        result = standardize_skill_name("django")
        assert result == "Django"



class TestNLPExtraction:
    """REQ-RE4-02/04: NLP短技能抽出の本番処理テスト"""

    def test_extract_go(self):
        """Go言語経験あり → go"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("Go言語経験あり", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "go" in ids, f"Expected 'go' in {ids}"

    def test_extract_js_ts(self):
        """JSとTSを使用 → javascript, typescript"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("JSとTSを使用", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "javascript" in ids, f"Expected 'javascript' in {ids}"
        assert "typescript" in ids, f"Expected 'typescript' in {ids}"

    def test_extract_cpp(self):
        """C++経験 → cpp"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("C++経験", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "cpp" in ids, f"Expected 'cpp' in {ids}"

    def test_extract_csharp(self):
        """C#経験 → csharp"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("C#経験", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "csharp" in ids, f"Expected 'csharp' in {ids}"

    def test_extract_dotnet(self):
        """.NET Framework → dotnet"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service(".NET Framework", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "dotnet" in ids, f"Expected 'dotnet' in {ids}"

    def test_extract_r(self):
        """R言語で分析 → r"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("R言語で分析", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "r" in ids, f"Expected 'r' in {ids}"

    def test_extract_c_lang(self):
        """C言語開発 → c"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("C言語開発", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "c" in ids, f"Expected 'c' in {ids}"

    # 誤検出禁止テスト
    def test_no_false_server_admin(self):
        """server administration → se, r を抽出しない"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("server administration", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "r" not in ids, f"False positive 'r' in {ids}"

    def test_no_false_google_cloud(self):
        """Google Cloud → go を抽出しない"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("Google Cloud experience", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "go" not in ids, f"False positive 'go' in {ids}"

    # 大文字小文字テスト
    def test_case_insensitive_go_rejected(self):
        """go (lowercase) → 抽出なし（REQ-RE6-01: 小文字goは拒否）"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("go言語経験", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "go" not in ids, f"Lowercase 'go' should be rejected, but found in {ids}"

    def test_case_insensitive_js(self):
        """js (lowercase) → javascript"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("jsフレームワーク", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "javascript" in ids, f"Expected 'javascript' from 'js' in {ids}"

    def test_golang_both_cases(self):
        """Golang/golang → go"""
        from src.utils.skill_extraction_service import extract_skills_service
        r1 = extract_skills_service("Golang開発", use_rag=False)
        r2 = extract_skills_service("golang開発", use_rag=False)
        ids1 = [s["skill_id"] for s in r1.get("skills", [])]
        ids2 = [s["skill_id"] for s in r2.get("skills", [])]
        assert "go" in ids1, f"Expected 'go' from 'Golang' in {ids1}"
        assert "go" in ids2, f"Expected 'go' from 'golang' in {ids2}"

    def test_plain_go_rejected(self):
        """I go to work → 抽出なし"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("I go to work", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "go" not in ids, f"Plain 'go' should be rejected, found in {ids}"

    def test_google_cloud_no_go(self):
        """Google Cloud → goなし"""
        from src.utils.skill_extraction_service import extract_skills_service
        result = extract_skills_service("Google Cloud", use_rag=False)
        ids = [s["skill_id"] for s in result.get("skills", [])]
        assert "go" not in ids, f"'go' should not be extracted from 'Google Cloud', found in {ids}"