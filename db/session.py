import sqlite3
import db
import db.user
import src.utils as utils
import src.email

def get_session_list(session_id: str) -> list | bool:
    session_info = get_info(session_id)
    if not session_info:
        return False
    if not session_info['is_active']:
        return False
    
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_sessions WHERE uid = ? ORDER BY created_at DESC", (session_info['uid'],))
    rows = cursor.fetchall()

    db.close_db_connection(conn)
    
    return [dict(row) for row in rows] if rows else False

def deactivate_session(session_id: str) -> bool:
    # 세션 ID가 유효한지 확인
    session_info = get_info(session_id)
    if not session_info:
        return False
    
    # 이미 세션이 비활성화된 경우 실패 처리
    if not session_info['is_active']:
        return False
    
    # 세션 비활성화
    conn = db.get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
        conn.commit()
        
        return True
    except sqlite3.Error:
        return False
    finally:
        db.close_db_connection(conn)

def create_session(email: str, password: str, user_agent: str, ip_address: str) -> str | bool:
    if not utils.is_valid_email(email):
        return False
    if not utils.is_valid_password(password):
        return False

    # 사용자 검증
    uid = db.user.validate_user(email, password)
    if not uid:
        return False

    conn = db.get_db_connection()
    cursor = conn.cursor()

    session_id = utils.gen_hash(16)
    expires_at = utils.get_future_timestamp(days=31)  # 31일 뒤 세션 만료

    try:
        # 세션 생성
        cursor.execute("INSERT INTO user_sessions (session_id, uid, user_agent, ip_address, expires_at) VALUES (?, ?, ?, ?, ?)",
                       (session_id, uid, user_agent, ip_address, expires_at))
        conn.commit()
        
        # 최신 날짜 순으로 5개 세션만 유지. 나머지는 is_activate를 0으로 설정
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE uid = ? AND session_id NOT IN (SELECT session_id FROM user_sessions WHERE uid = ? ORDER BY created_at DESC LIMIT 5)", (uid, uid))
        conn.commit()
        
        # 이메일 알림
        src.email.service.send_session_created_email(email, session_id)
        
        return session_id
    except sqlite3.IntegrityError:
        return False
    finally:
        db.close_db_connection(conn)
        
def get_info(session_id: str) -> dict | bool:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM user_sessions WHERE session_id = ?", (session_id,))
    row = cursor.fetchone()

    # 없는 세션 ID인 경우 실패 처리
    if not row:
        db.close_db_connection(conn)
        return False
    
    # 현재 시간이 expires_at을 초과한 경우 실패 처리(is_active도 0으로 설정)
    if utils.get_current_datetime() > utils.str_to_datetime(row['expires_at']):
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE session_id = ?", (session_id,))
        db.close_db_connection(conn)
        return False

    session_info = {
        'session_id': row['session_id'],
        'uid': row['uid'],
        'user_agent': row['user_agent'],
        'ip_address': row['ip_address'],
        'is_active': row['is_active'],
        'last_accessed': row['last_accessed'],
        'expires_at': row['expires_at'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return session_info