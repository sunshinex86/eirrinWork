"""市場データ分析ページ

案件・経歴書の登録イベントを集計し、スキル需給・単価トレンド・技術トレンドを可視化する。
"""
from __future__ import annotations

from datetime import date

import altair as alt
import pandas as pd
import requests
import streamlit as st

API_BASE = "http://localhost:8000/api"

# --- house palette（.claude配下 dataviz スキルの検証済みカテゴリカルパレットに準拠） ---
CATEGORICAL = [
    "#2a78d6",  # blue
    "#eb6834",  # orange
    "#1baf7a",  # aqua
    "#eda100",  # yellow
    "#e87ba4",  # magenta
    "#008300",  # green
    "#4a3aa7",  # violet
    "#e34948",  # red
]
COLOR_DEMAND = CATEGORICAL[0]
COLOR_SUPPLY = CATEGORICAL[1]
COLOR_RISING = "#2a78d6"     # diverging pole（成長）
COLOR_DECLINING = "#e34948"  # diverging pole（縮小）

STATUS_LABELS = {"scarce": "🔴 不足", "balanced": "🟡 均衡", "surplus": "🟢 供給過多"}

st.title("📊 市場データ分析")
st.caption(
    "本ページは本システムに蓄積された案件登録・経歴書登録イベントを集計した社内データです"
    "（外部の業界統計ではありません）。運用開始から間もない期間はサンプル数が少なく、"
    "数値はあくまで参考値としてご覧ください。"
)

# --- 期間フィルタ ---
col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input(
        "開始日", value=date(date.today().year, 1, 1), key="market_start_date"
    )
with col_end:
    end_date = st.date_input("終了日", value=date.today(), key="market_end_date")

if start_date > end_date:
    st.error("開始日は終了日以前を指定してください")
    st.stop()

start_str = start_date.isoformat()
end_str = end_date.isoformat()


def _get(path: str, params: dict) -> dict | None:
    """API を呼び出す。接続エラー・異常ステータスはここで警告表示し None を返す。"""
    try:
        resp = requests.get(f"{API_BASE}{path}", params=params, timeout=5)
        if resp.status_code == 200:
            return resp.json()
        st.warning(f"APIエラー（status={resp.status_code}）: {path}")
        return None
    except Exception as e:
        st.warning(f"APIに接続できません。`python run.py` でバックエンドを起動してください。（{e}）")
        return None


def _insufficient_banner(data: dict) -> None:
    if data.get("insufficient_data"):
        st.info("データ蓄積中のため参考値です（サンプル数が少ない状態です）")


tab1, tab2, tab3 = st.tabs(["🧩 技能供需分析", "💰 単価トレンド分析", "📈 技術トレンド分析"])


# ============================================================
# タブ1: 技能供需分析
# ============================================================
def render_supply_demand_tab() -> None:
    data = _get("/market/skill-supply-demand", {"start_date": start_str, "end_date": end_str})
    if data is None:
        return

    _insufficient_banner(data)

    skills = data.get("skills", [])
    if not skills:
        st.info("この期間に該当するスキル需給データはありません")
        return

    df = pd.DataFrame(skills)

    # scarce（不足傾向）スキルを目立たせる
    scarce_df = df[df["status"] == "scarce"]
    if not scarce_df.empty:
        badges = "".join(
            f"<span style='display:inline-block;margin:2px 6px 2px 0;padding:3px 10px;"
            f"border-radius:999px;background:#fee2e2;color:#b91c1c;font-weight:700;font-size:13px;'>"
            f"🔴 {row.skill_id}</span>"
            for row in scarce_df.itertuples()
        )
        st.markdown(f"**⚠️ 不足傾向（需要 > 供給）のスキル：** {badges}", unsafe_allow_html=True)

    # 需要 vs 供給（グループ化棒グラフ）
    chart_df = df.melt(
        id_vars=["skill_id"],
        value_vars=["demand_count", "supply_count"],
        var_name="種別",
        value_name="件数",
    )
    chart_df["種別"] = chart_df["種別"].map(
        {"demand_count": "需要（案件）", "supply_count": "供給（経歴書）"}
    )

    chart = (
        alt.Chart(chart_df)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X("skill_id:N", title="スキル", sort=df["skill_id"].tolist(), axis=alt.Axis(labelAngle=-40)),
            y=alt.Y("件数:Q", title="件数"),
            xOffset=alt.XOffset("種別:N", sort=["需要（案件）", "供給（経歴書）"]),
            color=alt.Color(
                "種別:N",
                scale=alt.Scale(domain=["需要（案件）", "供給（経歴書）"], range=[COLOR_DEMAND, COLOR_SUPPLY]),
                legend=alt.Legend(title=None, orient="top"),
            ),
            tooltip=[
                alt.Tooltip("skill_id:N", title="スキル"),
                alt.Tooltip("種別:N", title="種別"),
                alt.Tooltip("件数:Q", title="件数"),
            ],
        )
        .properties(height=400)
    )
    st.altair_chart(chart, use_container_width=True, theme="streamlit")

    st.markdown("#### 詳細一覧")
    table_df = df.rename(
        columns={
            "skill_id": "スキル",
            "demand_count": "需要件数",
            "supply_count": "供給件数",
            "ratio": "需給比率",
        }
    ).copy()
    table_df["ステータス"] = df["status"].map(STATUS_LABELS).fillna(df["status"])
    st.dataframe(
        table_df[["スキル", "需要件数", "供給件数", "需給比率", "ステータス"]],
        use_container_width=True,
        hide_index=True,
    )


with tab1:
    render_supply_demand_tab()


# ============================================================
# タブ2: 単価トレンド分析
# ============================================================
def render_unit_price_tab() -> None:
    st.markdown("#### フィルタ（任意）")
    col_skill, col_job = st.columns(2)
    with col_skill:
        skill_filter = st.text_input(
            "スキルID", value="", key="price_skill_filter", placeholder="例: python"
        )
    with col_job:
        job_type_filter = st.text_input(
            "職種", value="", key="price_job_type_filter", placeholder="例: エンジニア"
        )

    params: dict = {"start_date": start_str, "end_date": end_str}
    if skill_filter.strip():
        params["skill_id"] = skill_filter.strip()
    if job_type_filter.strip():
        params["job_type"] = job_type_filter.strip()

    data = _get("/market/unit-price-trend", params)
    if data is None:
        return

    _insufficient_banner(data)

    monthly = data.get("monthly", [])
    if not monthly:
        st.info("この条件に該当する単価データはありません")
        return

    df = pd.DataFrame(monthly)
    has_avg = df["avg_unit_price"].notna().any() if "avg_unit_price" in df else False

    if not has_avg:
        st.info("この期間は単価が登録された案件がありません（該当月のサンプル数が0件です）")
    else:
        line_df = df.dropna(subset=["avg_unit_price"])
        line_chart = (
            alt.Chart(line_df)
            .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(filled=True, size=60), color=COLOR_DEMAND)
            .encode(
                x=alt.X("month:N", title="月", sort=df["month"].tolist()),
                y=alt.Y("avg_unit_price:Q", title="平均単価（万円/月）"),
                tooltip=[
                    alt.Tooltip("month:N", title="月"),
                    alt.Tooltip("avg_unit_price:Q", title="平均単価（万円/月）", format=".1f"),
                    alt.Tooltip("median_unit_price:Q", title="中央値（万円/月）", format=".1f"),
                    alt.Tooltip("sample_size:Q", title="件数"),
                ],
            )
            .properties(height=400)
        )
        st.altair_chart(line_chart, use_container_width=True, theme="streamlit")

    st.markdown("#### 月次詳細")
    table_df = df.rename(
        columns={
            "month": "月",
            "avg_unit_price": "平均単価（万円/月）",
            "median_unit_price": "中央値（万円/月）",
            "sample_size": "件数",
            "mom_growth_rate": "前月比成長率",
        }
    )
    st.dataframe(table_df, use_container_width=True, hide_index=True)


with tab2:
    render_unit_price_tab()


# ============================================================
# タブ3: 技術トレンド分析
# ============================================================
def _rising_declining_chart(df: pd.DataFrame, color: str, ascending_sort: str) -> alt.Chart:
    return (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=3, color=color)
        .encode(
            y=alt.Y("skill_id:N", sort=ascending_sort, title=None),
            x=alt.X("growth_rate:Q", title="成長率"),
            tooltip=[
                alt.Tooltip("skill_id:N", title="スキル"),
                alt.Tooltip("growth_rate:Q", title="成長率", format=".1%"),
            ],
        )
        .properties(height=max(120, 32 * len(df)))
    )


def render_tech_trend_tab() -> None:
    data = _get("/market/tech-trend", {"start_date": start_str, "end_date": end_str, "top_n": 10})
    if data is None:
        return

    _insufficient_banner(data)

    rising = data.get("rising", [])
    declining = data.get("declining", [])

    if not rising and not declining:
        st.info("この期間の技術トレンドデータはありません")
        return

    col_rising, col_declining = st.columns(2)

    with col_rising:
        st.markdown("##### 📈 伸びているスキル")
        if not rising:
            st.info("該当データなし")
        else:
            df_r = pd.DataFrame(rising)
            st.altair_chart(
                _rising_declining_chart(df_r, COLOR_RISING, "-x"),
                use_container_width=True,
                theme="streamlit",
            )

    with col_declining:
        st.markdown("##### 📉 縮小しているスキル")
        if not declining:
            st.info("該当データなし")
        else:
            df_d = pd.DataFrame(declining)
            st.altair_chart(
                _rising_declining_chart(df_d, COLOR_DECLINING, "x"),
                use_container_width=True,
                theme="streamlit",
            )

    # 月次推移（上位スキルのみ、多重線グラフ）
    st.markdown("#### 月次推移（上位スキル）")
    top_series: list[tuple[str, dict]] = []
    for item in rising[:4]:
        top_series.append((item.get("skill_id", ""), item.get("monthly_counts", {}) or {}))
    for item in declining[:4]:
        top_series.append((item.get("skill_id", ""), item.get("monthly_counts", {}) or {}))

    rows = [
        {"skill_id": skill_id, "month": month, "count": count}
        for skill_id, monthly_counts in top_series
        for month, count in sorted(monthly_counts.items())
    ]

    if not rows:
        st.info("月次推移データはありません")
        return

    df_trend = pd.DataFrame(rows)
    months_sorted = sorted(df_trend["month"].unique().tolist())
    skill_order = list(dict.fromkeys(skill_id for skill_id, _ in top_series if skill_id))
    palette_for_trend = CATEGORICAL[: len(skill_order)]

    trend_chart = (
        alt.Chart(df_trend)
        .mark_line(strokeWidth=2, point=alt.OverlayMarkDef(filled=True, size=50))
        .encode(
            x=alt.X("month:N", title="月", sort=months_sorted),
            y=alt.Y("count:Q", title="案件件数"),
            color=alt.Color(
                "skill_id:N",
                scale=alt.Scale(domain=skill_order, range=palette_for_trend),
                legend=alt.Legend(title="スキル", orient="right"),
            ),
            tooltip=[
                alt.Tooltip("skill_id:N", title="スキル"),
                alt.Tooltip("month:N", title="月"),
                alt.Tooltip("count:Q", title="案件件数"),
            ],
        )
        .properties(height=380)
    )
    st.altair_chart(trend_chart, use_container_width=True, theme="streamlit")


with tab3:
    render_tech_trend_tab()
