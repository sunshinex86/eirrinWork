"""
アプリケーション設定
マッチングの重み、ファイルパス、フィーチャーフラグを一元管理
"""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

# プロジェクトルート
ROOT_DIR = Path(__file__).parent

# データファイルパス
DATA_DIR = ROOT_DIR / "data"
RESUMES_FILE = DATA_DIR / "resumes.json"
JOBS_FILE = DATA_DIR / "jobs.json"
SAMPLE_RESUMES_FILE = DATA_DIR / "sample_resumes.json"
SAMPLE_JOBS_FILE = DATA_DIR / "sample_jobs.json"

# マッチング重み（環境変数で上書き可能）
MATCHING_WEIGHTS = {
    "skill_match": float(os.getenv("WEIGHT_SKILL", "0.40")),
    "experience_match": float(os.getenv("WEIGHT_EXPERIENCE", "0.20")),
    "location_match": float(os.getenv("WEIGHT_LOCATION", "0.15")),
    "industry_match": float(os.getenv("WEIGHT_INDUSTRY", "0.10")),
    "unit_price_match": float(os.getenv("WEIGHT_UNIT_PRICE", "0.15")),
}

# Claude API フィーチャーフラグ
CLAUDE_API_KEY = os.getenv("CLAUDE_API_KEY", "")
CLAUDE_ENABLED = bool(CLAUDE_API_KEY)
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "1024"))

# 埋め込みモデル設定
EMBEDDING_ENABLED = os.getenv("EMBEDDING_ENABLED", "false").lower() in ("true", "1", "yes")
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "paraphrase-multilingual-MiniLM-L12-v2")

# ハイブリッドマッチング重み（10軸、REQ-FIX-02）
HYBRID_WEIGHTS = {
    "required_skill": float(os.getenv("HW_REQUIRED_SKILL", "0.20")),
    "preferred_skill": float(os.getenv("HW_PREFERRED_SKILL", "0.08")),
    "skill_depth": float(os.getenv("HW_SKILL_DEPTH", "0.12")),
    "skill_hierarchy": float(os.getenv("HW_SKILL_HIERARCHY", "0.08")),
    "experience": float(os.getenv("HW_EXPERIENCE", "0.07")),
    "location": float(os.getenv("HW_LOCATION", "0.08")),
    "context": float(os.getenv("HW_CONTEXT", "0.10")),
    "role": float(os.getenv("HW_ROLE", "0.08")),
    "unit_price": float(os.getenv("HW_UNIT_PRICE", "0.07")),
    "embedding": float(os.getenv("HW_EMBEDDING", "0.12")),
}

# サンプルデータ読込設定
ENABLE_SAMPLE_LOAD = os.getenv("ENABLE_SAMPLE_LOAD", "true").lower() in ("true", "1", "yes")

# RAG 設定
RAG_ENABLED = os.getenv("RAG_ENABLED", "").lower() in ("true", "1", "yes")
RAG_KNOWLEDGE_DIR = os.getenv("RAG_KNOWLEDGE_DIR", str(DATA_DIR / "knowledge"))
RAG_CONTEXT_SIMILARITY_THRESHOLD = float(os.getenv("RAG_CONTEXT_SIMILARITY_THRESHOLD", "0.70"))

# API設定
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", "8000"))
STREAMLIT_PORT = int(os.getenv("STREAMLIT_PORT", "8501"))

# 業界の関連性マッピング（簡易版）
INDUSTRY_GROUPS = {
    "IT・通信": ["IT・通信", "インターネット", "ソフトウェア", "情報処理"],
    "製造": ["製造", "メーカー", "自動車", "電機"],
    "金融": ["金融", "銀行", "保険", "証券"],
    "医療": ["医療", "病院", "ヘルスケア", "介護"],
    "小売": ["小売", "流通", "卸売", "EC"],
    "サービス": ["サービス", "コンサルティング", "人材", "教育"],
}
