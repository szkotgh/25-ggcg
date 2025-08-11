from flask import Blueprint, request
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

@user_bp.route('/find_password', methods=['POST'])
def find_password():
    user_email = request.form.get('email')

    return db.user.find_password(user_email).to_response()