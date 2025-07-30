from flask import Blueprint, request
import db.user
import src.utils as utils

user_bp = Blueprint('user', __name__, url_prefix='/user')

@user_bp.route('', methods=['POST'])
def create_user():
    email = request.form.get('email')
    password = request.form.get('password')
    name = request.form.get('name')
    
    print(request.form)
    
    if not email or not utils.is_valid_email(email):
        return utils.return_result(400, 'Invalid email')
    if not password or not utils.is_valid_password(password):
        return utils.return_result(400, 'Invalid password')
    if not name or not utils.is_valid_username(name):
        return utils.return_result(400, 'Invalid username')

    if db.user.create_user(email, password, name):
        return utils.return_result(200, 'User created successfully')
    else:
        return utils.return_result(405, 'Failed to create user')

@user_bp.route('/send_email_verify_code', methods=['POST'])
def send_email_verify_code():
    user_email = request.form.get('email')
    if not user_email or not utils.is_valid_email(user_email):
        return utils.return_result(400, 'Invalid email')

    if db.user.send_email_verify_code(user_email):
        return utils.return_result(200, 'Verification email sent')
    else:
        return utils.return_result(405, 'Failed to create email verification')
    
@user_bp.route('/verify_code', methods=['POST'])
def verify_code():
    user_email = request.form.get('email')
    verification_code = request.form.get('code')
    
    if not user_email or not utils.is_valid_email(user_email):
        return utils.return_result(400, 'Invalid email')
    if not verification_code or not utils.is_valid_verification_code(verification_code):
        return utils.return_result(400, 'Invalid verification code')

    if db.user.verify_code(user_email, verification_code):
        return utils.return_result(200, 'Email verified successfully')
    else:
        return utils.return_result(405, 'Email verification failed')