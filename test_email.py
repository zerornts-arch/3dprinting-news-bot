import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

def send_test_email():
    """간단한 테스트 이메일 발송"""
    try:
        from_addr = os.environ["EMAIL_FROM"]
        to_addr = os.environ["EMAIL_TO"]
        app_password = os.environ["EMAIL_APP_PASSWORD"]
        
        subject = f"🧪 테스트 메일 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        body = """안녕하세요!

GitHub Actions에서 자동으로 발송된 테스트 메일입니다.

✅ Gmail 연동 성공
✅ 자동화 시스템 작동 확인

이 메일이 도착했다면 시스템이 정상 작동하고 있습니다!

다음 단계에서 3D프린팅 뉴스 수집 기능을 추가하겠습니다."""

        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = from_addr
        msg["To"] = to_addr

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_addr, app_password)
            server.send_message(msg)
        
        print("✅ 테스트 이메일 발송 성공!")
        
    except Exception as e:
        print(f"❌ 오류 발생: {e}")

if __name__ == "__main__":
    send_test_email
