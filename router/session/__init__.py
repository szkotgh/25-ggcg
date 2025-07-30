from flask import Blueprint, request
import src.utils as utils
import db.session

session_bp = Blueprint('session', __name__, url_prefix='/session')

@session_bp.route('', methods=['GET'])
def get_session_info():
    session_id = request.form.get('session_id')
    
    if not session_id:
        return utils.return_result(400, 'Session ID is required')

    sessions = db.session.get_info(session_id)
    if not sessions:
        return utils.return_result(404, 'Invalid session ID')

    return utils.return_result(200, 'Sessions retrieved successfully', {'sessions': sessions})

@session_bp.route('', methods=['DELETE'])
def delete_session():
    session_id = request.form.get('session_id')

    if db.session.deactivate_session(session_id):
        return utils.return_result(200, 'Session deactivated successfully')
    else:
        return utils.return_result(500, 'Failed to deactivate session')

@session_bp.route('', methods=['POST'])
def create_session():
    login_email = request.form.get('email')
    login_password = request.form.get('password')
    login_useragent = request.headers.get('User-Agent')
    login_ip = utils.get_client_ip()

    if not login_email or not utils.is_valid_email(login_email):
        return utils.return_result(400, 'Invalid email')
    if not login_password or not utils.is_valid_password(login_password):
        return utils.return_result(400, 'Invalid password') 

    session_id = db.session.create_session(login_email, login_password, login_useragent, login_ip)
    if not session_id:
        return utils.return_result(500, 'Failed to create session')

    return utils.return_result(200, 'Session created successfully', {'session_id': session_id})

@session_bp.route('/list', methods=['GET'])
def list_sessions():
    session_id = request.form.get('session_id')
    
    if not session_id:
        return utils.return_result(400, 'Session ID is required')

    sessions = db.session.get_session_list(session_id)
    
    # If no sessions found or session ID is invalid
    if not sessions:
        return utils.return_result(404, 'Invalid session ID')
    
    # session id는 모두 제거
    for session in sessions:
        session.pop('session_id', None)

    return utils.return_result(200, 'Sessions retrieved successfully', {'sessions': sessions})