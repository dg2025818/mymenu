import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, date

# --- 페이지 설정 ---
st.set_page_config(
    page_title="고교 급식 칼로리 정밀 비교 분석기 (성남고 중심)",
    page_icon="🥗",
    layout="wide"
)

# --- NEIS API 키 로드 (Streamlit Secrets 연동) ---
API_KEY = st.secrets.get("NEIS_API_KEY", "sample")

API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "B10"  # 서울특별시교육청

# 학교명 및 행정표준코드 (성남고등학교 적용)
SCHOOLS = {
    "성남고등학교": "70101930",
    "당곡고등학교": "7010537",
    "수도여자고등학교": "7010142"
}

# --- 데이터 파싱 및 로드 함수 ---
@st.cache_data(ttl=3600)
def fetch_meal_data(school_code, target_date, api_key):
    """나이스 API에서 안전하게 급식 데이터를 가져옵니다."""
    params = {
        "KEY": api_key,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
        "SD_SCHUL_CODE": school_code,
        "MLSV_YMD": target_date
    }
    
    try:
        response = requests.get(API_URL, params=params, timeout=10)
        if response.status_code != 200:
            return []
            
        data = response.json()
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1].get("row", [])
        return []
    except Exception:
        return []

def parse_calorie(cal_str):
    """칼로리 문자열 안전 정제"""
    if not cal_str or not isinstance(cal_str, str):
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cal_str)
    return float(match.group(1)) if match else 0.0

def clean_menu_text(menu_str):
    """메뉴 특수문자 및 원산지/알레르기 숫자 안전 제거"""
    if not menu_str or not isinstance(menu_str, str):
        return "메뉴 정보 없음"
    cleaned = menu_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    cleaned = cleaned.strip(", ")
    return cleaned if cleaned else "메뉴 정보 없음"

# --- 메인 화면 ---
st.title("🥗 고교 급식 칼로리 정밀 비교 분석기")
st.write("선택한 날짜의 **성남고등학교, 당곡고등학교, 수도여자고등학교** 급식 칼로리를 높은 순으로 정밀 비교합니다.")

# 사이드바 API 상태 표시
st.sidebar.header("⚙️ API 설정 상태")
if "NEIS_API_KEY" in st.secrets:
    st.sidebar.success("🔒 Secrets API Key 적용됨")
else:
    st.sidebar.warning("⚠️ Secrets API Key 미설정 (sample 키 사용 중)")

# 날짜 선택 UI (2025.09 ~ 2026.09 범위 설정)
min_range = date(2025, 9, 1)
max_range = date(2026, 9, 30)
default_selected = date(2026, 9, 7)

selected_date = st.date_input(
    "📅 비교할 날짜 선택 (2025.09 ~ 2026.09)",
    value=default_selected,
    min_value=min_range,
    max_value=max_range
)
date_str = selected_date.strftime("%Y%m%d")

# --- 데이터 수집 ---
today_meals = []

with st.spinner("급식 데이터를 조회하고 있습니다..."):
    for school_name, school_code in SCHOOLS.items():
        rows = fetch_meal_data(school_code, date_str, API_KEY)
        
        if rows:
            for row in rows:
                cal_num = parse_calorie(row.get("CAL_INFO", ""))
                meal_type = row.get("MMEAL_SC_NM", "중식")
                menu = clean_menu_text(row.get("DDISH_NM", ""))
                
                today_meals.append({
                    "학교명": school_name,
                    "식사구분": meal_type,
                    "칼로리(kcal)": cal_num,
                    "메뉴": menu
                })

st.markdown("---")

# --- 결과 및 시각화 출력 ---
if not today_meals:
    st.warning(
        f"🚨 **{selected_date.strftime('%Y년 %m월 %d일')}**은 조회할 수 있는 급식 정보가 없습니다.\n\n"
        f"- 주말, 공휴일, 재량휴업일, 방학 기간이거나 급식 식단이 미등록된 날짜일 수 있습니다."
    )
else:
    df = pd.DataFrame(today_meals)
    df_sorted = df.sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)

    # 📌 1. 성남고등학교 강조 박스
    sungnam_df = df_sorted[df_sorted["학교명"] == "성남고등학교"]
    st.subheader("🏫 성남고등학교 급식 현황")
    
    if sungnam_df.empty:
        st.info("해당 날짜에 성남고등학교의 등록된 급식 정보가 없습니다.")
    else:
        for idx, row in sungnam_df.iterrows():
            rank_list = df_sorted.index[df_sorted["학교명"] == "성남고등학교"].tolist()
            sn_rank = rank_list[0] + 1 if rank_list else "-"
            
            st.success(
                f"🍱 **[성남고 {row['식사구분']}]** — **{row['칼로리(kcal)']} kcal** (3개교 중 **{sn_rank}위**)\n\n"
                f"👉 **메뉴**: {row['메뉴']}"
            )

    st.markdown("---")

    # 📌 2. 칼로리 비교 시각화 차트 (Streamlit 내장 차트 사용 - 라이브러리 충돌 예방)
    st.subheader("📈 학교별 급식 칼로리 시각화 차트")
    
    chart_df = df_sorted.set_index("학교명")[["칼로리(kcal)"]]
    st.bar_chart(chart_df, height=350)

    st.markdown("---")

    # 📌 3. 종합 요약
    st.subheader(f"📢 {selected_date.strftime('%Y-%m-%d')} 전체 칼로리 요약")
    
    if len(df_sorted) > 0:
        top_school = df_sorted.iloc[0]
        lowest_school = df_sorted.iloc[-1]
        total_diff = round(top_school["칼로리(kcal)"] - lowest_school["칼로리(kcal)"], 1)
        
        st.info(
            f"🏆 **가장 칼로리가 높은 학교**: **{top_school['학교명']}** ({top_school['식사구분']} - **{top_school['칼로리(kcal)']} kcal**)\n\n"
            f"📉 **가장 칼로리가 낮은 학교**: **{lowest_school['학교명']}** ({lowest_school['식사구분']} - **{lowest_school['칼로리(kcal)']} kcal**)\n\n"
            f"💡 **최대 칼로리 차이**: **{total_diff} kcal**"
        )
        
        # 📌 4. 학교 간 1:1 비교 차이 안내
        if len(df_sorted) >= 2:
            st.markdown("#### 🔍 학교별 세부 칼로리 차이")
            for i in range(len(df_sorted) - 1):
                h_school = df_sorted.iloc[i]
                l_school = df_sorted.iloc[i+1]
                diff = round(h_school["칼로리(kcal)"] - l_school["칼로리(kcal)"], 1)
                st.write(
                    f"- **{h_school['학교명']}**({h_school['칼로리(kcal)']} kcal)이(가) "
                    f"**{l_school['학교명']}**({l_school['칼로리(kcal)']} kcal)보다 **{diff} kcal** 더 높습니다."
                )

    st.markdown("---")
    
    # 📌 5. 전체 칼로리 순위 목록
    st.subheader("📊 전체 칼로리 순위 목록 (높은 순)")
    df_display = df_sorted.copy()
    df_display.index = df_display.index + 1
    df_display.index.name = "순위"
    
    st.dataframe(
        df_display[["학교명", "식사구분", "칼로리(kcal)", "메뉴"]],
        use_container_width=True
    )

    # 📌 6. 학교별 상세 카드
    st.subheader("📋 학교별 상세 카드")
    cols = st.columns(len(SCHOOLS))
    
    for idx, (school_name, _) in enumerate(SCHOOLS.items()):
        school_data = df_sorted[df_sorted["학교명"] == school_name]
        with cols[idx]:
            header_title = f"⭐ {school_name}" if school_name == "성남고등학교" else f"🏫 {school_name}"
            st.markdown(f"### {header_title}")
            
            if school_data.empty:
                st.caption("등록된 급식 없음")
            else:
                for _, row in school_data.iterrows():
                    st.metric(
                        label=row["식사구분"],
                        value=f"{row['칼로리(kcal)']} kcal"
                    )
                    st.caption(f"**메뉴**: {row['메뉴']}")
