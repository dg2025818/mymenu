import re
import requests
import pandas as pd

# 1. 설정 및 기본 정보 정의
# 오픈API 인증키가 있는 경우 'sample' 대신 입력하세요.
API_KEY = "sample"  
BASE_URL = "https://open.neis.go.kr/hub/mealServiceDietInfo"

# 서울특별시교육청 코드
OFFICE_CODE = "B10"

# 분석 대상 학교 정보 (행정표준코드)
SCHOOLS = {
    "당곡고등학교": "7010536",
    "수도여자고등학교": "7010082",
    "성남고등학교": "7010081"
}

def fetch_meal_data(office_code, school_code, from_ymd="20260301", to_ymd="20260331"):
    """
    나이스 오픈API에서 해당 학교의 급식 정보를 조회합니다.
    """
    params = {
        "KEY": API_KEY,
        "Type": "json",
        "pIndex": 1,
        "pSize": 100,
        "ATPT_OFCDC_SC_CODE": office_code,
        "SD_SCHUL_CODE": school_code,
        "MLSV_FROM_YMD": from_ymd,
        "MLSV_TO_YMD": to_ymd
    }
    
    try:
        response = requests.get(BASE_URL, params=params)
        data = response.json()
        
        # 정상 응답 확인
        if "mealServiceDietInfo" in data:
            return data["mealServiceDietInfo"][1]["row"]
        else:
            print(f"데이터 없음 또는 에러 발생: {school_code}")
            return []
    except Exception as e:
        print(f"API 요청 오류 ({school_code}): {e}")
        return []

def parse_calorie(cal_str):
    """
    '725.4 Kcal' 문자열에서 숫자(float)만 추출합니다.
    """
    if not cal_str:
        return 0.0
    match = re.search(r"([0-9]+\.?[0-9]*)", str(cal_str))
    if match:
        return float(match.group(1))
    return 0.0

def clean_dish_name(dish_str):
    """
    메뉴명에서 알레르기 유발물질 번호(예: 1.2.5.)나 특수문자를 제거합니다.
    """
    if not dish_str:
        return ""
    # <br/> 태그 변경 및 알레르기 번호 제거
    cleaned = dish_str.replace("<br/>", ", ")
    cleaned = re.sub(r"\d+\.", "", cleaned)
    return cleaned.strip()

# 2. 데이터 수집 및 가공
all_meals = []

for school_name, school_code in SCHOOLS.items():
    rows = fetch_meal_data(OFFICE_CODE, school_code)
    
    for row in rows:
        cal_val = parse_calorie(row.get("CAL_INFO", ""))
        dish_clean = clean_dish_name(row.get("DDISH_NM", ""))
        
        all_meals.append({
            "학교명": row.get("SCHUL_NM", school_name),
            "급식일자": row.get("MLSV_YMD"),
            "식사명": row.get("MMEAL_SC_NM"),
            "칼로리(Kcal)": cal_val,
            "메뉴": dish_clean,
            "영양정보": row.get("NTR_INFO", "")
        })

# 3. 데이터프레임 생성 및 칼로리 내림차순 정렬
df = pd.DataFrame(all_meals)

if not df.empty:
    # 칼로리 기준 내림차순 정렬 (높은 칼로리 -> 낮은 칼로리)
    df_sorted = df.sort_values(by="칼로리(Kcal)", ascending=False).reset_index(drop=True)
    
    print("=" * 60)
    print("🔥 [고칼로리 -> 저칼로리] 급식 순위 TOP 5")
    print("=" * 60)
    for idx, row in df_sorted.head(5).iterrows():
        print(f"[{idx+1}위] {row['학교명']} ({row['급식일자']} {row['식사명']}) - {row['칼로리(Kcal)']} Kcal")
        print(f"   메뉴: {row['메뉴'][:50]}...\n")

    print("=" * 60)
    print("🥗 [다이어트 추천!] 저칼로리 급식 TOP 5")
    print("=" * 60)
    for idx, row in df_sorted.tail(5).iloc[::-1].reset_index(drop=True).iterrows():
        print(f"[{idx+1}위] {row['학교명']} ({row['급식일자']} {row['식사명']}) - {row['칼로리(Kcal)']} Kcal")
        print(f"   메뉴: {row['메뉴'][:50]}...\n")

    print("=" * 60)
    print("🏫 학교별 평균 칼로리 비교")
    print("=" * 60)
    avg_cal = df.groupby("학교명")["칼로리(Kcal)"].mean().reset_index()
    for _, row in avg_cal.iterrows():
        print(f"- {row['학교명']}: 평균 {row['칼로리(Kcal)']:.1f} Kcal")
        
    # 결과를 CSV 파일로 저장 (깃허브 업로드용)
    df_sorted.to_csv("school_meal_calories.csv", index=False, encoding="utf-8-sig")
    print("\n분석 결과가 'school_meal_calories.csv' 파일로 저장되었습니다.")
else:
    print("조회된 급식 데이터가 없습니다.")
