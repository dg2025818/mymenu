import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, date

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="고교 급식 칼로리 비교 분석기",
    page_icon="🥗",
    layout="wide"
)

# --- API 및 학교 정보 설정 ---
API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "B10"  # 서울특별시교육청

SCHOOLS = {
    "성남고등학교": "70101930",
    "당곡고등학교": "7010537",
    "수도여자고등학교": "7010142"
}

# --- 데이터 파싱 및 로드 함수 ---
@st.cache_data(ttl=3600)
def fetch_meal_data(school_code, target_date, api_key="sample"):
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
        data = response.json()
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
        return []
    except Exception:
        return []

def parse_calorie(cal_str):
    if not cal_str:
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cal_str)
    return float(match.group(1)) if match else 0.0

def clean_menu_text(menu_str):
    if not menu_str:
        return "메뉴 정보 없음"
    cleaned = menu_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    return cleaned.strip(", ")

# --- UI 화면 구성을 위한 헤더 ---
st.title("🥗 고교 급식 칼로리 정밀 비교 분석")
st.write("선택한 날짜의 **성남고, 당곡고, 수도여고** 급식 칼로리를 비교하여 어느 학교의 급식이 더 칼로리가 높은지 한눈에 분석합니다.")

# 기본 날짜 설정: 2026년 9월 7일
default_date = date(2026, 9, 7)
selected_date = st.date_input("📅 비교할 날짜 선택", value=default_date)
date_str = selected_date.strftime("%Y%m%d")

api_key = st.sidebar.text_input("NEIS API Key", value="sample")

# --- 데이터 수집 및 처리 ---
today_meals = []

with st.spinner("학교별 급식 정보 및 칼로리를 수집/분석 중입니다..."):
    for school_name, school_code in SCHOOLS.items():
        rows = fetch_meal_data(school_code, date_str, api_key)
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

# --- 결과 및 분석 출력 ---
if not today_meals:
    st.info(f"💡 **{selected_date.strftime('%Y년 %m월 %d일')}**은 등록된 급식 정보가 없거나 휴업일/주말입니다.")
else:
    df = pd.DataFrame(today_meals)
    
    # 칼로리 내림차순 정렬 (높은 순 -> 낮은 순)
    df_sorted = df.sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)
    
    # 1. 비교 브리핑 요약
    st.subheader(f"📢 {selected_date.strftime('%Y년 %m월 %d일')} 칼로리 비교 요약")
    
    top_school = df_sorted.iloc[0]
    lowest_school = df_sorted.iloc[-1]
    total_diff = round(top_school["칼로리(kcal)"] - lowest_school["칼로리(kcal)"], 1)
    
    st.success(
        f"🏆 **가장 칼로리가 높은 학교**: **{top_school['학교명']}** ({top_school['식사구분']} - **{top_school['칼로리(kcal)']} kcal**)\n\n"
        f"📉 **가장 칼로리가 낮은 학교**: **{lowest_school['학교명']}** ({lowest_school['식사구분']} - **{lowest_school['칼로리(kcal)']} kcal**)\n\n"
        f"💡 **최대 칼로리 차이**: **{total_diff} kcal**"
    )
    
    # 2. 학교 간 1:1 세부 비교 문장 출력
    if len(df_sorted) >= 2:
        st.markdown("#### 🔍 학교별 칼로리 차이 정밀 분석")
        for i in range(len(df_sorted) - 1):
            h_school = df_sorted.iloc[i]
            l_school = df_sorted.iloc[i+1]
            diff = round(h_school["칼로리(kcal)"] - l_school["칼로리(kcal)"], 1)
            st.write(
                f"- **{h_school['학교명']}**({h_school['칼로리(kcal)']} kcal)이(가) "
                f"**{l_school['학교명']}**({l_school['칼로리(kcal)']} kcal)보다 **{diff} kcal** 더 높습니다."
            )

    st.markdown("---")
    
    # 3. 칼로리 순위 목록 표
    st.subheader("📊 칼로리 순위 목록 (높은 순)")
    df_display = df_sorted.copy()
    df_display.index = df_display.index + 1
    df_display.index.name = "순위"
    
    st.dataframe(
        df_display[["학교명", "식사구분", "칼로리(kcal)", "메뉴"]],
        use_container_width=True
    )

    # 4. 카드 형태 상세 정보
    st.subheader("📋 학교별 상세 메뉴")
    cols = st.columns(len(SCHOOLS))
    
    for idx, (school_name, _) in enumerate(SCHOOLS.items()):
        school_data = df_sorted[df_sorted["학교명"] == school_name]
        with cols[idx]:
            st.markdown(f"### {school_name}")
            if school_data.empty:
                st.caption("등록된 급식 없음")
            else:
                for _, row in school_data.iterrows():
                    st.metric(
                        label=row["식사구분"],
                        value=f"{row['칼로리(kcal)']} kcal"
                    )
                    st.caption(f"**메뉴**: {row['메뉴']}")
