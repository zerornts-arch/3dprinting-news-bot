"""
샘플 데이터로 HTML 이메일 미리보기 파일 생성
"""
import sys
sys.path.insert(0, '.')

# main.py 에서 build_html_email 만 임포트
from main import build_html_email

SAMPLE_ARTICLES = {
    "국내": [
        {"title": '"60초마다 하나씩 뚝딱"…UNIST, 초고속 마이크로 3D프린팅 기술 개발', "link": "https://news.google.com/rss/articles/sample1", "source": "글로벌이코노믹", "published": "05/14 09:12"},
        {"title": '"재생의학으로 콩팥 살린다" AI·3D 프린팅 활용 신장 패치 개발', "link": "https://news.google.com/rss/articles/sample2", "source": "헬스조선", "published": "05/14 08:45"},
        {"title": "인천광역시교육청계양도서관, 지식에서 창작으로 3D 프린팅 작품전 개최", "link": "https://news.google.com/rss/articles/sample3", "source": "더코리아", "published": "05/14 07:30"},
        {"title": "캐딜락 F1팀, FIA 데뷔 앞두고 SLA 3D 프린팅 시스템 도입 확대", "link": "https://news.google.com/rss/articles/sample4", "source": "네이트", "published": "05/14 06:55"},
        {"title": "현대차, 3D 프린팅 기술로 전기차 경량 부품 양산 체제 구축", "link": "#", "source": "한국경제", "published": "05/14 06:10"},
        {"title": "KAIST 연구팀, 고강도 금속 3D 프린팅 기술로 항공우주 부품 개발 성공", "link": "#", "source": "전자신문", "published": "05/13 18:22"},
    ],
    "국외": [
        {"title": "Vivobarefoot, 맞춤형 3D 프린팅 샌들 'Tabi Gen 02' 출시", "link": "https://3dprintingindustry.com/sample1", "source": "3D Printing Industry", "published": "05/14 10:05"},
        {"title": "AML3D, 미 해군 제조 허브에 휴대용 금속 프린터 배치", "link": "https://3dprintingindustry.com/sample2", "source": "3D Printing Industry", "published": "05/14 09:50"},
        {"title": "Formnext Asia 선전 2026, AI 하드웨어 냉각에서 AM의 역할 조명", "link": "https://3dprintingindustry.com/sample3", "source": "3D Printing Industry", "published": "05/14 09:33"},
        {"title": "Mahdi Naïm 스튜디오, 3D 프린팅 래티스 구조 자전거 안장 'AERIS' 개발", "link": "https://3dprintingindustry.com/sample4", "source": "3D Printing Industry", "published": "05/14 08:17"},
        {"title": "뉴질랜드 기업들, 양모 기반 컬러 3D 프린팅 필라멘트 출시", "link": "https://3dprintingindustry.com/sample5", "source": "3D Printing Industry", "published": "05/14 07:44"},
        {"title": "NASA, 달 기지 건설용 레골리스 3D 프린팅 기술 실증 성공", "link": "#", "source": "All3DP", "published": "05/14 06:30"},
    ],
    "미국이란": [
        {"title": "이란전 여파로 6조∼9조원 '구멍'…美육군, 훈련 대폭 축소", "link": "https://news.google.com/rss/articles/iran1", "source": "연합뉴스", "published": "05/14 08:00"},
        {"title": "시진핑 입지 높인 이란전…아쉬워진 트럼프, 베이징서 종전해법 찾을까", "link": "https://news.google.com/rss/articles/iran2", "source": "한겨레", "published": "05/14 07:15"},
        {"title": "유가 1~2% 하락…트럼프 방중 속 미국·이란 협상 교착", "link": "https://news.google.com/rss/articles/iran3", "source": "뉴스1", "published": "05/14 06:45"},
        {"title": '"이란 군사력 끝났다"던 트럼프…美당국은 "대부분 살아남았다"', "link": "https://news.google.com/rss/articles/iran4", "source": "다음뉴스", "published": "05/14 06:20"},
        {"title": '"미국·이란 휴전 깨지면 UAE 가장 먼저 전쟁 휘말릴 듯"', "link": "https://news.google.com/rss/articles/iran5", "source": "KBS 뉴스", "published": "05/14 05:55"},
    ],
}

html = build_html_email("05월 14일 브리핑", SAMPLE_ARTICLES)

with open("preview.html", "w", encoding="utf-8") as f:
    f.write(html)

print("✅ preview.html 생성 완료!")
