"""Streamlit メインページ - 経歴書×案件マッチングシステム"""
import streamlit as st

st.set_page_config(
    page_title="経歴書×案件マッチングシステム",
    page_icon="🤝",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("🤝 経歴書×案件マッチングシステム")
st.markdown("---")

st.markdown("""
### このシステムについて

経歴書（人材）と案件（求人）を**双方向**にマッチングするシステムです。

- 📋 **経歴書管理**: 候補者の経歴書を登録・管理します
- 📌 **案件管理**: 求人案件を登録・管理します
- 🎯 **マッチング**: 経歴書から案件を探す／案件から候補者を探す 双方向のマッチングを実行します

### 使い方

1. 左のサイドバーから **経歴書管理** を選び、サンプルデータを読み込む
2. 左のサイドバーから **案件管理** を選び、サンプルデータを読み込む
3. 左のサイドバーから **マッチング** を選び、マッチングを実行する

### マッチングの仕組み

5つの評価軸でスコアリングします：

| 評価軸 | 重み | 内容 |
|--------|------|------|
| スキル一致 | 40% | 必須スキル・歓迎スキルの一致率 |
| 経験年数 | 20% | 必要経験年数との適合度 |
| 勤務地 | 15% | 勤務地・リモート条件の一致度 |
| 業界 | 10% | 業界の関連性 |
| 年収 | 15% | 希望年収と案件年収のオーバーラップ率 |

---
*サイドバーから各機能を選択してください*
""")

# サイドバーにシステム状態を表示
st.sidebar.markdown("### システム状態")

import requests
try:
    resp = requests.get("http://localhost:8000/api/match/status", timeout=3)
    if resp.status_code == 200:
        status = resp.json()
        st.sidebar.metric("経歴書数", status["resume_count"])
        st.sidebar.metric("案件数", status["job_count"])
        ai_status = "✅ 有効" if status["semantic_matching_enabled"] else "⚠️ 無効"
        st.sidebar.metric("AIマッチング", ai_status)
    else:
        st.sidebar.warning("APIが応答していません")
except Exception:
    st.sidebar.warning("APIに接続できません")
    st.sidebar.info("`python run.py` でAPIが起動します")
