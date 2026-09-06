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
        return "메뉴 정보 없음"
    # <br/> 태그 정제 및 알레르기 안내 숫자 제거
    cleaned = menu_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    # 연속된 공백 및 쉼표 정돈
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    return cleaned.strip(", ")


# --- 메인 화면 레이아웃 ---
st.title("🥗 고교 급식 메뉴 & 칼로리 순위")
st.write("날짜를 선택하면 성남고, 당곡고, 수도여고의 메뉴와 칼로리를 자동으로 비교하여 **칼로리가 높은 순**으로 보여줍니다.")

# 날짜 선택기 (기본값: 오늘)
selected_date = st.date_input("📅 날짜 선택", datetime.now())
date_str_formatted = selected_date.strftime("%Y%m%d")

# API Key 입력 (필요 시 사이드바에서 수정 가능)
with st.sidebar:
    st.header("⚙️ 설정")
    api_key = st.text_input("NEIS API Key (선택)", value="sample")
    st.caption("※ 기본 sample 키로도 작동하지만, 안정적인 요청을 위해 정식 키 사용을 권장합니다.")

# --- 데이터 수집 및 파싱 ---
all_meals = []

with st.spinner("급식 정보를 조회하고 있습니다..."):
    for school_name, school_code in SCHOOLS.items():
        rows = fetch_meal_data(school_code, date_str_formatted, api_key)
        
        for row in rows:
            cal_num = parse_calorie(row.get("CAL_INFO", ""))
            meal_type = row.get("MMEAL_SC_NM", "식사")
            menu = clean_menu_text(row.get("DDISH_NM", ""))
            
            all_meals.append({
                "학교명": school_name,
                "식사 구분": meal_type,
                "칼로리(kcal)": cal_num,
                "메뉴 요약": menu,
                "영양 정보": clean_menu_text(row.get("NTR_INFO", ""))
            })

# --- 결과 출력 ---
st.markdown("---")

if not all_meals:
    st.info(f"💡 **{selected_date.strftime('%Y년 %m월 %d일')}**은 급식 정보가 없거나 주말/휴일입니다.")
else:
    # 칼로리 내림차순 정렬 (높은 순 -> 낮은 순)
    df = pd.DataFrame(all_meals)
    df_sorted = df.sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)

    # 1. 최고 칼로리 강조 카드
    max_meal = df_sorted.iloc[0]
    st.subheader("🔥 오늘 가장 칼로리가 높은 급식")
    
    st.warning(
        f"**1위: {max_meal['학교명']} ({max_meal['식사 구분']})** — **{max_meal['칼로리(kcal)']} kcal**\n\n"
        f"🍱 **메뉴**: {max_meal['메뉴 요약']}"
    )

    # 2. 전체 칼로리 순위 목록
    st.subheader(f"📊 칼로리 순위 목록 (높은 순)")
    
    # 순위 컬럼 추가
    df_sorted.index = df_sorted.index + 1
    df_sorted.index.name = "순위"

    # 칼로리 높은 순 테이블 표시
    st.dataframe(
        df_sorted[["학교명", "식사 구분", "칼로리(kcal)", "메뉴 요약"]],
        use_container_width=True
    )

    # 3. 학교별 메뉴 세부 보기
    st.subheader("📋 학교별 세부 메뉴")
    cols = st.columns(len(SCHOOLS))
    
    for idx, (school_name, _) in enumerate(SCHOOLS.items()):
        school_data = df[df["학교명"] == school_name]
        with cols[idx]:
            st.markdown(f"### {school_name}")
            if school_data.empty:
                st.write("급식 없음")
            else:
                for _, row in school_data.iterrows():
                    st.metric(
                        label=f"{row['식사 구분']}",
                        value=f"{row['칼로리(kcal)']} kcal"
                    )
                    st.caption(row["메뉴 요약"])
