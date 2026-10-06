"""Claude APIを使った意味的マッチング（v2）

フィーチャーフラグ: CLAUDE_API_KEY 環境変数が未設定の場合は無効化
キーワードマッチングの上位結果をClaudeが意味的に再評価・説明文を生成
"""
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import config


def is_available() -> bool:
    """Claude APIが利用可能かどうか"""
    return config.CLAUDE_ENABLED


def build_matching_prompt(resume: dict, job: dict) -> str:
    """マッチング用プロンプトを構築（日本語）"""
    resume_text = json.dumps({
        "氏名": resume.get("name"),
        "経験年数": f"{resume.get('years_of_experience')}年",
        "スキル": resume.get("skills"),
        "職歴": [
            {
                "会社": wh.get("company"),
                "職位": wh.get("position"),
                "業務内容": wh.get("description"),
                "業界": wh.get("industry"),
            }
            for wh in resume.get("work_history", [])
        ],
        "希望勤務地": resume.get("desired_locations"),
        "希望単価": f"{resume.get('desired_unit_price_min')}〜{resume.get('desired_unit_price_max')}万円/月",
        "自己PR": resume.get("self_pr"),
    }, ensure_ascii=False, indent=2)

    job_text = json.dumps({
        "案件名": job.get("title"),
        "企業": job.get("company"),
        "業界": job.get("industry"),
        "勤務地": job.get("location"),
        "リモート": job.get("remote_policy"),
        "必須スキル": job.get("required_skills"),
        "歓迎スキル": job.get("preferred_skills"),
        "必要経験年数": f"{job.get('required_experience_years')}年",
        "単価": f"{job.get('unit_price_min')}〜{job.get('unit_price_max')}万円/月",
        "業務内容": job.get("description"),
    }, ensure_ascii=False, indent=2)

    return f"""あなたは採用マッチングの専門家です。
以下の経歴書と案件情報を比較し、マッチ度を0-100で評価してください。

【経歴書】
{resume_text}

【案件】
{job_text}

評価基準:
- スキルの一致度（必須スキルを満たしているか）
- 経験年数の適合度
- 業界知識の関連性
- 勤務地の適合度
- 単価条件の一致度

以下のJSON形式で日本語で回答してください:
{{
  "score": 数値(0-100),
  "strengths": ["この候補者の強み1", "強み2"],
  "gaps": ["不足している点1"],
  "explanation": "総合的な評価コメント（2-3文の日本語）"
}}"""


def semantic_match(resume_id: str, job_id: str) -> dict:
    """Claude APIを使った意味的マッチング

    Returns:
        {
            "score": float (0-100),
            "strengths": list[str],
            "gaps": list[str],
            "explanation": str,
            "error": str (エラー時のみ)
        }
    """
    if not is_available():
        return {
            "score": 0,
            "strengths": [],
            "gaps": [],
            "explanation": "",
            "error": "Claude APIが設定されていません。環境変数 CLAUDE_API_KEY を設定してください。",
        }

    try:
        from anthropic import Anthropic
    except ImportError:
        return {
            "score": 0,
            "strengths": [],
            "gaps": [],
            "explanation": "",
            "error": "anthropic パッケージがインストールされていません。pip install anthropic を実行してください。",
        }

    from config import RESUMES_FILE, JOBS_FILE
    from src.repository.json_resume_repo import JsonResumeRepository
    from src.repository.json_job_repo import JsonJobRepository

    resume_repo = JsonResumeRepository(RESUMES_FILE)
    job_repo = JsonJobRepository(JOBS_FILE)

    resume = resume_repo.find_by_id(resume_id)
    job = job_repo.find_by_id(job_id)

    if resume is None:
        return {"score": 0, "strengths": [], "gaps": [], "explanation": "", "error": f"経歴書ID '{resume_id}' が見つかりません"}
    if job is None:
        return {"score": 0, "strengths": [], "gaps": [], "explanation": "", "error": f"案件ID '{job_id}' が見つかりません"}

    try:
        client = Anthropic(api_key=config.CLAUDE_API_KEY)
        prompt = build_matching_prompt(resume, job)

        message = client.messages.create(
            model=config.CLAUDE_MODEL,
            max_tokens=config.CLAUDE_MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )

        # JSONレスポンスをパース
        response_text = message.content[0].text
        # JSONブロックを抽出
        json_start = response_text.find("{")
        json_end = response_text.rfind("}") + 1
        if json_start >= 0 and json_end > json_start:
            result = json.loads(response_text[json_start:json_end])
            return {
                "score": result.get("score", 0),
                "strengths": result.get("strengths", []),
                "gaps": result.get("gaps", []),
                "explanation": result.get("explanation", ""),
                "error": "",
            }

        return {
            "score": 0,
            "strengths": [],
            "gaps": [],
            "explanation": response_text,
            "error": "",
        }

    except Exception as e:
        return {
            "score": 0,
            "strengths": [],
            "gaps": [],
            "explanation": "",
            "error": f"Claude API呼び出しエラー: {str(e)}",
        }
