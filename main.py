import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime

# --- 페이지 기본 설정 ---
st.set_page_config(
    page_title="고교 급식 칼로리 나침반",
    page_icon="🥗",
    layout="wide"
)

# --- 기본 상수 정의 ---
API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "B10"  # 서울특별시교육청 코드

# 대상 학교 목록 (학교명: 행정표준코드)
SCHOOLS = {
    "성남고등학교": "70101930",
    "당곡고등학교": "7010537",
    "수도여자고등학교": "7010142"
}

# --- 데이터 전처리 및 로드 함수 ---
@st.cache_data(ttl=3600)
def fetch_meal_data(school_code, target_date, api_key="sample"):
    """나이스 API로부터 지정된 학교 및 날짜의 급식 정보를 수집합니다."""
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
    """칼로리 문자열에서 숫자(float)만 추출합니다."""
    if not cal_str:
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cal_str)
    return float(match.group(1)) if match else 0.0

def clean_menu_text(menu_str):
    """메뉴 텍스트의 알레르기 원산지 번호 표기를 제거하고 정돈합니다."""
    if not menu_str:
        return "-"
    cleaned = menu_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    return cleaned.strip(", ")

# --- 메인 화면 레이아웃 ---
st.title("🥗 고교 급식 메뉴 & 칼로리 순위")
st.write("날짜를 선택하면 성남고, 당곡고, 수도여고의 메뉴와 칼로리를 **칼로리가 높은 순**으로 비교합니다.")

# 날짜 선택기 (주말, 휴일 등 모든 날짜 선택 가능)
selected_date = st.date_input("📅 날짜 선택", datetime.now())
date_str_formatted = selected_date.strftime("%Y%m%d")

# 사이드바 설정
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("NEIS API Key (선택)", value="sample")
    st.caption("※ 기본 sample 키 사용 시 요청 제한이 발생할 수 있습니다.")

# --- 데이터 수집 ---
all_meals = []
school_meal_status = {}  # 학교별 급식 유무 상태 저장

with st.spinner("급식 정보를 조회하고 있습니다..."):
    for school_name, school_code in SCHOOLS.items():
        rows = fetch_meal_data(school_code, date_str_formatted, api_key)
        
        if rows:
            school_meal_status[school_name] = True
            for row in rows:
                cal_num = parse_calorie(row.get("CAL_INFO", ""))
                meal_type = row.get("MMEAL_SC_NM", "식사")
                menu = clean_menu_text(row.get("DDISH_NM", ""))
                
                all_meals.append({
                    "학교명": school_name,
                    "식사 구분": meal_type,
                    "칼로리(kcal)": cal_num,
                    "메뉴 요약": menu
                })
        else:
            school_meal_status[school_name] = False

st.markdown("---")

# --- 결과 출력 ---
# 1. 3개 학교 모두 급식이 없는 경우
if not all_meals:
    st.warning(
        f"🚨 **{selected_date.strftime('%Y년 %m월 %d일')}**은 대상 학교(성남고, 당곡고, 수도여고) 모두 **급식이 없는 날**입니다. "
        f"(주말, 공휴일, 재량휴업일, 방학 등)"
    )

# 2. 일부 또는 전체 학교에 급식이 있는 경우
else:
    df = pd.DataFrame(all_meals)
    df_sorted = df.sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)

    # 최고 칼로리 급식 강조
    max_meal = df_sorted.iloc[0]
    st.subheader("🔥 선택일 최고 칼로리 급식")
    st.warning(
        f"**1위: {max_meal['학교명']} ({max_meal['식사 구분']})** — **{max_meal['칼로리(kcal)']} kcal**\n\n"
        f"🍱 **메뉴**: {max_meal['메뉴 요약']}"
    )

    # 전체 순위 테이블
    st.subheader("📊 칼로리 순위 목록 (높은 순)")
    df_display = df_sorted.copy()
    df_display.index = df_display.index + 1
    df_display.index.name = "순위"
    
    st.dataframe(
        df_display[["학교명", "식사 구분", "칼로리(kcal)", "메뉴 요약"]],
        use_container_width=True
    )

st.markdown("---")

# 3. 학교별 상태 및 상세 메뉴 카드
st.subheader("📋 학교별 급식 현황")
cols = st.columns(len(SCHOOLS))

for idx, (school_name, _) in enumerate(SCHOOLS.items()):
    with cols[idx]:
        st.markdown(f"### {school_name}")
        
        if school_meal_status.get(school_name, False):
            school_data = [m for m in all_meals if m["학교명"] == school_name]
            for row in school_data:
                st.metric(
                    label=f"{row['식사 구분']}",
                    value=f"{row['칼로리(kcal)']} kcal"
                )
                st.caption(row["메뉴 요약"])
        else:
            # 급식이 없는 학교는 사유 안내
            st.error("❌ **급식 없음**")
            st.caption("해당 날짜에는 급식운영 정보가 존재하지 않습니다.")
