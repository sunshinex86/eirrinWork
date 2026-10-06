"""FastAPIアプリケーション定義"""
import sys
from pathlib import Path

# プロジェクトルートをsys.pathに追加（Streamlit非経由での起動用）
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="経歴書×案件マッチングシステム API",
    description="経歴書と案件の双方向マッチングを行うAPI",
    version="1.0.0",
)

# CORS設定（Streamlitからのアクセスを許可）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ルーターの登録
from src.api.routes_resumes import router as resumes_router
from src.api.routes_jobs import router as jobs_router
from src.api.routes_match import router as match_router
from src.api.routes_skills import router as skills_router
from src.api.routes_market import router as market_router

app.include_router(resumes_router, prefix="/api")
app.include_router(jobs_router, prefix="/api")
app.include_router(match_router, prefix="/api")
app.include_router(skills_router, prefix="/api")
app.include_router(market_router, prefix="/api")


@app.get("/api/health")
def health_check():
    """ヘルスチェック"""
    return {"status": "ok", "service": "matching-system"}
