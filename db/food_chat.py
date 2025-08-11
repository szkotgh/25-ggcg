import src.utils as utils
import db
import db.session
import db.food
import time
from openai import OpenAI
from datetime import datetime
import threading

class FoodChat:
    gen_chat_queue = []
    create_queue = []
    
    def __init__(self):
        # 대화 생성 스레드 시작
        def chat_generating_thread():
            while True:
                if self.gen_chat_queue:
                    chat_info = self.gen_chat_queue.pop(0)
                    sid = chat_info['sid']
                    fcid = chat_info['fcid']

                    result = generate_chat(sid, fcid)
                    
                    continue
            
                time.sleep(10)

        threading.Thread(target=chat_generating_thread, daemon=True).start()

    def queue_add(self, sid: str, fcid: str):
        self.gen_chat_queue.append({
            'sid': sid,
            'fcid': fcid
        })
        food_chat_config(fcid, status='queued')

foodchat_service = FoodChat()

def get_info(sid: str, fcid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info
    if session_info.data['session_info']['is_active'] == 0:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)
    
    uid = session_info.data['session_info']['uid']
    
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # fcid와 uid가 일치하는 food_chat 정보 조회
    cursor.execute("SELECT * FROM food_chat WHERE fcid = ? AND uid = ?", (fcid, uid))
    row = cursor.fetchone()
    
    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="등록된 대화 정보를 찾을 수 없습니다.", result=False)
    
    row = dict(row)
    
    # food_chat_items에서 해당 fcid에 대한 식품 ID 목록 조회
    cursor.execute("SELECT fid FROM food_chat_items WHERE fcid = ?", (fcid,))
    items = cursor.fetchall()
    
    food_ids = [item['fid'] for item in items]
    
    db.close_db_connection(conn)
    
    return utils.ResultDTO(code=200, message="성공적으로 조회했습니다.", data={'chat_info': row, 'food_ids': food_ids}, result=True)

def create_chat_db(sid: str, fid_list: list) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info
    if session_info.data['session_info']['is_active'] == 0:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)
    uid = session_info.data['session_info']['uid']
    
    if not fid_list:
        return utils.ResultDTO(code=400, message="식품 ID 목록이 비어 있습니다.", result=False)
    if len(fid_list) < 2:
        return utils.ResultDTO(code=400, message="식품 ID 목록은 최소 2개 이상이어야 합니다.", result=False)
    if len(fid_list) > 10:
        return utils.ResultDTO(code=400, message="식품 ID 목록은 최대 10개까지 가능합니다.", result=False)
    
    food_info_list = []
    for index, fid in enumerate(fid_list):
        food_info = db.food.get_info(sid, fid)
        if not food_info.result:
            food_info.message = f"식품 ID 조회에 실패했습니다: [{index}] {food_info.message}"
            return food_info
        # 중복된 식품 ID는 제외
        if any(food['fid'] == fid for food in food_info_list):
            continue
        food_info_list.append(food_info.data['food_info'])

    # 대화 생성
    con = db.get_db_connection()
    cursor = con.cursor()
    ## food_chat 테이블 데이터 삽입
    fcid = utils.gen_hash(16)
    cursor.execute('''INSERT INTO food_chat (fcid, uid) VALUES (?, ?)''', (fcid, uid))
    con.commit()
    for food_info in food_info_list:
        cursor.execute('''INSERT INTO food_chat_items (fcid, fid) VALUES (?, ?)''', (fcid, food_info['fid']))
    con.commit()
    
    db.close_db_connection(con)
    
    # add to queue
    foodchat_service.queue_add(sid, fcid)
    
    return utils.ResultDTO(code=200, message="대화 정보가 성공적으로 생성되었습니다.", data=get_info(sid, fcid).data, result=True)

def food_chat_config(fcid: str, status: str = None, response: str = None, usage_input_tokens: int = None, usage_output_tokens: int = None) -> utils.ResultDTO:
    # None 값이 아닌 경우에만 업데이트
    updates = []
    params = []
    if status is not None:
        updates.append("status = ?")
        params.append(status)
    if response is not None:
        updates.append("response = ?")
        params.append(response)
    if usage_input_tokens is not None:
        updates.append("usage_input_token = ?")
        params.append(usage_input_tokens)
    if usage_output_tokens is not None:
        updates.append("usage_output_token = ?")
        params.append(usage_output_tokens)
    
    if not updates:
        return utils.ResultDTO(code=400, message="업데이트할 필드가 없습니다.", result=False)
    
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute(f"UPDATE food_chat SET {', '.join(updates)}, updated_at = CURRENT_TIMESTAMP WHERE fcid = ?", [*params, fcid])
    conn.commit()
    db.close_db_connection(conn)

    return utils.ResultDTO(code=200, message="설정이 성공적으로 업데이트되었습니다.", result=True)

def generate_chat(sid: str, fcid: str) -> utils.ResultDTO:
    session_info = db.session.get_info(sid)
    if not session_info.result:
        return session_info
    if session_info.data['session_info']['is_active'] == 0:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)
    uid = session_info.data['session_info']['uid']
    
    food_chat_info = get_info(sid, fcid)
    if not food_chat_info.result:
        return food_chat_info
    
    chat_info = food_chat_info.data['chat_info']
    if chat_info['status'] == 'creating':
        return utils.ResultDTO(code=400, message="생성 중인 대화입니다.", result=False)
    elif chat_info['status'] == 'completed':
        return utils.ResultDTO(code=400, message="이미 완료된 대화입니다.", result=False)
    elif chat_info['status'] == 'failed':
        return utils.ResultDTO(code=400, message="실패한 대화입니다.", result=False)
    
    food_info_list = []
    for fid in food_chat_info.data['food_ids']:
        food_info = db.food.get_info(sid, fid)
        food_info_list.append(food_info.data['food_info'])
    
    try:
        food_chat_config(fcid, status='creating')
        
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
        
        response = client.responses.create(
            model="gpt-4.1-nano",
            input=[
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
        )
        
        output_text = response.output_text
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        food_chat_config(fcid, status='completed', response=output_text, usage_input_tokens=input_tokens, usage_output_tokens=output_tokens)
        
        return utils.ResultDTO(code=200, message="대화가 성공적으로 생성되었습니다.", data=get_info(sid, fcid).data, result=True)
    except Exception as e:
        food_chat_config(fcid, status='failed') 
        return utils.ResultDTO(code=500, message=f"대화 생성 중 오류가 발생했습니다: {str(e)}", result=False)