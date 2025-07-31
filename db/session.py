import sqlite3
import db
import db.user
import src.utils as utils
import src.email

def get_session_list(sid: str) -> utils.ResultDTO:
    # 세션 ID가 유효한지 확인
    session_info = get_info(sid)
    if not session_info.result:
        return utils.ResultDTO(code=404, message="유효하지 않은 세션 ID입니다.", result=False)
    # 세션이 비활성화된 경우 실패 처리
    session_info = session_info.data['session_info']
    if not session_info['is_active']:
        return utils.ResultDTO(code=401, message="비활성화된 세션입니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_sessions WHERE uid = ? ORDER BY created_at DESC", (session_info['uid'],))
    rows = cursor.fetchall()

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="세션 목록을 성공적으로 조회했습니다.", data={"sessions_info" : [dict(row) for row in rows]}, result=True)

def deactivate_session(sid: str) -> utils.ResultDTO:
    # 세션 ID가 유효한지 확인
    session_info = get_info(sid)
    if not session_info.result:
        return utils.ResultDTO(code=404, message="유효하지 않은 세션 ID입니다.", result=False)
    # 이미 세션이 비활성화된 경우 실패 처리
    session_info = session_info.data['session_info']
    if not session_info['is_active']:
        return utils.ResultDTO(code=400, message="비활성화된 세션입니다.", result=False)

    # 세션 비활성화
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE sid = ?", (sid,))
        conn.commit()
        
        return utils.ResultDTO(code=200, message="로그아웃 되었습니다.", result=True)
    except sqlite3.Error:
        return utils.ResultDTO(code=500, message="로그아웃에 실패했습니다.", result=False)
    finally:
        db.close_db_connection(conn)

def create_session(email: str, password: str, user_agent: str, ip_address: str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="유효하지 않은 이메일 형식입니다.", result=False)
    if not utils.is_valid_password(password):
        return utils.ResultDTO(code=400, message="유효하지 않은 비밀번호 형식입니다.", result=False)

    # 사용자 검증
    uid = db.user.validate_user(email, password)
    if not uid.result:
        return utils.ResultDTO(code=401, message="이메일 또는 비밀번호를 확인하십시오.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    sid = utils.gen_hash(16)
    expires_at = utils.get_future_timestamp(days=31)  # 31일 뒤 세션 만료

    try:
        # 세션 생성
        cursor.execute("INSERT INTO user_sessions (sid, uid, user_agent, ip_address, expires_at) VALUES (?, ?, ?, ?, ?)",
                       (sid, uid.data['uid'], user_agent, ip_address, expires_at))
        conn.commit()
        
        # 최신 날짜 순으로 5개 세션만 유지. 나머지는 is_activate를 0으로 설정
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE uid = ? AND sid NOT IN (SELECT sid FROM user_sessions WHERE uid = ? ORDER BY created_at DESC LIMIT 5)", (uid.data['uid'], uid.data['uid']))
        conn.commit()
        
        # 이메일 알림
        src.email.service.send_session_created_email(email, sid)
        
        return utils.ResultDTO(code=200, message="성공적으로 로그인하였습니다.", data={'sid': sid}, result=True)
    except sqlite3.IntegrityError:
        return utils.ResultDTO(code=409, message="세션이 이미 존재합니다.", result=False)
    finally:
        db.close_db_connection(conn)
        
def get_info(sid: str) -> utils.ResultDTO:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_sessions WHERE sid = ?", (sid,))
    row = cursor.fetchone()

    # 없는 세션 ID인 경우 실패 처리
    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="유효하지 않은 세션 ID입니다.", result=False)

    # 현재 시간이 expires_at을 초과한 경우 실패 처리(is_active도 0으로 설정)
    if utils.get_current_datetime() > utils.str_to_datetime(row['expires_at']):
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE sid = ?", (sid,))
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="세션이 만료되었습니다.", result=False)

    session_info = {
        'sid': row['sid'],
        'uid': row['uid'],
        'user_agent': row['user_agent'],
        'ip_address': row['ip_address'],
        'is_active': row['is_active'],
        'last_accessed': row['last_accessed'],
        'expires_at': row['expires_at'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="세션을 성공적으로 조회했습니다.", data={'session_info': session_info}, result=True)