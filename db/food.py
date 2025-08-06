import os
import sqlite3
import db
import db.session
import src.utils as utils
import requests
import urllib3
from datetime import datetime, timedelta
from dotenv import load_dotenv
from openai import OpenAI
load_dotenv()
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def delete_food(sid: str, fid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info
    
    uid = session_info.data['session_info']['uid']
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # 식품 ID와 유저 ID가 일치하는 식품 정보 삭제
    cursor.execute("DELETE FROM foods WHERE fid = ? AND uid = ?", (fid, uid))
    conn.commit()
    
    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 식품 정보를 찾을 수 없습니다.", result=False)
    
    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="성공적으로 삭제되었습니다.", result=True)

def get_info(sid: str, fid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info

    if not fid:
        return utils.ResultDTO(code=400, message="유효하지 않은 식품 ID입니다.", result=False)
    
    conn = db.get_db_connection()
    cursor = conn.cursor()

    # 유저 ID와 식품 ID가 일치하는 식품 정보 조회
    uid = session_info.data['session_info']['uid']
    cursor.execute("SELECT * FROM foods WHERE fid = ? AND uid = ?", (fid, uid))
    row = cursor.fetchone()
    
    if not row:
        cursor.execute("SELECT * FROM foods WHERE fid = ?", (fid,))
        row = cursor.fetchone()
        if row:
            return utils.ResultDTO(code=401, message="본인의 식품 정보만 조회할 수 있습니다.", result=False)
        
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 식품 정보를 찾을 수 없습니다.", result=False)
    row = dict(row)
    
    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="성공적으로 조회되었습니다.", data={'food_info': row}, result=True)

def get_list_info(sid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    # 잘못된 세션 ID일 경우 실패 처리
    if not session_info.result:
        return session_info
    
    uid = session_info.data['session_info']['uid']
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM foods WHERE uid = ?", (uid,))
    rows = cursor.fetchall()
    
    if not rows:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 식품 정보가 없습니다.", result=False)
    
    food_list = [dict(row) for row in rows]
    
    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="성공적으로 조회되었습니다.", data={'food_list': food_list}, result=True)

def chat_food(sid: str, fid_list: list) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    # 잘못된 세션 ID일 경우 실패 처리
    if not session_info.result:
        return session_info
    
    if not fid_list:
        return utils.ResultDTO(code=400, message="식품 ID 목록이 비어 있습니다.", result=False)
    
    food_info_list = []
    for index, fid in enumerate(fid_list):
        food_info = get_info(sid, fid)
        if not food_info.result:
            food_info.message = f"식품 ID 조회에 실패했습니다: [{index}] {food_info.message}"
            return food_info
        food_info_list.append(food_info.data['food_info'])

    def generate(food_info_list):
        client = OpenAI()
        datetime_now = datetime.now()
        
        prompt = f'''선택된 식품 정보로 레시피 추천을 생성.
        선택된 식품 정보로만 되도록 레시피를 생성하되, 레시피 생성이 어려울 경우 1~2개 정도는 선택된 식품 정보에 없는 식품 추가 가능.
        Markdown 형식이 아닌 일반 plain text로 응답.
        재료는 줄바꿈 리스트(- , - , - ) 형식으로 답해야 함.
        조리 방법은 줄바꿈 리스트(1. 2. 3.) 형식으로 답해야 함.
        현재 시간에 알맞는 음식으로 추천. 현재 한국 시간(24시간제): {datetime_now.strftime('%H:%M')}). 6-10시: 아침음식 추천, 11-14시: 점심음식 추천, 15-17시 간식 추천, 18-21시: 저녁음식 추천, 22-5시: 야식 추천
        재료를 말할 땐 재료를 명확하게 말해야 함(혼합음료 -> 이온음료 등으로 명확하게 기제)
        한 끼에 적합한 양으로 추천(1인분 기준, 2인분 이상은 추가로 기재)
        
        아래의 형식으로 응답. 꺽쇠괄호 안에는 생성해야하는 정보를 뜻함(꺽쇠괄호 내용 출력 금지):
<레시피 추천 격려 문구(가지고 계신 식품을 아래 레시피로 즐겨보세요! 등. 사용자가 가지고 있는 식품을 활용해보라는 문구를 강조)>\n
레시피: <요리 제목>\n
재료: <재료 목록>\n
조리 방법: <조리 방법>\n
<간단한 코멘트>

        선택된 식품 정보:'''
        for food_info in food_info_list:
            prompt += f"\n- {food_info['name']}(용량: {food_info['volume']}, 식품 유형: {food_info['type']})"
        
        stream = client.responses.create(
            model="gpt-4.1-nano",
            input=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            stream=True,
        )
        for event in stream:
            if event.type == 'response.output_text.delta':
                yield event.delta

    return utils.ResultDTO(code=200, message="대화가 성공적으로 생성되었습니다.", data=generate(food_info_list), result=True)

def regi_food_with_barcode(sid:str, barcode:str, food_count:int) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    # 잘못된 세션 ID일 경우 실패 처리
    if not session_info.result:
        return session_info
    
    # 잘못된 바코드 값일 경우 실패 처리
    if not barcode or not utils.is_valid_barcode(barcode):
        return utils.ResultDTO(code=400, message="유효하지 않은 바코드 형식입니다. (12~13자리 숫자)", result=False)
    
    # 잘못된 식품 수량일 경우 실패 처리
    if food_count <= 0 or food_count > 100:
        return utils.ResultDTO(code=400, message="식품 수량은 1 이상 100 이하이어야 합니다.", result=False)
    
    # 식품의 이름, 종류(유탕면, 음료 등), 유통기한 가져오기
    food_name = None
    food_type = None
    food_expiration_date = None
    food_expiration_date_desc = None
    food_image_url = None
    food_volume = None
    try:
        # get Food name, type, expiration date
        foodsafety_api_url = f"http://openapi.foodsafetykorea.go.kr/api/{os.environ['FOODSAFETYKOREA_API_KEY']}/C005/json/1/100/BAR_CD={barcode}"
        response = requests.get(foodsafety_api_url)
        response.raise_for_status()
        response_json = response.json()
        row = response_json['C005']['row'][0]
        food_name = row['PRDLST_NM']
        food_type = row['PRDLST_DCNM']
        food_expiration_date = datetime.now() + timedelta(days=utils.extract_months(row['POG_DAYCNT'])*30)
        food_expiration_date_desc = row['POG_DAYCNT']
        
        retaildb_api_url = f"https://www.retaildb.or.kr/service/product_info/search/{barcode}"
        response = requests.get(retaildb_api_url, verify=False)
        response_json = response.json()
        food_volume = response_json['originVolume']
        food_image_url = response_json['images'][0]
    except:
        return utils.ResultDTO(code=400, message="식품 정보를 찾을 수 없습니다.", result=False)
    
    # DB 작성
    fid = utils.gen_hash(16)
    uid = session_info.data['session_info']['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("INSERT INTO foods (fid, uid, name, type, description, count, volume, image_url, barcode, expiration_date_desc, expiration_date) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (fid, uid, food_name, food_type, food_name, food_count, food_volume, food_image_url, barcode, food_expiration_date_desc, utils.datetime_to_str(food_expiration_date)))
        conn.commit()
        db.close_db_connection(conn)
    except:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=409, message="등록 중 오류가 발생했습니다.", result=False)

    return utils.ResultDTO(code=200, message="식품 등록 성공", data=get_info(sid, fid).data, result=True)