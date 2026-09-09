import streamlit as st
import requests
import pandas as pd
import re
from datetime import date

# --- 페이지 설정 ---
st.set_page_config(
    page_title="고교 급식 칼로리 정밀 비교 분석기",
    page_icon="🥗",
    layout="wide"
)

# --- Secrets API 키 로드 ---
API_KEY = st.secrets.get("NEIS_API_KEY", "sample")

API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "B10"  # 서울특별시교육청

SCHOOLS = {
    "성남고등학교": "70101930",
    "당곡고등학교": "7010537",
    "수도여자고등학교": "7010142"
}

# --- API 호출 및 디버깅 함수 ---
@st.cache_data(ttl=3600)
def fetch_meal_data_with_debug(school_code, target_date, api_key):
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
        
        # 1. NEIS API 에러 메시지 검증
        if "RESULT" in data:
            code = data["RESULT"].get("CODE")
            msg = data["RESULT"].get("MESSAGE")
            return [], f"API 응답 메세지: [{code}] {msg}"
            
        # 2. 정상 응답 처리
        if "mealServiceDietInfo" in data:
            rows = data["mealServiceDietInfo"][1].get("row", [])
            return rows, "성공"
            
        return [], "응답 데이터 구조 없음"
        
    except Exception as e:
        return [], f"통신 에러: {str(e)}"

def parse_calorie(cal_str):
    if not cal_str or not isinstance(cal_str, str):
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cal_str)
    return float(match.group(1)) if match else 0.0

def clean_menu_text(menu_str):
    if not menu_str or not isinstance(menu_str, str):
        return "메뉴 정보 없음"
    cleaned = menu_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    return cleaned.strip(", ")

# --- 메인 UI ---
st.title("🥗 고교 급식 칼로리 정밀 비교 분석기")

# 사이드바 API 상태 표시
st.sidebar.header("⚙️ API 상태")
if "NEIS_API_KEY" in st.secrets:
    st.sidebar.success("🔒 Secrets API Key 사용 중")
else:
    st.sidebar.warning("⚠️ sample 키 사용 중 (정밀 조회가 안될 수 있음)")

selected_date = st.date_input(
    "📅 날짜 선택",
    value=date(2026, 9, 7),
    min_value=date(2025, 9, 1),
    max_value=date(2026, 9, 30)
)
date_str = selected_date.strftime("%Y%m%d")

today_meals = []
debug_logs = {}

with st.spinner("급식 정보 데이터 요청 중..."):
    for school_name, school_code in SCHOOLS.items():
        rows, debug_msg = fetch_meal_data_with_debug(school_code, date_str, API_KEY)
        debug_logs[school_name] = debug_msg
        
        for row in rows:
            today_meals.append({
                "학교명": school_name,
                "식사구분": row.get("MMEAL_SC_NM", "중식"),
                "칼로리(kcal)": parse_calorie(row.get("CAL_INFO", "")),
                "메뉴": clean_menu_text(row.get("DDISH_NM", ""))
            })

# --- 결과 출력 ---
if not today_meals:
    st.error(f"🚨 **{selected_date.strftime('%Y년 %m월 %d일')}** 급식 정보를 불러오지 못했습니다.")
    
    st.subheader("🔍 디버그 리포트 (데이터 미등록 원인)")
    for sch_name, log in debug_logs.items():
        st.write(f"- **{sch_name}**: `{log}`")
        
    st.info("💡 **해결 팁**: 나이스 Open API 공식 홈페이지에서 발급받은 실제 API KEY를 Streamlit Secrets에 입력해보세요.")
else:
    df_sorted = pd.DataFrame(today_meals).sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)
    
    # 성남고 강조
    sn_df = df_sorted[df_sorted["학교명"] == "성남고등학교"]
    st.subheader("🏫 성남고등학교 급식 현황")
    if not sn_df.empty:
        for _, row in sn_df.iterrows():
            st.success(f"🍱 **[성남고 {row['식사구분']}]** — **{row['칼로리(kcal)']} kcal**\n\n👉 **메뉴**: {row['메뉴']}")
    else:
        st.warning("성남고등학교 데이터가 등록되어 있지 않습니다.")

    # 전체 데이터 표
    st.subheader("📊 전체 급식 순위")
    st.dataframe(df_sorted[["학교명", "식사구분", "칼로리(kcal)", "메뉴"]], use_container_width=True)
