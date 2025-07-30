from flask import Blueprint, request
import src.utils as utils
import db.session

session_bp = Blueprint('session', __name__, url_prefix='/session')

@session_bp.route('', methods=['GET'])
def get_session_info():
    sid = request.form.get('sid')

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
    sid = request.form.get('sid')

    sessions = db.session.get_session_list(sid)
    
    # If no sessions found or session ID is invalid
    if not sessions.result:
        return sessions.to_response()

    # session id는 모두 제거
    for session in sessions.data['sessions_info']:
        session.pop('sid', None)

    return sessions.to_response()