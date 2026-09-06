import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime

# --- 페이지 설정 ---
st.set_page_config(
    page_title="고교 급식 칼로리 나침반",
    page_icon="🥗",
    layout="wide"
)

# --- 기본 설정값 ---
API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "B10"  # 서울특별시교육청 코드

# 대상 학교 정보 (행정표준코드)
SCHOOLS = {
    "성남고등학교": "70101930",
    "당곡고등학교": "7010537",
    "수도여자고등학교": "7010142"
}

# --- 데이터 로드 함수 ---
@st.cache_data(ttl=3600)
def fetch_meal_data(school_code, target_date, api_key="sample"):
    """나이스 API로부터 특정 학교 및 날짜의 급식 데이터를 가져옵니다."""
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
    except Exception as e:
        st.error(f"데이터 수신 중 오류 발생: {e}")
        return []

def parse_calorie(cal_str):
    """칼로리 문자열(예: '650.5 Kcal')에서 숫자만 추출합니다."""
    if not cal_str:
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cal_str)
    return float(match.group(1)) if match else 0.0

def clean_menu_text(menu_str):
    """메뉴 이름의 알레르기 원산지 번호 등 불필요한 특수문자를 정제합니다."""
    if not menu_str:
        return ""
    # <br/> 태그를 줄바꿈으로 변경하고 원산지/알레르기 숫자 제거
    cleaned = menu_str.replace("<br/>", "\n")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    return cleaned.strip()

# --- UI 레이아웃 ---
st.title("🥗 고교 급식 칼로리 비교 & 다이어트 도우미")
st.caption("성남고, 당곡고, 수도여고의 급식 칼로리를 높은 순/낮은 순으로 비교하여 건강한 식단을 계획해보세요.")

# 데이터 조회를 위한 사이드바
st.sidebar.header("🔍 조회 설정")
selected_date = st.sidebar.date_input("조회할 날짜 선택", datetime.now())
formatted_date = selected_date.strftime("%Y%m%m") if hasattr(selected_date, "strftime") else selected_date.replace("-", "")
date_str_formatted = selected_date.strftime("%Y%m%d")

api_key = st.sidebar.text_input("NEIS API Key (미입력 시 sample key 사용)", value="sample")

st.sidebar.markdown("---")
st.sidebar.info("💡 **Tip**: API 샘플 키는 호출 제한이 있을 수 있으므로 나이스 Open API에서 정식 키를 발급받아 사용하는 것을 권장합니다.")

# --- 메인 처리 ---
if st.button("급식 데이터 가져오기", type="primary"):
    all_meals = []

    with st.spinner("학교별 급식 정보를 조회하는 중..."):
        for school_name, school_code in SCHOOLS.items():
            rows = fetch_meal_data(school_code, date_str_formatted, api_key)
            
            for row in rows:
                cal_num = parse_calorie(row.get("CAL_INFO", ""))
                meal_type = row.get("MMEAL_SC_NM", "식사")
                menu = clean_menu_text(row.get("DDISH_NM", ""))
                
                all_meals.append({
                    "학교명": school_name,
                    "식사": meal_type,
                    "칼로리(kcal)": cal_num,
                    "원본 칼로리": row.get("CAL_INFO", "-"),
                    "메뉴": menu,
                    "영양정보": clean_menu_text(row.get("NTR_INFO", "-"))
                })

    if not all_meals:
        st.warning(f"{selected_date.strftime('%Y년 %m월 %d일')}의 급식 정보가 없거나 데이터를 가져올 수 없습니다.")
    else:
        df = pd.DataFrame(all_meals)
        
        # 칼로리 내림차순 정렬 (높은 순 -> 낮은 순)
        df_sorted = df.sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)
        
        st.subheader(f"📅 {selected_date.strftime('%Y-%m-%d')} 급식 칼로리 순위")
        
        # 메트릭 카드로 최고/최저 강조
        col1, col2 = st.columns(2)
        with col1:
            max_meal = df_sorted.iloc[0]
            st.metric(
                label="🔥 최고 칼로리 급식",
                value=f"{max_meal['칼로리(kcal)']} kcal",
                delta=f"{max_meal['학교명']} ({max_meal['식사']})"
            )
        with col2:
            min_meal = df_sorted.iloc[-1]
            st.metric(
                label="🥗 최저 칼로리 급식",
                value=f"{min_meal['칼로리(kcal)']} kcal",
                delta=f"{min_meal['학교명']} ({min_meal['식사']})",
                delta_color="normal"
            )

        st.markdown("---")
        
        # 정렬된 표 출력
        st.dataframe(
            df_sorted[["학교명", "식사", "칼로리(kcal)", "메뉴"]],
            use_container_width=True,
            height=250
        )
        
        # 세부 정보 확인 (선택)
        st.subheader("📌 상세 메뉴 및 영양 정보")
        for idx, row in df_sorted.iterrows():
            with st.expander(f"[{idx+1}위] {row['학교명']} - {row['식사']} ({row['칼로리(kcal)']} kcal)"):
                st.write("**[식단 메뉴]**")
                st.text(row["메뉴"])
                st.write("**[영양 성분 정보]**")
                st.text(row["영양정보"])
