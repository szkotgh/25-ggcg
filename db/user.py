import sqlite3
import db
import db.session
import src.utils as utils
import src.email as email

def set_profile_url(session_id: str, profile_url: str) -> bool:
    # Validate session ID
    session_info = db.session.get_info(session_id)
    if not session_info:
        return False
    if not session_info['is_active']:
        return False
    
    uid = session_info['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET profile_url = ? WHERE uid = ?", (profile_url, uid))
    conn.commit()
    
    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return False
    
    db.close_db_connection(conn)
    return True

def validate_user(email: str, password: str) -> str | bool:
    if not utils.is_valid_email(email):
        return False
    if not utils.is_valid_password(password):
        return False

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()

    if not row or row['password'] != utils.str_to_hash(password + row['salt']):
        db.close_db_connection(conn)
        return False

    db.close_db_connection(conn)
    return row['uid']

def get_info(uid: str) -> dict | bool:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    row = cursor.fetchone()

    if not row:
        db.close_db_connection(conn)
        return False

    user_info = {
        'uid': row['uid'],
        'email': row['email'],
        'name': row['name'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return user_info

def create_user(email:str, password:str, name:str) -> bool:
    if not utils.is_valid_email(email):
        return False
    if not utils.is_valid_password(password):
        return False
    if not utils.is_valid_username(name):
        return False

    salt = utils.gen_hash(16)
    hashed_password = utils.str_to_hash(password + salt)

    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Check Email
    ## If email already exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        db.close_db_connection(conn)
        return False
    
    ## If email verification is not done
    cursor.execute("SELECT is_verified FROM email_verification WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row or not row[0]:
        db.close_db_connection(conn)
        return False

    try:
        cursor.execute("INSERT INTO users (uid, email, password, salt, name) VALUES (?, ?, ?, ?, ?)",
                       (utils.gen_hash(16), email, hashed_password, salt, name))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        db.close_db_connection(conn)

# 이메일 인증 생성
def send_email_verify_code(user_email: str) -> bool:
    verification_code = utils.gen_number(6)
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT created_at, is_verified FROM email_verification WHERE email = ?", (user_email,))
    row = cursor.fetchone()
    # 만약 이메일이 이미 존재한다면, 기존 레코드를 업데이트(create_at이 3분이 지났을 경우 재설정 가능)
    if row:
        created_at, is_verified = row
        
        # 이미 인증된 이메일이면 실패 처리
        if is_verified:
            db.close_db_connection(conn)
            return False
        # 만약 created_at이 3분이 지났다면, 새로운 인증 코드를 생성하고 이메일을 재전송
        if utils.is_minutes_passed(created_at, 3):
            cursor.execute("UPDATE email_verification SET verification_code = ?, is_verified = 0, try_count = 0, updated_at = (datetime('now', '+9 hours')), created_at = (datetime('now', '+9 hours')) WHERE email = ?", (verification_code, user_email))
            conn.commit()
            db.close_db_connection(conn)
            email.service.send_verification_code_email(user_email, verification_code)
            return True
        # 만약 created_at이 3분이 지나지 않았다면, 인증 코드를 재전송하지 않고 실패 처리
        else:
            db.close_db_connection(conn)
            return False
        
    # 만약 이메일이 존재하지 않는다면, 새로운 레코드를 생성
    else:
        cursor.execute("INSERT INTO email_verification (email, verification_code) VALUES (?, ?)", (user_email, verification_code))
        conn.commit()
        db.close_db_connection(conn)
        email.service.send_verification_code_email(user_email, verification_code)
        return True

# 이메일 인증코드 확인
def verify_code(user_email: str, verification_code: str) -> bool:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT verification_code, is_verified, try_count, created_at FROM email_verification WHERE email = ?", (user_email,))
    row = cursor.fetchone()

    if row:
        stored_code, is_verified, try_count, created_at = row

        # 이미 인증된 이메일이면 실패 처리
        if is_verified:
            db.close_db_connection(conn)
            return False
        # try_count 증가 updated_at 갱신
        cursor.execute("UPDATE email_verification SET try_count = try_count + 1, updated_at = (datetime('now', '+9 hours')) WHERE email = ?", (user_email,))
        conn.commit()
        # created_at이 3분이 지나면 실패 처리
        if utils.is_minutes_passed(created_at, 3):
            db.close_db_connection(conn)
            return False
        # try_count가 5 이상이면 실패 처리
        if try_count > 5:
            db.close_db_connection(conn)
            return False
        
        # 인증 코드가 일치하지 않으면 실패 처리
        if not is_verified and stored_code == verification_code:
            cursor.execute("UPDATE email_verification SET is_verified = 1 WHERE email = ?", (user_email,))
            conn.commit()
            db.close_db_connection(conn)
            return True

    db.close_db_connection(conn)
    return False