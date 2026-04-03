import os
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timedelta, timezone
import google.generativeai as genai
from bs4 import BeautifulSoup
import re

print("🚀 Lincsolution 3D프린팅 뉴스 브리핑 시스템 시작!")

KST = timezone(timedelta(hours=9))

# RSS 피드 목록
RSS_FEEDS = {
    "해외": [
        "https://3dprintingindustry.com/feed/",
        "https://all3dp.com/feed/",
        "https://3dprint.com/feed/",
        "https://news.google.com/rss/search?q=3D+printing+OR+additive+manufacturing&hl=en-US&gl=US&ceid=US:en"
    ],
    "국내": [
        "https://news.google.com/rss/search?q=3D프린터+OR+3D프린팅+OR+적층제조&hl=ko&gl=KR&ceid=KR:ko",
        "https://rss.etnews.com/Section902.xml"
    ],
    "링크솔루션": [
        "https://news.google.com/rss/search?q=링크솔루션&hl=ko&gl=KR&ceid=KR:ko"
    ]
}

KEYWORDS_3D = [
    "3d printing", "3d printer", "additive manufacturing", "3d printed",
    "3d프린터", "3d프린팅", "적층제조", "3차원프린팅"
]

def clean_text(text):
    """HTML 태그 제거 및 텍스트 정리"""
    if not text:
        return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def normalize_title(title):
    """중복 비교를 위한 제목 정규화"""
    # 소문자 변환 및 특수문자 제거
    title = title.lower()
    title = re.sub(r'[^\w\s가-힣]', '', title)
    title = re.sub(r'\s+', ' ', title).strip()
    
    # 회사명 제거 (중복 판단 시 회사명 차이 무시)
    company_names = [
        'stratasys', 'markforged', 'bambu', 'creality', 'prusa',
        'formlabs', 'ultimaker', 'makerbot', '3dsystems', 'hp',
        '삼성', 'lg', '현대', '기아', '포스코', '한화', '링크솔루션'
    ]
    for company in company_names:
        title = title.replace(company, '')
    
    return re.sub(r'\s+', ' ', title).strip()

def calculate_similarity(title1, title2):
    """두 제목 간 유사도 계산 (0.0 ~ 1.0)"""
    words1 = set(normalize_title(title1).split())
    words2 = set(normalize_title(title2).split())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0

def is_relevant_3d(title, summary):
    """3D프린팅 관련성 검사"""
    text = f"{title} {summary}".lower()
    return any(keyword.lower() in text for keyword in KEYWORDS_3D)

def fetch_articles():
    """RSS 피드에서 당일 기사 수집 + 중복 제거"""
    print("📰 당일 뉴스 수집 및 중복 제거 중...")
    articles = {"국내": [], "해외": [], "링크솔루션": []}
    
    # 당일 기사만 수집 (24시간 이내)
    since = datetime.now(KST) - timedelta(hours=24)
    
    # 전체 수집된 제목들 (중복 제거용)
    all_collected_titles = []

    for region, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                print(f"  📡 {region} 수집: {url[:50]}...")
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:10]:
                    # 발행 시간 처리
                    published = datetime.now(KST)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(KST)
                        except:
                            pass
                    
                    # 24시간 이내 기사만 허용
                    if published < since:
                        continue

                    title = clean_text(entry.get("title", ""))
                    summary = clean_text(entry.get("summary", ""))
                    link = entry.get("link", "")

                    if not title:
                        continue

                    # 3D프린팅 관련성 검사 (링크솔루션 제외)
                    if region != "링크솔루션":
                        if not is_relevant_3d(title, summary):
                            continue

                    # 중복 검사 (유사도 70% 이상이면 중복으로 판단)
                    is_duplicate = False
                    for existing_title in all_collected_titles:
                        if calculate_similarity(title, existing_title) >= 0.7:
                            print(f"  🔄 중복 제거: '{title[:40]}...'")
                            is_duplicate = True
                            break
                    
                    if is_duplicate:
                        continue

                    # 중복이 아니면 추가
                    all_collected_titles.append(title)
                    articles[region].append({
                        "title": title,
                        "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                        "link": link,
                        "source": feed.feed.get("title", "Unknown"),
                        "published": published.strftime("%H:%M")
                    })
                        
            except Exception as e:
                print(f"  ⚠️ 수집 오류: {e}")
                continue

    print(f"  ✅ 수집 완료 - 국내: {len(articles['국내'])}개, 해외: {len(articles['해외'])}개, 링크솔루션: {len(articles['링크솔루션'])}개")
    return articles

def generate_ai_briefing(articles):
    """Google Gemini AI로 통합 브리핑 생성 (중복 제거 + 해외 번역)"""
    print("🤖 AI 브리핑 생성 중...")
    
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    print(f"  API 키 길이: {len(api_key)}자")
    
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY 없음. 기본 브리핑으로 대체합니다.")
        return create_fallback_briefing(articles)
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 각 섹션별 기사 정리
        domestic_text = "\n".join([
            f"제목: {a['title']}\n시간: {a['published']}\n링크: {a['link']}\n출처: {a['source']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "오늘 관련 기사 없음"
        
        international_text = "\n".join([
            f"제목: {a['title']}\n시간: {a['published']}\n링크: {a['link']}\n출처: {a['source']}\n---"
            for a in articles["해외"]
        ]) if articles["해외"] else "오늘 관련 기사 없음"
        
        linksolution_text = "\n".join([
            f"제목: {a['title']}\n시간: {a['published']}\n링크: {a['link']}\n출처: {a['source']}\n---"
            for a in articles["링크솔루션"]
        ]) if articles["링크솔루션"] else "오늘 관련 기사 없음"

        prompt = f"""
당신은 3D프린팅 전문 뉴스 큐레이터입니다.
오늘({datetime.now(KST).strftime("%Y년 %m월 %d일")}) 수집된 기사들을 분석하여 브리핑을 작성해주세요.

[국내 3D프린팅 기사]
{domestic_text}

[해외 3D프린팅 기사]
{international_text}

[링크솔루션 관련 기사]
{linksolution_text}

=== 작성 규칙 (반드시 준수) ===

1. 구조: 다음 3개 섹션으로만 구성
   🇰🇷 국내 동향
   🌍 해외 동향  
   🏢 링크솔루션 관련 뉴스

2. 중복 제거 규칙:
   - 회사명만 다르고 내용이 동일한 기사는 1개만 선택
   - 국내 동향과 링크솔루션 섹션에 같은 내용이 있다면 링크솔루션 섹션에만 배치
   - 오늘 새롭게 업데이트된 내용만 포함

3. 해외 동향 작성 규칙:
   - 영어 제목을 반드시 자연스러운 한국어로 번역
   - 각 기사를 한 줄 한국어 요약으로 작성
   - 원문 링크 첨부

4. 국내/링크솔루션 동향:
   - 각 기사를 간결한 한 줄 요약으로 작성
   - 원문 링크 첨부

5. 형식:
   각 기사는 다음 형식으로 작성:
   • [한글 제목/요약]
     🔗 [링크]

6. 기사가 없는 섹션: "오늘은 새로운 소식이 없습니다."

7. 절대 포함하지 말 것:
   - 인사말, 맺음말, 날짜 머리말
   - "1.3D프린팅 관련뉴스" 같은 불필요한 제목
"""

        response = model.generate_content(prompt)
        print("  ✅ AI 브리핑 생성 완료")
        return response.text
        
    except Exception as e:
        print(f"  ⚠️ AI 오류: {e}")
        return create_fallback_briefing(articles)

def create_fallback_briefing(articles):
    """AI 실패 시 기본 브리핑 생성"""
    result = ""
    
    result += "🇰🇷 국내 동향\n"
    if articles["국내"]:
        for a in articles["국내"][:5]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
    else:
        result += "오늘은 새로운 소식이 없습니다.\n\n"
    
    result += "🌍 해외 동향\n"
    if articles["해외"]:
        for a in articles["해외"][:5]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
    else:
        result += "오늘은 새로운 소식이 없습니다.\n\n"
    
    result += "🏢 링크솔루션 관련 뉴스\n"
    if articles["링크솔루션"]:
        for a in articles["링크솔루션"][:5]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
    else:
        result += "오늘은 새로운 소식이 없습니다.\n\n"
    
    return result

def send_email(subject, body):
    """Gmail 다중 발송"""
    print("📧 이메일 발송 중...")
    try:
        from_addr = os.environ.get("EMAIL_FROM", "").replace('\n', '').replace('\r', '').strip()
        raw_to = os.environ.get("EMAIL_TO", "").replace('\n', '').replace('\r', '').strip()
        app_password = os.environ.get("EMAIL_APP_PASSWORD", "").replace('\n', '').replace('\r', '').replace(' ', '').strip()

        to_list = [e.strip() for e in raw_to.split(',') if e.strip()]
        to_string = ", ".join(to_list)

        print(f"  발송자: {from_addr}")
        print(f"  수신자 ({len(to_list)}명): {to_string}")
        print(f"  앱 비밀번호 길이: {len(app_password)}자")

        if not from_addr or not to_list or not app_password:
            raise ValueError("이메일 설정 정보가 누락되었습니다.")
        if len(app_password) != 16:
            raise ValueError(f"앱 비밀번호 오류: {len(app_password)}자 (16자 필요)")

        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = from_addr
        msg["To"] = to_string

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_addr, app_password)
            server.sendmail(from_addr, to_list, msg.as_string())
        
        print(f"  ✅ {len(to_list)}명에게 발송 완료!")
        return True
        
    except Exception as e:
        print(f"  ❌ 발송 실패: {e}")
        return False

def main():
    now = datetime.now(KST)
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')} KST] 브리핑 생성 시작\n")
    
    # 1. 당일 뉴스 수집 (중복 제거 포함)
    articles = fetch_articles()
    
    # 2. AI 통합 브리핑 생성 (해외 번역 + 추가 중복 제거)
    briefing = generate_ai_briefing(articles)
    
    # 3. 이메일 구성
    today = now.strftime("%Y년 %m월 %d일")
    subject = "[Lincsolution] 매일 보는 3D프린팅 뉴스"
    
    body = f"""안녕하세요!!

링크솔루션 정우민입니다!!
이메일은 3D프린팅 관련 뉴스를 정리하여 평일 오전 10시 자동 발송됩니다.
------------------------------------
📅 {today} 브리핑

{briefing}
------------------------------------

감사합니다
우민짱"""
    
    # 4. 발송
    result = send_email(subject, body)
    
    if result:
        print("\n🎉 브리핑 발송 완료!")
    else:
        print("\n❌브리핑 발송 실패!")

if __name__ == "__main__":
    main()
