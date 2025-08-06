from flask import Blueprint, Response, request, stream_with_context
import db.user
import db.session
import db.food
import src.utils as utils

food_bp = Blueprint('food', __name__, url_prefix='/food')

@food_bp.route('', methods=['GET'])
def get_food_info():
    sid = request.form.get('sid')
    fid = request.form.get('fid')
    
    return db.food.get_info(sid, fid).to_response()

@food_bp.route('', methods=['POST'])
def regi_food():
    session_id = request.form.get('sid')
    barcode = request.form.get('barcode')
    count = request.form.get('count', 1, type=int)

    return db.food.regi_food_with_barcode(session_id, barcode, count).to_response()

@food_bp.route('', methods=['DELETE'])
def delete_food():
    sid = request.form.get('sid')
    fid = request.form.get('fid')

    return db.food.delete_food(sid, fid).to_response()

@food_bp.route('/list', methods=['GET'])
def get_food_list():
    sid = request.form.get('sid')
    
    return db.food.get_list_info(sid).to_response()

@food_bp.route('/chat', methods=['GET'])
def chat():
    sid = request.form.get('sid')
    fid_list = request.form.getlist('fid')
    
    info = db.food.chat_food(sid, fid_list)
    if info.result == False:
        return info.to_response()

    return info.to_response()