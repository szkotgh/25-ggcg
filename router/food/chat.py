from flask import Blueprint, request
import db.food_chat

chat_bp = Blueprint('chat', __name__, url_prefix='/chat')

@chat_bp.route('', methods=['GET'])
def chat():
    sid = request.args.get('sid')
    fcid = request.args.get('fcid')

    return db.food_chat.get_info(sid, fcid).to_response()

@chat_bp.route('', methods=['POST'])
def create_food_chat():
    sid = request.form.get('sid')
    fid_list = request.form.getlist('fid')

    return db.food_chat.create_chat_db(sid, fid_list).to_response()
