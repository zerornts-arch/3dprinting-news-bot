import os
import smtplib
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime

print("🚀 === Python 스크립트 시작 ===")
print("1단계: 환경변수 확인 중...")

def send_test_email():
    try:
        # 환경변수 읽기
        from_addr = os.environ.get("EMAIL_FROM", "")
        to_addr = os.environ.get("EMAIL_TO", "")
        app_password = os.environ.get("EMAIL_APP_PASSWORD", "")
        
        print(f"EMAIL_FROM 길이: {len(from_addr)}자")
        print(f"EMAIL_TO 길이: {len(to_addr)}자")
        print(f"EMAIL_APP_PASSWORD 길이: {len(app_password)}자")
        
        # 필수값 검증
        if not from_addr:
            print("❌ ERROR: EMAIL_FROM이 비어있습니다!")
            return False
        if not to_addr:
            print("❌ ERROR: EMAIL_TO가 비어있습니다!")
            return False
        if not app_password:
            print("❌ ERROR: EMAIL_APP_PASSWORD가 비어있습니다!")
            return False
        if len(app_password) != 16:
            print(f"❌ ERROR: 앱 비밀번호 길이가 {len(app_password)}자입니다. 16자여야 합니다!")
            return False
            
        print("2단계: 이메일 메시지 구성 중...")
        
        # 이메일 구성
        subject = f"🧪 테스트 메일 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        body = f"""안녕하세요!

GitHub Actions에서 자동으로 발송된 테스트 메일입니다.

✅ Python 코드 정상 실행
✅ 환경변수 정상 로드
✅ Gmail 연동 성공

발송자: {from_addr}
수신자: {to_addr}

이 메일이 도착했다면 시스템이 완벽하게 작동하고 있습니다!"""

        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = from_addr
        msg["To"] = to_addr
        
        print("3단계: Gmail SMTP 서버 연결 시도...")
        
        # Gmail 서버 연결 및 발송
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            print("4단계: TLS 보안 연결 시작...")
            server.starttls()
            print("5단계: Gmail 로그인 시도...")
            server.login(from_addr, app_password)
            print("6단계: 이메일 발송 시도...")
            server.send_message(msg)
        
        print("🎉 === 성공! 테스트 이메일 발송 완료 ===")
        print("📧 이메일함 확인 장소:")
        print("   - 받은편지함")
        print("   - 스팸함 (가장 가능성 높음)")
        print("   - 프로모션 탭")
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"❌ Gmail 로그인 실패: {e}")
        print("해결방법: GitHub Secrets에서 EMAIL_FROM, EMAIL_APP_PASSWORD 재확인")
        return False
    except Exception as e:
        print(f"❌ 예상치 못한 오류: {type(e).__name__}: {e}")
        return False

# ⭐ 이 부분이 가장 중요합니다! 실행 진입점
if __name__ == "__main__":
    print("메인 함수 시작...")
    result = send_test_email()
    if result:
        print("🏁 프로그램 성공적으로 완료")
    else:
        print("🏁 프로그램 오류로 인해 종료")
    print("=== 전체 로그 끝 ===")
