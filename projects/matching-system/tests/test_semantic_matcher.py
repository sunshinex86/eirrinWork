"""意味的マッチング（Claude API）のテスト"""
import json
import sys
import tempfile
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch
import pytest

import config
from src.matching.semantic_matcher import (
    is_available,
    build_matching_prompt,
    semantic_match,
)


def _make_mock_anthropic():
    """Claude APIのモックを作成"""
    mock_anthropic = ModuleType("anthropic")
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_content = MagicMock()
    mock_content.text = '{"score": 85, "strengths": ["スキルが合致"], "gaps": ["経験不足"], "explanation": "良いマッチです。"}'
    mock_response.content = [mock_content]
    mock_client.messages.create.return_value = mock_response
    mock_anthropic.Anthropic = MagicMock(return_value=mock_client)
    return mock_anthropic


class TestIsAvailable:
    """利用可否判定のテスト"""

    def test_not_available_by_default(self):
        """APIキー未設定時はFalse"""
        # デフォルトではキー未設定
        assert is_available() == bool(config.CLAUDE_API_KEY)

    def test_available_when_key_set(self, monkeypatch):
        """APIキー設定時はTrue"""
        monkeypatch.setattr(config, "CLAUDE_API_KEY", "sk-ant-test123")
        monkeypatch.setattr(config, "CLAUDE_ENABLED", True)
        assert is_available() is True


class TestBuildMatchingPrompt:
    """プロンプト構築のテスト"""

    def test_prompt_contains_resume_info(self, sample_resume, sample_job):
        """経歴書と案件の情報がプロンプトに含まれること"""
        prompt = build_matching_prompt(sample_resume, sample_job)
        assert "田中 太郎" in prompt
        assert "12年" in prompt
        assert "Pythonバックエンドエンジニア" in prompt
        assert "GHIテクノロジーズ株式会社" in prompt
        assert "0-100" in prompt  # 評価スコア形式の指示

    def test_prompt_is_japanese(self, sample_resume, sample_job):
        """プロンプトが日本語であること"""
        prompt = build_matching_prompt(sample_resume, sample_job)
        assert "【経歴書】" in prompt
        assert "【案件】" in prompt
        assert "評価基準" in prompt
        assert "採用マッチングの専門家" in prompt


class TestSemanticMatch:
    """意味的マッチングのテスト"""

    @pytest.fixture(autouse=True)
    def setup_repos(self, sample_resume, sample_job):
        """テストデータを準備"""
        self.resume_file = Path(tempfile.mktemp(suffix=".json"))
        self.job_file = Path(tempfile.mktemp(suffix=".json"))

        json.dump([sample_resume], open(self.resume_file, "w", encoding="utf-8"))
        json.dump([sample_job], open(self.job_file, "w", encoding="utf-8"))

        self.orig_resume_file = config.RESUMES_FILE
        self.orig_job_file = config.JOBS_FILE
        config.RESUMES_FILE = self.resume_file
        config.JOBS_FILE = self.job_file

        yield

        config.RESUMES_FILE = self.orig_resume_file
        config.JOBS_FILE = self.orig_job_file
        self.resume_file.unlink(missing_ok=True)
        self.job_file.unlink(missing_ok=True)

    def test_graceful_degradation_no_api_key(self):
        """APIキー未設定時のグレースフルデグラデーション"""
        result = semantic_match("resume-001", "job-001")
        assert result["score"] == 0
        assert result["error"] != ""
        assert "CLAUDE_API_KEY" in result["error"]

    def test_graceful_degradation_no_anthropic_package(self, monkeypatch):
        """anthropicパッケージ未インストール時のグレースフルデグラデーション"""
        monkeypatch.setattr(config, "CLAUDE_API_KEY", "sk-ant-test123")
        monkeypatch.setattr(config, "CLAUDE_ENABLED", True)
        # anthropic が実際にない環境 = 実環境の多く
        result = semantic_match("resume-001", "job-001")
        # スコア=0 でエラーメッセージがある
        assert result["score"] == 0
        assert "error" in result

    def test_not_found_resume(self, monkeypatch):
        """存在しない経歴書ID"""
        monkeypatch.setattr(config, "CLAUDE_API_KEY", "sk-ant-test123")
        monkeypatch.setattr(config, "CLAUDE_ENABLED", True)
        # anthropic モジュールをモック
        sys.modules["anthropic"] = _make_mock_anthropic()
        try:
            result = semantic_match("non-existent", "job-001")
            assert "経歴書ID" in result["error"]
        finally:
            del sys.modules["anthropic"]

    def test_not_found_job(self, monkeypatch):
        """存在しない案件ID"""
        monkeypatch.setattr(config, "CLAUDE_API_KEY", "sk-ant-test123")
        monkeypatch.setattr(config, "CLAUDE_ENABLED", True)
        sys.modules["anthropic"] = _make_mock_anthropic()
        try:
            result = semantic_match("resume-001", "non-existent")
            assert "案件ID" in result["error"]
        finally:
            del sys.modules["anthropic"]

    def test_successful_semantic_match(self, monkeypatch):
        """正常系: ClaudeがJSONレスポンスを返す"""
        monkeypatch.setattr(config, "CLAUDE_API_KEY", "sk-ant-test123")
        monkeypatch.setattr(config, "CLAUDE_ENABLED", True)
        sys.modules["anthropic"] = _make_mock_anthropic()
        try:
            result = semantic_match("resume-001", "job-001")
            assert result["score"] == 85
            assert "スキルが合致" in result["strengths"]
            assert result["error"] == ""
        finally:
            del sys.modules["anthropic"]

    def test_claude_api_error_handling(self, monkeypatch):
        """Claude APIエラー時のハンドリング"""
        monkeypatch.setattr(config, "CLAUDE_API_KEY", "sk-ant-test123")
        monkeypatch.setattr(config, "CLAUDE_ENABLED", True)
        mock_anthropic = _make_mock_anthropic()
        mock_anthropic.Anthropic().messages.create.side_effect = Exception("API Error")
        sys.modules["anthropic"] = mock_anthropic
        try:
            result = semantic_match("resume-001", "job-001")
            assert result["score"] == 0
            assert "Claude API呼び出しエラー" in result["error"]
        finally:
            del sys.modules["anthropic"]


class TestBuildMatchingPromptEdgeCases:
    """プロンプト構築のエッジケース"""

    def test_minimal_data(self):
        """最低限のデータでもプロンプトが構築できること"""
        minimal_resume = {
            "id": "r-001", "name": "テスト", "years_of_experience": 0,
            "skills": {}, "work_history": [], "desired_locations": [],
            "desired_unit_price_min": 0, "desired_unit_price_max": 0, "self_pr": "",
        }
        minimal_job = {
            "id": "j-001", "title": "テスト案件", "company": "テスト会社",
            "industry": "", "location": "", "remote_policy": "",
            "required_skills": {}, "preferred_skills": {},
            "required_experience_years": 0, "unit_price_min": 0, "unit_price_max": 0,
            "description": "",
        }
        prompt = build_matching_prompt(minimal_resume, minimal_job)
        assert "テスト" in prompt
        assert len(prompt) > 0
