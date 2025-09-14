
import smtplib
import os
import threading
import queue
import src.utils as utils
from flask import render_template
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import db.user
import db.session

# Setting Email
class EmailSender:
    def __init__(self):
        self.smtp_server  = os.environ['MAIL_SERVER']
        self.smtp_port    = os.environ['MAIL_PORT']
        self.sender_email = os.environ['MAIL_USERNAME']
        self.password     = os.environ['MAIL_PASSWORD']
        self.email_queue = queue.Queue()
        self.worker_thread = threading.Thread(target=self._worker, daemon=True)
        self.worker_thread.start()

    def _worker(self):
        while True:
            item = self.email_queue.get()
            if item is None:
                break
            receiver_email, subject, plain, html = item
            self._send_email_now(receiver_email, subject, plain, html)
            self.email_queue.task_done()

    def _send_email_now(self, receiver_email: str, subject: str, plain, html):
        msg = MIMEMultipart("alternative")
        msg['Subject'] = subject
        msg['From'] = self.sender_email
        msg['To'] = receiver_email

        msg.attach(MIMEText(plain, 'plain'))
        msg.attach(MIMEText(html, 'html'))

        try:
            print(f"Connecting to SMTP server: {self.smtp_server}:{self.smtp_port} as {self.sender_email}")
            with smtplib.SMTP(self.smtp_server, int(self.smtp_port)) as smtp:
                smtp.starttls()
                smtp.login(self.sender_email, self.password)
                print("Connected to SMTP server successfully.")
                print(f"Sending email to {receiver_email} with subject: {subject}")
                smtp.sendmail(self.sender_email, receiver_email, msg.as_string())
                print("Email sent successfully.")
        except Exception as e:
            print(f"Failed to send email: {e}")

    def send_email(self, receiver_email: str, subject: str, plain, html):
        self.email_queue.put((receiver_email, subject, plain, html))

    def send_verification_code_email(self, receiver_email: str, code: str):
        subject = f'[스마일알러지] 인증코드 {code}'
        plain = f'이메일 인증을 위한 코드는 {code}입니다.'
        html = render_template('email/send_verification_code_email.html', receiver_email=receiver_email, code=code)
        self.send_email(receiver_email, subject, plain, html)

    def send_welcome_email(self, receiver_email: str, user_info: utils.ResultDTO):
        subject = '[스마일알러지] 회원가입을 환영합니다'
        plain = f'안녕하세요 {user_info.data["user_info"]["name"]}님, 서비스 가입을 환영합니다.'
        html = render_template('email/welcome_service_email.html', user_info=user_info.data["user_info"])
        self.send_email(receiver_email, subject, plain, html)
        
    def send_deleted_account_email(self, receiver_email: str, user_info: utils.ResultDTO):
        subject = '[스마일알러지] 서비스 탈퇴처리 되었습니다.'
        plain = f'안녕하세요 {user_info.data["user_info"]["name"]}님, 서비스 탈퇴가 완료되었습니다.'
        html = render_template('email/deleted_account_email.html', user_info=user_info.data["user_info"])
        self.send_email(receiver_email, subject, plain, html)
    
    def send_session_created_email(self, receiver_email: str, sid: str, session_deactive_link_hash: str):
        session_info = db.session.get_info(sid).data['session_info']
        user_info = db.user.get_info(session_info['uid']).data['user_info']
        subject = '[스마일알러지] 로그인 알림'
        plain = f'로그인 알림: {user_info["name"]}님, 새로운 환경에서 로그인 되었습니다.'
        session_deactive_link = f"{os.environ['SERVER_URL']}/session/deactive?link_hash={session_deactive_link_hash}"
        html = render_template('email/session_created_email.html', user_info=user_info, session_info=session_info, session_deactive_link=session_deactive_link)
        self.send_email(receiver_email, subject, plain, html)

    def send_password_find_email(self, receiver_email: str, user_info: utils.ResultDTO, link_hash: str):
        subject = '[스마일알러지] 비밀번호 찾기 요청'
        plain = f'비밀번호 찾기 요청: {user_info.data["user_info"]["name"]}님, 비밀번호 변경 요청이 발생했습니다.'
        password_find_url = f"{os.environ['SERVER_URL']}/user/find_password?link_hash={link_hash}"
        html = render_template('email/password_find_email.html', password_find_url=password_find_url, user_info=user_info.data["user_info"])
        self.send_email(receiver_email, subject, plain, html)
    
service = EmailSender()
