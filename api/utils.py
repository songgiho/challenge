import csv
import os
from django.conf import settings
import pandas as pd

# CSV 파일 경로 (프로젝트 루트에 있다고 가정)
CSV_FILE_PATH = os.path.join(settings.BASE_DIR.parent, '음식만개등급화.csv')

# CSV 파일 로드 (서버 시작 시 한 번만 로드)
try:
    food_data_df = pd.read_csv(CSV_FILE_PATH, encoding='utf-8')
except FileNotFoundError:
    food_data_df = None
    print(f"Error: CSV file not found at {CSV_FILE_PATH}")
except Exception as e:
    food_data_df = None
    print(f"Error loading CSV file: {e}")

def load_food_grades():
    """음식 등급 CSV 파일을 로드하여 딕셔너리로 반환"""
    # 이미 로드된 DataFrame 사용
    if food_data_df is not None:
        food_grades = {}
        for index, row in food_data_df.iterrows():
            food_name = row['음식명'].strip()
            grade = row['kfni_grade'].strip() if 'kfni_grade' in row else '' # kfni_grade 컬럼이 없을 경우 대비
            calories = float(row['에너지(kcal)']) if '에너지(kcal)' in row and row['에너지(kcal)'] else 0
            food_grades[food_name] = {
                'grade': grade,
                'calories': calories,
                'category': row['식품대분류명'] if '식품대분류명' in row else ''
            }
        return food_grades
    return {}

def estimate_mass(food_name, estimated_calories):
    """음식명과 추정 칼로리를 기반으로 질량을 추정"""
    food_grades = load_food_grades()
    
    # 정확한 음식명 매칭
    if food_name in food_grades:
        reference_calories = food_grades[food_name]['calories']
        if reference_calories > 0:
            # 100g 기준으로 질량 추정
            estimated_mass = (estimated_calories / reference_calories) * 100
            return round(estimated_mass, 1)
    
    # 부분 매칭 시도
    for key in food_grades:
        if food_name in key or key in food_name:
            reference_calories = food_grades[key]['calories']
            if reference_calories > 0:
                estimated_mass = (estimated_calories / reference_calories) * 100
                return round(estimated_mass, 1)
    
    # 기본 추정 (일반적인 음식 기준)
    if '밥' in food_name or '쌀' in food_name:
        return round(estimated_calories / 1.2, 1)  # 밥 1.2kcal/g
    elif '고기' in food_name or '육류' in food_name or '돈까스' in food_name:
        return round(estimated_calories / 2.5, 1)  # 고기 2.5kcal/g
    elif '면' in food_name or '국수' in food_name:
        return round(estimated_calories / 1.1, 1)  # 면 1.1kcal/g
    elif '빵' in food_name or '과자' in food_name:
        return round(estimated_calories / 2.8, 1)  # 빵 2.8kcal/g
    else:
        return round(estimated_calories / 2.0, 1)  # 기본 2.0kcal/g

def determine_grade(food_name, calories):
    """음식명과 칼로리를 기반으로 등급 결정"""
    food_grades = load_food_grades()
    
    # 정확한 매칭
    if food_name in food_grades:
        return food_grades[food_name]['grade']
    
    # 부분 매칭
    for key in food_grades:
        if food_name in key or key in food_name:
            return food_grades[key]['grade']
    
    # 칼로리 기반 등급 (기본)
    if calories < 300:
        return 'A'
    elif calories < 600:
        return 'B'
    else:
        return 'C'

def process_multiple_foods(analysis_text):
    """Gemini 분석 결과에서 여러 음식을 추출하고 처리"""
    import json
    import re
    
    try:
        # JSON 배열 형식 파싱 시도
        if analysis_text.strip().startswith('['):
            data = json.loads(analysis_text)
            # 배열이 이미 올바른 형태인지 확인
            if isinstance(data, list):
                # 각 항목이 딕셔너리인지 확인하고 필요한 키가 있는지 검증
                processed_foods = []
                for item in data:
                    if isinstance(item, dict) and '음식명' in item:
                        processed_foods.append(item)
                return processed_foods
            return []
        
        # JSON 객체 형식 파싱 시도
        if analysis_text.strip().startswith('{'):
            data = json.loads(analysis_text)
            if isinstance(data, dict) and '음식명' in data:
                return [data]  # 단일 객체를 배열로 감싸서 반환
            return []
        
        # 여러 음식이 포함된 경우 처리
        foods = []
        
        # 패턴 매칭으로 여러 음식 추출
        food_patterns = [
            r'(\d+\.\s*)?([^,\n]+?)\s*:\s*(\d+)\s*g\s*,\s*(\d+)\s*kcal',
            r'([^,\n]+?)\s*(\d+)\s*g\s*(\d+)\s*kcal',
            r'([^,\n]+?)\s*질량[:\s]*(\d+)\s*칼로리[:\s]*(\d+)',
        ]
        
        for pattern in food_patterns:
            matches = re.findall(pattern, analysis_text, re.IGNORECASE)
            for match in matches:
                if len(match) >= 3:
                    if match[0].isdigit():  # 번호가 있는 경우
                        food_name = match[1].strip()
                        mass = int(match[2])
                        calories = int(match[3])
                    else:
                        food_name = match[0].strip()
                        mass = int(match[1])
                        calories = int(match[2])
                    
                    foods.append({
                        '음식명': food_name,
                        '질량': mass,
                        '칼로리': calories
                    })
        
        if foods:
            return foods
        
        # 파싱 실패 시 빈 배열 반환
        return []
        
    except Exception as e:
        print(f"여러 음식 처리 실패: {e}")
        return []

def calculate_nutrition_score(food_name, calories, mass):
    """영양 점수 계산 (15점 만점)"""
    grade = determine_grade(food_name, calories)
    
    # 등급별 기본 점수
    grade_scores = {'A': 15, 'B': 10, 'C': 5}
    base_score = grade_scores.get(grade, 8)
    
    # 칼로리 보정
    if calories < 300:
        bonus = 3
    elif calories < 600:
        bonus = 1
    else:
        bonus = -2
    
    final_score = max(1, min(15, base_score + bonus))
    return final_score

def generate_ai_feedback(food_name, calories, mass, grade):
    """Gemini LLM을 활용한 개인화된 AI 피드백 생성"""
    import requests
    from django.conf import settings
    
    try:
        # Gemini API 호출
        api_key = settings.GEMINI_API_KEY
        api_url = f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash:generateContent?key={api_key}'
        
        prompt = f"""다음 음식에 대한 건강한 조언을 해주세요:\n\n음식명: {food_name}\n칼로리: {calories}kcal\n질량: {mass}g\n등급: {grade}\n\n다음 형식으로 답해주세요:\n1. 간단한 한 줄 코멘트 (예: \"돈까스는 지방이 높으니 채소를 함께 드세요!\")\n2. 구체적인 조언 (2-3문장)\n3. 대체 음식 추천\n\n친근하고 격려하는 톤으로 답해주세요."""

        response = requests.post(api_url, json={
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ]
        }, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            feedback = response_data['candidates'][0]['content']['parts'][0]['text']
            return feedback.strip()
        else:
            return f"{food_name}의 칼로리는 {calories}kcal입니다. {'건강한 선택입니다!' if calories < 600 else '적당한 칼로리입니다.' if calories < 800 else '칼로리가 높으니 다음 식사는 가볍게 드세요.'}"
    
    except Exception as e:
        print(f"AI 피드백 생성 실패: {e}")
        return f"{food_name}의 칼로리는 {calories}kcal입니다. {'건강한 선택입니다!' if calories < 600 else '적당한 칼로리입니다.' if calories < 800 else '칼로리가 높으니 다음 식사는 가볍게 드세요.'}" 
