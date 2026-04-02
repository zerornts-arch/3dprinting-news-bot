import os
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timedelta, timezone
import google.generativeai as genai
from bs4 import BeautifulSoup
import re

print("🚀 우민님의 3D프린팅 뉴스 브리핑 시스템 시작!")

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

def is_relevant_3d(title, summary):
    """3D프린팅 관련성 검사"""
    text = f"{title} {summary}".lower()
    return any(keyword.lower() in text for keyword in KEYWORDS_3D)

def fetch_articles():
    """RSS 피드에서 관련 기사 수집"""
    print("📰 뉴스 수집 중...")
    articles = {"국내": [], "해외": [], "링크솔루션": []}
    since = datetime.now(KST) - timedelta(days=1)

    for region, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                print(f"  📡 {region} 뉴스 수집: {url[:50]}...")
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:8]:  # 각 피드당 최대 8개
                    published = datetime.now(KST)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(KST)
                        except:
                            pass
                    
                    if published < since:
                        continue

                    title = clean_text(entry.get("title", ""))
                    summary = clean_text(entry.get("summary", ""))
                    link = entry.get("link", "")

                    # 3D프린팅 피드는 키워드 필터링, 링크솔루션은 모든 기사
                    if region != "링크솔루션":
                        if title and is_relevant_3d(title, summary):
                            articles[region].append({
                                "title": title,
                                "summary": summary[:120] + "..." if len(summary) > 120 else summary,
                                "link": link,
                                "source": feed.feed.get("title", "Unknown")
                            })
                    else:
                        if title:
                            articles[region].append({
                                "title": title,
                                "summary": summary[:120] + "..." if len(summary) > 120 else summary,
                                "link": link,
                                "source": feed.feed.get("title", "Unknown")
                            })
            except Exception as e:
                print(f"  ⚠️ 수집 오류: {e}")
                continue

    print(f"  ✅ 수집 완료 - 국내: {len(articles['국내'])}개, 해외: {len(articles['해외'])}개, 링크솔루션: {len(articles['링크솔루션'])}개")
    return articles

def generate_ai_summary(articles):
    """Google Gemini AI로 뉴스 요약 생성"""
    print("🤖 AI 요약 생성 중...")
    
    try:
        genai.configure(api_key=os.environ["GEMINI_API_KEY"])
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        domestic_text = "\n".join([
            f"제목: {a['title']}\n출처: {a['source']}\n링크: {a['link']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "관련 기사 없음"
        
        international_text = "\n".join([
            f"제목: {a['title']}\n출처: {a['source']}\n링크: {a['link']}\n---"
            for a in articles["해외"]
        ]) if articles["해외"] else "관련 기사 없음"

        prompt = f"""
당신은 3D프린팅 전문 뉴스 큐레이터입니다. 다음 기사들을 분석하여 브리핑을 작성해주세요.

[국내 3D프린팅 기사]
{domestic_text}

[해외 3D프린팅 기사]  
{international_text}

작성 요구사항:
1. "1.3D프린팅 관련뉴스 국내,국외" 섹션으로 작성
2. 국내와 해외를 구분하여 정리
3. 각 뉴스는 2-3줄로 핵심 요약 후 링크 첨부
4. 전문적이면서도 이해하기 쉽게 작성
5. 인사말이나 맺음말은 절대 포함하지 마세요

현재 날짜: {datetime.now(KST).strftime("%Y년 %m월 %d일")}
"""

        response = model.generate_content(prompt)
        print("  ✅ AI 요약 완료")
        return response.text
        
    except Exception as e:
        print(f"  ⚠️ AI 요약 오류: {e}")
        # AI 실패 시 기본 형식으로 반환
        result = "🇰🇷 국내 동향\n"
        for a in articles["국내"][:3]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
        result += "\n🌍 해외 동향\n"
        for a in articles["해외"][:3]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
        return result

def build_linksolution_news(articles):
    """링크솔루션 뉴스 섹션 구성"""
    if articles["링크솔루션"]:
        result = ""
        for a in articles["링크솔루션"][:5]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
        return result
    else:
        return "오늘은 링크솔루션 관련 새로운 뉴스가 없습니다.\n"

def send_email(subject, body):
    """Gmail을 통한 이메일 발송"""
    print("📧 이메일 발송 중...")
    try:
        from_addr = os.environ["EMAIL_FROM"]
        to_addr = os.environ["EMAIL_TO"]
        app_password = os.environ["EMAIL_APP_PASSWORD"]

        msg = MIMEText(body, _charset="utf-8")
        msg["Subject"] = Header(subject, "utf-8")
        msg["From"] = from_addr
        msg["To"] = to_addr

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_addr, app_password)
            server.send_message(msg)
        
        print("  ✅ 이메일 발송 완료!")
        return True
        
    except Exception as e:
        print(f"  ❌ 이메일 발송 실패: {e}")
        return False

def main():
    print(f"\n[{datetime.now(KST).strftime('%Y-%m-%d %H:%M:%S')}] 브리핑 생성 시작\n")
    
    # 1. 뉴스 수집
    articles = fetch_articles()
    
    # 2. AI 요약 생성
    ai_summary = generate_ai_summary(articles)
    
    # 3. 링크솔루션 뉴스 구성
    linksolution_news = build_linksolution_news(articles)
    
    # 4. 우민님 맞춤형 이메일 구성
    today = datetime.now(KST).strftime("%Y년 %m월 %d일")
    subject = "[링크솔루션] 우민님이 테스트 중입니다."
    
    body = f"""안녕하세요!!

링크솔루션 정우민입니다!!
이메일은 3D프린팅 관련 뉴스를 정리하여 평일 8시 자동 발송됩니다.!!
------------------------------------

{ai_summary}

2. 링크솔루션 관련 뉴스

{linksolution_news}
---------------------------------

후원 : 국민은행 051001-04-149838

감사합니다
우민짱"""
    
    # 5. 이메일 발송
    result = send_email(subject, body)
    
    if result:
        print("\n🎉 우민님의 브리핑 발송 완료!")
    else:
        print("\n❌ 브리핑 발송 실패!")

if __name__ == "__main__":
    main()
