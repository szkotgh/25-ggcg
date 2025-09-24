from dotenv import load_dotenv
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

load_dotenv()

smtp_server = os.getenv("MAIL_SERVER")
smtp_port = os.getenv("MAIL_PORT")
sender_email = os.getenv("MAIL_USERNAME")
receiver_email = os.getenv("MAIL_RECEIVER")
password = os.getenv("MAIL_PASSWORD")

def send_signup_verify_code(email, code, user_name):
    message = MIMEMultipart("alternative")
    message["Subject"] = f"[스마일푸드] 이메일 확인 코드: {code}"
    message["From"] = sender_email
    message["To"] = email

    html = f'''
<h2>안녕하세요, {user_name}님.</h2>
<p>아래 이메일 확인 코드를 입력해 스마일푸드 서비스 가입을 마무리해주세요.</p><br>

<div class="code">{code}</div><br>

이 코드는 5분 후에 만료됩니다.<br>
코드를 다른 사람과 공유하지 마세요.<br><br>

본 이메일은 스마일푸드 서비스 가입을 위해 발송되었습니다.<br>
문의사항이 있으시면 고객센터로 연락해 주세요.
    '''

    part1 = MIMEText(html, "html")
    message.attach(part1)
    send_email(email, message)
    
def send_welcome(email, user_name):
    message = MIMEMultipart("alternative")
    message["Subject"] = "[스마일푸드] 가입을 환영합니다"
    message["From"] = sender_email
    message["To"] = email

    html = f'''
<h2>안녕하세요, {user_name}님.</h2>
<p>스마일푸드 서비스에 가입해 주셔서 감사합니다.</p>
<p>본인이 가입한 것이 아니라면 즉시 고객센터로 알려주세요.</p>
    '''
    
    part1 = MIMEText(html, "html")
    message.attach(part1)
    send_email(email, message)

def send_email(email, message):
    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, email, message.as_string())
    
    