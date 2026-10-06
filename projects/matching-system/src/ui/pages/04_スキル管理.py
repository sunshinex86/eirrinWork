"""スキル管理ページ（FIX-06）"""
import streamlit as st
import requests
import pandas as pd

API_BASE = "http://localhost:8000/api"

st.title("🛠️ スキル管理")

tab1, tab2, tab3 = st.tabs(["📋 一覧", "➕ 新規登録", "🔍 検索・確認"])

with tab1:
    st.markdown("### スキル一覧")
    try:
        resp = requests.get(f"{API_BASE}/skills")
        if resp.status_code == 200:
            skills = resp.json().get("skills", [])
            if skills:
                df = pd.DataFrame(skills)
                if "aliases" in df.columns:
                    df["aliases"] = df["aliases"].apply(lambda x: ", ".join(x) if x else "")
                st.dataframe(df, use_container_width=True)
            else:
                st.info("スキルが登録されていません")
        else:
            st.error(f"取得失敗: {resp.text}")
    except Exception as e:
        st.error(f"API接続エラー: {e}")

with tab2:
    st.markdown("### 新規スキル登録")
    name = st.text_input("スキル名（必須）")
    category = st.text_input("カテゴリ（例: programming_language）")
    aliases = st.text_input("別名（カンマ区切り）")
    if st.button("登録", type="primary"):
        if not name.strip():
            st.error("スキル名は必須です")
        else:
            payload = {"name": name.strip(), "category": category.strip()}
            if aliases.strip():
                payload["aliases"] = [a.strip() for a in aliases.split(",") if a.strip()]
            try:
                resp = requests.post(f"{API_BASE}/skills", json=payload)
                if resp.status_code == 201:
                    st.success(f"スキル '{name}' を登録しました (id: {resp.json().get('id')})")
                else:
                    err = resp.json().get("detail", resp.text)
                    st.error(f"登録失敗: {err}")
            except Exception as e:
                st.error(f"API接続エラー: {e}")

with tab3:
    col_search, col_tree, col_refs = st.columns(3)

    with col_search:
        st.markdown("#### スキル検索")
        q = st.text_input("検索語", key="skill_search")
        if q:
            try:
                resp = requests.get(f"{API_BASE}/skills", params={"name": q})
                if resp.status_code == 200:
                    results = resp.json().get("skills", [])
                    if results:
                        for s in results:
                            st.markdown(f"- **{s['name']}** ({s.get('id', '')}) [{s.get('category', '')}]")
                    else:
                        st.info("該当するスキルがありません")
            except Exception as e:
                st.error(f"検索エラー: {e}")

    with col_tree:
        st.markdown("#### ツリー位置確認")
        tid = st.text_input("スキルID", key="tree_skill_id")
        if tid:
            try:
                resp = requests.get(f"{API_BASE}/skills/{tid}/tree")
                if resp.status_code == 200:
                    data = resp.json()
                    path = data.get("path", [])
                    if path:
                        st.markdown("**パス:** " + " → ".join(path))
                    if data.get("node"):
                        st.json(data["node"])
                    else:
                        st.info("ツリー上に見つかりません")
                else:
                    st.error("取得失敗")
            except Exception as e:
                st.error(f"エラー: {e}")

    with col_refs:
        st.markdown("#### 参照確認")
        rid = st.text_input("スキルID", key="ref_skill_id")
        if rid:
            try:
                resp = requests.get(f"{API_BASE}/skills/{rid}/references")
                if resp.status_code == 200:
                    data = resp.json()
                    resumes = data.get("resumes", [])
                    jobs = data.get("jobs", [])
                    if resumes:
                        st.markdown(f"**経歴書 ({len(resumes)}):** {', '.join(resumes)}")
                    if jobs:
                        st.markdown(f"**案件 ({len(jobs)}):** {', '.join(jobs)}")
                    if not resumes and not jobs:
                        st.info("参照している経歴書・案件はありません")
                else:
                    st.error("取得失敗")
            except Exception as e:
                st.error(f"エラー: {e}")

st.markdown("---")
st.markdown("### 管理操作")

col_edit, col_del, col_val = st.columns(3)

with col_edit:
    st.markdown("#### スキル編集")
    edit_id = st.text_input("編集するスキルID", key="edit_skill_id")
    edit_name = st.text_input("新しい名称", key="edit_name")
    edit_cat = st.text_input("新しいカテゴリ", key="edit_cat")
    edit_aliases = st.text_input("新しい別名（カンマ区切り）", key="edit_aliases")
    if st.button("更新", type="primary"):
        if edit_id.strip():
            payload = {}
            if edit_name.strip():
                payload["name"] = edit_name.strip()
            if edit_cat.strip():
                payload["category"] = edit_cat.strip()
            if edit_aliases.strip():
                payload["aliases"] = [a.strip() for a in edit_aliases.split(",") if a.strip()]
            try:
                resp = requests.put(f"{API_BASE}/skills/{edit_id.strip()}", json=payload)
                if resp.status_code == 200:
                    st.success(f"スキル '{edit_id}' を更新しました")
                else:
                    st.error(f"更新失敗: {resp.text}")
            except Exception as e:
                st.error(f"エラー: {e}")

with col_del:
    st.markdown("#### スキル削除（論理削除）")
    del_id = st.text_input("削除するスキルID")
    if st.button("削除", type="secondary"):
        if del_id.strip():
            try:
                resp = requests.delete(f"{API_BASE}/skills/{del_id.strip()}")
                if resp.status_code == 200:
                    data = resp.json()
                    refs = data.get("references", {})
                    st.success(f"スキル '{del_id}' を無効化しました")
                    if refs.get("resumes") or refs.get("jobs"):
                        st.warning(f"参照元あり: {refs}")
                else:
                    st.error(f"削除失敗: {resp.text}")
            except Exception as e:
                st.error(f"エラー: {e}")

with col_val:
    st.markdown("#### 整合性検証")
    if st.button("検証実行"):
        try:
            resp = requests.post(f"{API_BASE}/skills/validate")
            if resp.status_code == 200:
                data = resp.json()
                if data.get("valid"):
                    st.success("整合性 ✓")
                else:
                    for issue in data.get("issues", []):
                        st.warning(issue)
            else:
                st.error(f"検証失敗: {resp.text}")
        except Exception as e:
            st.error(f"エラー: {e}")
