from flask import Blueprint, request, session
import db.user
import src.utils as utils

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('', methods=['GET'])
def get_user_info():
    uid = request.args.get('uid')

    return db.user.get_info(uid).to_response()

@user_bp.route('', methods=['DELETE'])
def delete_user():
    email = request.form.get('email')
    password = request.form.get('password')

    return db.user.delete_user(email, password).to_response()

@user_bp.route('', methods=['POST'])
def create_user():
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')

    return db.user.create_user(email, password, name).to_response()

@user_bp.route('/send_email_verify_code', methods=['POST'])
def send_email_verify_code():
    user_email = request.form.get('email')

    return db.user.send_email_verify_code(user_email).to_response()
    
@user_bp.route('/verify_code', methods=['POST'])
def verify_code():
    user_email = request.form.get('email')
    verification_code = request.form.get('code')

    return db.user.verify_code(user_email, verification_code).to_response()

@user_bp.route('/find_password', methods=['GET', 'POST'])
def find_password():
    user_email = request.form.get('email')
    link_hash = request.args.get('link_hash')
    form_link_hash = request.form.get('link_hash')
    form_new_password = request.form.get('new_password')
    
    if request.method == 'GET':
        if not link_hash:
            return "해쉬 정보가 필요합니다.", 400

        link_info = db.user.get_find_password_link_info(link_hash)
        if not link_info.result:
            return f"{link_info.message}", link_info.code
        print(link_info.data)
        
        if link_info.data['pw_find_info']['is_used']:
            return "이미 사용된 링크입니다.", 400
        
        if not link_info.data['pw_find_info']['is_active']:
            return "비활성화된 링크입니다.<br>유효기간이 지났거나, 서버에서 비활성화시켰습니다.", 400
        
        return f"새 비밀번호를 입력해주세요. <form method='POST'><input type='text' name='link_hash' value='{link_hash}' style='display:none;'><input type='password' name='new_password' required><input type='submit' value='변경'></form>", 400

    if request.method == 'POST':
        # 비밀번호 변경 요청 시
        if form_link_hash and form_new_password:
            change_result = db.user.change_password(form_link_hash, form_new_password)
            if change_result.result:
                return "비밀번호가 성공적으로 변경되었습니다.", 200
            else:
                return f"비밀번호 변경 실패: {change_result.message}", change_result.code
        
        # 비밀번호 변경 링크 요청 시
        return db.user.find_password(user_email).to_response()