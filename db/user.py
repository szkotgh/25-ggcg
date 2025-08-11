import sqlite3
import db
import db.session
import src.utils as utils
import src.email

def set_profile_url(session_id: str, profile_url: str) -> utils.ResultDTO:
    # Validate session ID
    session_info = db.session.get_info(session_id)
    if not session_info:
        return utils.ResultDTO(code=405, message="Invalid session ID", result=False)
    if not session_info['is_active']:
        return utils.ResultDTO(code=401, message="Inactive session ID", result=False)

    uid = session_info['uid']
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("UPDATE users SET profile_url = ? WHERE uid = ?", (profile_url, uid))
    conn.commit()
    
    if cursor.rowcount == 0:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="Failed to update profile URL", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="Profile URL updated successfully", result=True)

def validate_user(email: str, password: str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="유효하지 않은 이메일 형식입니다.", result=False)
    if not password:
        return utils.ResultDTO(code=400, message="비밀번호가 필요합니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()

    if not row or row['password'] != utils.str_to_hash(password + row['salt']):
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="이메일 또는 비밀번호를 확인하십시오.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="인증에 성공했습니다.", data={'uid': row['uid']}, result=True)

def validate_user_by_uid(uid: str, password: str) -> utils.ResultDTO:
    if not uid:
        return utils.ResultDTO(code=400, message="UID가 필요합니다.", result=False)
    if not password:
        return utils.ResultDTO(code=400, message="비밀번호가 필요합니다.", result=False)

    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    row = cursor.fetchone()

    if not row or row['password'] != utils.str_to_hash(password + row['salt']):
        db.close_db_connection(conn)
        return utils.ResultDTO(code=401, message="UID 또는 비밀번호를 확인하십시오.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="인증에 성공했습니다.", data={'uid': row['uid']}, result=True)

def get_info(uid: str) -> utils.ResultDTO:
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE uid = ?", (uid,))
    row = cursor.fetchone()

    if not row:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=404, message="유저를 찾을 수 없습니다.", result=False)

    user_info = {
        'uid': row['uid'],
        'email': row['email'],
        'name': row['name'],
        'profile_url': row['profile_url'],
        'created_at': row['created_at']
    }

    db.close_db_connection(conn)
    return utils.ResultDTO(code=200, message="유저 정보를 성공적으로 조회했습니다.", data={'user_info': user_info}, result=True)

def create_user(email:str, password:str, name:str) -> utils.ResultDTO:
    if not utils.is_valid_email(email):
        return utils.ResultDTO(code=400, message="이메일이 올바르지 않습니다.", result=False)
    if not utils.is_valid_password(password):
        return utils.ResultDTO(code=400, message="비밀번호 형식이 올바르지 않습니다. (영문, 숫자, 기호 8~256자)", result=False)
    if not utils.is_valid_username(name):
        return utils.ResultDTO(code=400, message="올바르지 않은 이름입니다. (한글, 영어 1~20자)", result=False)

    salt = utils.gen_hash(16)
    hashed_password = utils.str_to_hash(password + salt)

    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    # Check Email
    ## If email already exists
    cursor.execute("SELECT email FROM users WHERE email = ?", (email,))
    if cursor.fetchone():
        db.close_db_connection(conn)
        return utils.ResultDTO(code=409, message="이미 가입된 이메일입니다.", result=False)

    ## If email verification is not done
    cursor.execute("SELECT is_verified FROM email_verification WHERE email = ?", (email,))
    row = cursor.fetchone()
    if not row or not row[0]:
        db.close_db_connection(conn)
        return utils.ResultDTO(code=400, message="이메일 인증이 완료되지 않았습니다.", result=False)

    try:
        uid = utils.gen_hash(16)
        cursor.execute("INSERT INTO users (uid, email, password, salt, name) VALUES (?, ?, ?, ?, ?)",
                       (uid, email, hashed_password, salt, name))
        conn.commit()
        src.email.service.send_welcome_email(email, get_info(uid))
        return utils.ResultDTO(code=200, message="성공적으로 가입되었습니다.", result=True)
    except sqlite3.IntegrityError:
        return utils.ResultDTO(code=409, message="이미 가입된 이메일입니다.", result=False)
    finally:
        db.close_db_connection(conn)

def delete_user(email: str, password: str) -> utils.ResultDTO:
    # 사용자 인증
    validate_info = validate_user(email, password)
    if not validate_info.result:
        return validate_info

    uid = validate_info.data['uid']
    user_info = get_info(uid)
    
    # 관련 정보 모두 삭제. 세션 정보는 uid로 조회 후 모두 비활성화 처리
    conn = db.get_db_connection()
    cursor = conn.cursor()

    try:
        # Delete user sessions
        cursor.execute("UPDATE user_sessions SET is_active = 0 WHERE uid = ?", (uid,))
        
        # Delete user foods
        cursor.execute("DELETE FROM foods WHERE uid = ?", (uid,))
        
        # Delete user
        cursor.execute("DELETE FROM users WHERE uid = ?", (uid,))
        
        conn.commit()
        
        src.email.service.send_deleted_account_email(email, user_info)
        
        return utils.ResultDTO(code=200, message="탈퇴가 완료되었습니다.\n이용해주셔서 감사합니다.", result=True)
    except sqlite3.Error as e:
        return utils.ResultDTO(code=500, message=f"탈퇴에 실패했습니다: {str(e)}", result=False)
    finally:
        db.close_db_connection(conn)

# 이메일 인증 생성
def send_email_verify_code(user_email: str) -> utils.ResultDTO:
    verification_code = utils.gen_number(6)
    conn = db.get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT created_at, is_verified FROM email_verification WHERE email = ?", (user_email,))
    row = cursor.fetchone()
    
    # 만약 이메일이 이미 존재한다면, 기존 레코드를 업데이트(create_at이 3분이 지났을 경우 재설정 가능)
    if row:
        created_at, is_verified = row
        
        # 이미 가입된 이메일이라면 실패 처리
        cursor.execute("SELECT email FROM users WHERE email = ?", (user_email,))
        if cursor.fetchone():
            db.close_db_connection(conn)
            return utils.ResultDTO(code=409, message="이미 가입된 이메일입니다. 다른 이메일을 사용하십시오.", result=False)
        # 만약 created_at이 1분이 지났다면, 새로운 인증 코드를 생성하고 이메일을 재전송
        if utils.is_minutes_passed(created_at, 1):
            cursor.execute("UPDATE email_verification SET verification_code = ?, is_verified = 0, try_count = 0, updated_at = (datetime('now', '+9 hours')), created_at = (datetime('now', '+9 hours')) WHERE email = ?", (verification_code, user_email))
            conn.commit()
            db.close_db_connection(conn)
            src.email.service.send_verification_code_email(user_email, verification_code)
            return utils.ResultDTO(code=200, message=f"{user_email}으로 인증 코드가 전송되었습니다.", result=True)
        # 만약 created_at이 1분이 지나지 않았다면, 인증 코드를 재전송하지 않고 실패 처리
        else:
            created_at_datetime = utils.str_to_datetime(created_at)
            now = utils.get_current_datetime()
            diff_datetime = created_at_datetime + utils.timedelta(minutes=1) - now
            total_seconds = max(0, int(diff_datetime.total_seconds()))
            diff_str = f"{total_seconds // 60}:{total_seconds % 60:02d}"

            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message=f"잠시 후 다시 시도하세요. (남은 시간: {diff_str})", result=False)

    # 만약 이메일이 존재하지 않는다면, 새로운 레코드를 생성
    else:
        cursor.execute("INSERT INTO email_verification (email, verification_code) VALUES (?, ?)", (user_email, verification_code))
        conn.commit()
        db.close_db_connection(conn)
        src.email.service.send_verification_code_email(user_email, verification_code)
        return utils.ResultDTO(code=200, message=f"{user_email}으로 인증 코드가 전송되었습니다.", result=True)

# 이메일 인증코드 확인
def verify_code(user_email: str, verification_code: str) -> utils.ResultDTO:
    if not utils.is_valid_email(user_email):
        return utils.ResultDTO(code=400, message="이메일 형식이 올바르지 않습니다.", result=False)
    if not verification_code:
        return utils.ResultDTO(code=400, message="인증코드가 필요합니다.", result=False)
    
    conn = db.get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT verification_code, is_verified, try_count, created_at FROM email_verification WHERE email = ?", (user_email,))
    row = cursor.fetchone()

    if row:
        stored_code, is_verified, try_count, created_at = row

        # 이미 인증된 이메일이면 실패 처리
        if is_verified:
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message="이미 인증된 이메일입니다.", result=False)
        # try_count 증가 updated_at 갱신
        cursor.execute("UPDATE email_verification SET try_count = try_count + 1, updated_at = (datetime('now', '+9 hours')) WHERE email = ?", (user_email,))
        conn.commit()
        # created_at이 3분이 지나면 실패 처리
        if utils.is_minutes_passed(created_at, 3):
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message="인증 코드가 만료되었습니다. 재발송 후 다시 시도하세요.", result=False)
        # try_count가 5 이상이면 실패 처리
        if try_count >= 5:
            db.close_db_connection(conn)
            return utils.ResultDTO(code=429, message="재발송 후 다시 시도하세요.", result=False)

        # 인증 코드가 일치하지 않으면 실패 처리
        if not is_verified and stored_code == verification_code:
            cursor.execute("UPDATE email_verification SET is_verified = 1 WHERE email = ?", (user_email,))
            conn.commit()
            db.close_db_connection(conn)
            return utils.ResultDTO(code=200, message="이메일 인증이 완료되었습니다.", result=True)
        else:
            db.close_db_connection(conn)
            return utils.ResultDTO(code=400, message="인증 코드가 일치하지 않습니다.", result=False)

    db.close_db_connection(conn)
    return utils.ResultDTO(code=404, message="올바르지 않은 이메일입니다.", result=False)

def find_password(user_email: str) -> utils.ResultDTO:
    if not utils.is_valid_email(user_email):
        return utils.ResultDTO(code=400, message="이메일 형식이 올바르지 않습니다.", result=False)
    
    return utils.ResultDTO(code=400, message="비밀번호 찾기 기능은 현재 지원하지 않습니다.", result=False)