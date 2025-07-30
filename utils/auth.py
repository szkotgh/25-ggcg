from flask import session, redirect, url_for, flash
from functools import wraps
import db.user
import time

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get('uid') is None:
            flash('로그인이 필요합니다.', 'error')
            return redirect(url_for('router.user.signin'))
        
        if not db.user.get_user_info_by_uid(session['uid']):
            flash('유효하지 않은 세션입니다. 다시 로그인 해주세요.', 'error')
            session.pop('uid', None)
            return redirect(url_for('router.user.signin'))
        
        if session.get('LAST_ACTIVATE') is None or time.time() - session['LAST_ACTIVATE'] > 1800:
            flash('세션이 만료되었습니다. 다시 로그인 해주세요.', 'error')
            session.pop('uid', None)
            return redirect(url_for('router.user.signin'))
        session['LAST_ACTIVATE'] = time.time()
        
        return f(*args, **kwargs)
    return decorated_function