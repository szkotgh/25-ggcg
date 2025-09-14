from flask import Blueprint, request
import src.utils as utils
import db.session

session_bp = Blueprint('session', __name__, url_prefix='/session')

@session_bp.route('', methods=['GET'])
def get_session_info():
    sid = request.args.get('sid')

    return db.session.get_info(sid).to_response()

@session_bp.route('', methods=['POST'])
def create_session():
    login_email = request.form.get('email')
    login_password = request.form.get('password')
    login_useragent = request.headers.get('User-Agent', 'Unknown')
    login_ip = utils.get_client_ip()

    return db.session.create_session(login_email, login_password, login_useragent, login_ip).to_response()

@session_bp.route('', methods=['DELETE'])
def delete_session():
    sid = request.form.get('sid')

    return db.session.deactivate_session(sid).to_response()

@session_bp.route('/list', methods=['GET'])
def list_sessions():
    sid = request.args.get('sid')

    sessions = db.session.get_session_list(sid)
    
    # If no sessions found or session ID is invalid
    if not sessions.result:
        return sessions.to_response()

    # session id는 모두 제거
    for session in sessions.data['sessions_info']:
        session.pop('sid', None)

    return sessions.to_response()

@session_bp.route('/deactive', methods=['GET'])
def get_deactive_info():
    link_hash = request.args.get('link_hash')
    
    if not link_hash:
        return "해쉬 정보가 필요합니다.", 400

    deactive_info = db.session.get_session_deactive_info(link_hash)
    if not deactive_info.result:
        return f"{deactive_info.message}", deactive_info.code

    if deactive_info.data['deactive_info']['is_used']:
        return "이미 사용되었습니다.", 400
    
    deactivate_session_info = db.session.deactivate_session(deactive_info.data['deactive_info']['sid'])
    if deactivate_session_info.result:
        db.session.mark_deactive_link_as_used(link_hash)
        return "성공적으로 비활성화했습니다.", 200

    return f"세션 비활성화에 실패했습니다: {deactivate_session_info.message}", 500