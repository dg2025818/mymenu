import streamlit as st
import requests
import pandas as pd
import re
from datetime import datetime, date

st.set_page_config(
    page_title="고교 급식 칼로리 & 메뉴 조회 (2021~2026)",
    page_icon="🥗",
    layout="wide"
)

API_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"
OFFICE_CODE = "B10"  # 서울특별시교육청

SCHOOLS = {
    "성남고등학교": "70101930",
    "당곡고등학교": "7010537",
    "수도여자고등학교": "7010142"
}

def parse_calorie(cal_str):
    if not cal_str:
        return 0.0
    match = re.search(r"([0-9]+(?:\.[0-9]+)?)", cal_str)
    return float(match.group(1)) if match else 0.0

def clean_menu_text(menu_str):
    if not menu_str:
        return "-"
    cleaned = menu_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    cleaned = re.sub(r"\s*,\s*", ", ", cleaned)
    return cleaned.strip(", ")

@st.cache_data(ttl=3600)
def fetch_period_meal_data(school_code, start_ymd, end_ymd, api_key="sample"):
    """시작일부터 종료일까지 페이지네이션을 처리하며 모든 데이터를 수집합니다."""
    all_rows = []
    p_index = 1
    
    while True:
        params = {
            "KEY": api_key,
            "Type": "json",
            "pIndex": p_index,
            "pSize": 100,  # 1회 최대 조회 수
            "ATPT_OFCDC_SC_CODE": OFFICE_CODE,
            "SD_SCHUL_CODE": school_code,
            "MLSV_FROM_YMD": start_ymd,
            "MLSV_TO_YMD": end_ymd
        }
        
        try:
            response = requests.get(API_URL, params=params, timeout=10)
            data = response.json()
            
            if "mealServiceDietInfo" in data:
                rows = data["mealServiceDietInfo"][1]["row"]
                all_rows.extend(rows)
                # 가져온 데이터가 100개 미만이면 마지막 페이지임
                if len(rows) < 100:
                    break
                p_index += 1
            else:
                break
        except Exception:
            break
            
    return all_rows

st.title("🥗 2021년~2026년 9월 고교 급식 메뉴 & 칼로리")
st.write("조회하고자 하는 **기간(시작일 ~ 종료일)**을 설정하면 2021년부터 2026년 9월까지의 데이터를 수집하여 칼로리 순으로 정렬합니다.")

# 기간 선택 UI
col_start, col_end = st.columns(2)
with col_start:
    start_date = st.date_input("시작일", date(2021, 1, 1), min_value=date(2021, 1, 1), max_value=date(2026, 9, 30))
with col_end:
    end_date = st.date_input("종료일", date(2026, 9, 30), min_value=date(2021, 1, 1), max_value=date(2026, 9, 30))

api_key = st.sidebar.text_input("NEIS API Key", value="sample")

if st.button("급식 데이터 수집 및 조회", type="primary"):
    start_ymd = start_date.strftime("%Y%m%d")
    end_ymd = end_date.strftime("%Y%m%d")
    
    parsed_meals = []
    
    with st.spinner("NEIS API에서 장기 급식 데이터를 수집 중입니다..."):
        for school_name, school_code in SCHOOLS.items():
            rows = fetch_period_meal_data(school_code, start_ymd, end_ymd, api_key)
            
            for row in rows:
                parsed_meals.append({
                    "급식일자": row.get("MLSV_YMD", ""),
                    "학교명": school_name,
                    "식사 구분": row.get("MMEAL_SC_NM", "식사"),
                    "칼로리(kcal)": parse_calorie(row.get("CAL_INFO", "")),
                    "메뉴 요약": clean_menu_text(row.get("DDISH_NM", ""))
                })

    if not parsed_meals:
        st.error("선택한 기간 동안 수집된 급식 데이터가 없습니다.")
    else:
        df = pd.DataFrame(parsed_meals)
        # 칼로리 내림차순 정렬 (높은 순 -> 낮은 순)
        df_sorted = df.sort_values(by="칼로리(kcal)", ascending=False).reset_index(drop=True)
        
        st.success(f"총 {len(df_sorted)}건의 급식 정보가 조회되었습니다.")
        
        # 칼로리 상위 항목 정렬 표
        st.subheader("🔥 칼로리 높은 순 정렬")
        st.dataframe(df_sorted, use_container_width=True)
        
        # 엑셀/CSV 다운로드 기능 제공
        csv = df_sorted.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 조회된 급식 데이터 CSV 다운로드",
            data=csv,
            file_name=f"급식데이터_{start_ymd}_{end_ymd}.csv",
            mime="text/csv"
        )
