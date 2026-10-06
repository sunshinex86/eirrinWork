"""AIエージェントスキル定義（REQ-10/13）

マッチングシステム内でAIエージェントが実行するスキルを定義する。
各スキルは tool として登録され、API/Agent/MCP から同じサービス層を利用する。
実行ログとエラー情報を記録する。
"""
import logging

_logger = logging.getLogger(__name__)

from src.agent.skills.matching_skills import (
    analyze_skill_gap,
    get_industry_context,
    suggest_skill_improvements,
    rank_matches_with_reason,
    validate_skill_consistency,
    extract_skills,
)
from src.utils.recommendation_reasoning_service import build_recommendation_reason
from src.utils.jd_optimization_service import optimize_jd
from src.utils.recommendation_action_service import build_recommendation_actions
from src.utils.schedule_management_service import model_availability, detect_schedule_conflicts

# スキル定義レジストリ（名前・説明・入出力スキーマ）
SKILL_REGISTRY = {
    "rank_matches": {
        "name": "rank_matches",
        "description": "マッチ結果をスコア順にソートし、各結果に理由付けを行う",
        "input_schema": {
            "type": "object",
            "properties": {
                "matches": {
                    "type": "array",
                    "items": {"type": "object"},
                    "description": "マッチ結果のリスト（各要素に total_score を含む）"
                }
            },
            "required": ["matches"]
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "rank": {"type": "integer"},
                    "target": {"type": "string"},
                    "score": {"type": "number"},
                    "level": {"type": "string"},
                    "reason": {"type": "string"}
                }
            }
        },
        "function": rank_matches_with_reason,
    },
    "suggest_improvements": {
        "name": "suggest_improvements",
        "description": "不足スキルに対する学習・改善提案を生成する",
        "input_schema": {
            "type": "object",
            "properties": {
                "missing_skills": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "不足しているスキル一覧"
                },
                "target_role": {
                    "type": "string",
                    "description": "目標ロール（任意）"
                }
            },
            "required": ["missing_skills"]
        },
        "output_schema": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "skill": {"type": "string"},
                    "found_in_dictionary": {"type": "boolean"},
                    "skill_path": {"type": "string"},
                    "suggestion": {"type": "string"}
                }
            }
        },
        "function": suggest_skill_improvements,
    },
    "validate_consistency": {
        "name": "validate_consistency",
        "description": "スキル辞書とツリーの整合性をチェックする（重複ID・孤立ノード検出）",
        "input_schema": {
            "type": "object",
            "properties": {},
            "required": []
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "valid": {"type": "boolean"},
                "errors": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}}
            }
        },
        "function": validate_skill_consistency,
    },
    "analyze_skill_gap": {
        "name": "analyze_skill_gap",
        "description": "候補者と案件のスキルギャップを分析する",
        "input_schema": {
            "type": "object",
            "properties": {
                "resume_skills": {"type": "array", "items": {"type": "string"}},
                "required_skills": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["resume_skills", "required_skills"]
        },
        "output_schema": {"type": "object"},
        "function": analyze_skill_gap,
    },
    "get_industry_context": {
        "name": "get_industry_context",
        "description": "業界に関連する知識をナレッジベースから取得する",
        "input_schema": {
            "type": "object",
            "properties": {
                "industry_name": {"type": "string"}
            },
            "required": ["industry_name"]
        },
        "output_schema": {"type": "object"},
        "function": get_industry_context,
    },
    "extract_skills": {
        "name": "extract_skills",
        "description": "自由記述テキストからスキルを抽出する（NLP + 辞書標準化）",
        "input_schema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "minLength": 1, "maxLength": 20000},
                "use_rag": {"type": "boolean", "default": False},
                "top_k": {"type": "integer", "minimum": 1, "maximum": 100, "default": 20}
            },
            "required": ["text"]
        },
        "output_schema": {
            "type": "object",
            "properties": {
                "skills": {"type": "array"},
                "rag_suggestions": {"type": "array", "items": {"type": "object"}},
                "rag_sources": {"type": "array", "items": {"type": "string"}},
                "warnings": {"type": "array", "items": {"type": "string"}}
            }
        },
        "function": extract_skills,
    },
    "recommendation_reason": {
        "name": "recommendation_reason",
        "description": "候補者と案件の推薦理由をスキル・業界・経験の観点で分解しギャップ分析する",
        "input_schema": {
            "type": "object",
            "properties": {
                "resume_id": {"type": "string"},
                "job_id": {"type": "string"}
            },
            "required": ["resume_id", "job_id"]
        },
        "output_schema": {"type": "object"},
        "function": build_recommendation_reason,
    },
    "optimize_jd": {
        "name": "optimize_jd",
        "description": "JDを自動最適化し、スキル抽出と予算妥当性分析を行う",
        "input_schema": {
            "type": "object",
            "properties": {
                "raw_jd": {"type": "string", "minLength": 1, "maxLength": 40000},
                "budget_range": {
                    "type": "object",
                    "properties": {
                        "unit_price_max": {"type": "integer"}
                    }
                }
            },
            "required": ["raw_jd"]
        },
        "output_schema": {"type": "object"},
        "function": optimize_jd,
    },
    "build_recommendation_actions": {
        "name": "build_recommendation_actions",
        "description": "推薦順位、連絡優先度、自動コミュニケーション生成を行う",
        "input_schema": {
            "type": "object",
            "properties": {
                "resume_id": {"type": "string"},
                "top_n": {"type": "integer", "minimum": 1, "maximum": 20, "default": 5}
            },
            "required": ["resume_id"]
        },
        "output_schema": {"type": "object"},
        "function": build_recommendation_actions,
    },
    "model_availability": {
        "name": "model_availability",
        "description": "候補者のavailabilityをモデリングしてスケジュール適合度を測る",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_availability": {"type": "object"},
                "job_window": {"type": "object"}
            },
            "required": ["candidate_availability", "job_window"]
        },
        "output_schema": {"type": "object"},
        "function": model_availability,
    },
    "detect_schedule_conflicts": {
        "name": "detect_schedule_conflicts",
        "description": "候補者の予定と競合イベントの重複を検知する",
        "input_schema": {
            "type": "object",
            "properties": {
                "candidate_availability": {"type": "object"},
                "other_events": {"type": "array", "items": {"type": "object"}}
            },
            "required": ["candidate_availability", "other_events"]
        },
        "output_schema": {"type": "object"},
        "function": detect_schedule_conflicts,
    },
}

def get_skill_definitions() -> list[dict]:
    """全スキル定義を返す（API/Agent/MCP 共通インターフェース）"""
    return [
        {
            "name": info["name"],
            "description": info["description"],
            "inputSchema": info["input_schema"],
        }
        for info in SKILL_REGISTRY.values()
    ]

def execute_skill(skill_name: str, params: dict) -> dict:
    """スキルを実行する（REQ-13: 実行ログ記録）
    Args:
        skill_name: スキル名
        params: 入力パラメータ
    Returns:
        実行結果
    """
    _logger.info(f"SKILL executed: {skill_name}, params={params}")
    if skill_name not in SKILL_REGISTRY:
        _logger.warning(f"SKILL unknown: {skill_name}")
        return {"error": f"Unknown skill: {skill_name}"}
    info = SKILL_REGISTRY[skill_name]
    try:
        result = info["function"](**params)
        _logger.info(f"SKILL success: {skill_name}, result_size={len(str(result))}")
        return {"result": result}
    except Exception as e:
        _logger.error(f"SKILL error: {skill_name}, error={e}", exc_info=True)
        return {"error": str(e)}
