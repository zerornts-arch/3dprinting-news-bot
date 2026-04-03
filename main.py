import os
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.header import Header
from datetime import datetime, timedelta, timezone, date
import google.generativeai as genai
from bs4 import BeautifulSoup
import re
import holidays

print("🚀 Lincsolution 지능형 3D프린팅 뉴스 브리핑 시스템!")

KST = timezone(timedelta(hours=9))

# 추가 임시공휴일 (holidays 라이브러리에 없는 특별한 날들)
ADDITIONAL_HOLIDAYS = {
    # 2025년 임시공휴일 (필요시 추가)
    date(2025, 5, 6): "어린이날 대체공휴일",
    # 2026년 임시공휴일 (필요시 추가)
    # date(2026, 6, 1): "임시공휴일",
}

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

def is_holiday_or_weekend(check_date):
    """한국 기준 공휴일 또는 주말 여부 확인"""
    # 주말 확인 (토요일=5, 일요일=6)
    if check_date.weekday() >= 5:
        return True, "주말"
    
    # 한국 공휴일 확인
    kr_holidays = holidays.KR()
    if check_date in kr_holidays:
        return True, kr_holidays.get(check_date)
    
    # 추가 임시공휴일 확인
    if check_date in ADDITIONAL_HOLIDAYS:
        return True, ADDITIONAL_HOLIDAYS[check_date]
    
    return False, None

def get_last_working_day():
    """마지막 근무일 계산"""
    current = datetime.now(KST)
    check_date = current.date() - timedelta(days=1)
    
    # 이전 날부터 거슬러 올라가며 마지막 근무일 찾기
    while True:
        is_holiday, holiday_name = is_holiday_or_weekend(check_date)
        if not is_holiday:
            break
        check_date -= timedelta(days=1)
    
    # 마지막 근무일 오전 10시로 설정
    last_working_datetime = datetime.combine(check_date, datetime.min.time().replace(hour=10))
    last_working_datetime = last_working_datetime.replace(tzinfo=KST)
    
    return last_working_datetime

def calculate_collection_period():
    """수집 기간 계산 및 정보 출력"""
    now = datetime.now(KST)
    today = now.date()
    
    # 오늘부터 거슬러 올라가며 연속 휴일 계산
    collection_days = 1  # 오늘 포함
    check_date = today - timedelta(days=1)
    
    holiday_info = []
    while True:
        is_holiday, holiday_name = is_holiday_or_weekend(check_date)
        if not is_holiday:
            break
        collection_days += 1
        day_name = ['월','화','수','목','금','토','일'][check_date.weekday()]
        holiday_info.append(f"{check_date.strftime('%m/%d')}({day_name}){holiday_name}")
        check_date -= timedelta(days=1)
    
    since = now - timedelta(days=collection_days)
    
    print(f"\n📅 수집 기간 분석:")
    print(f"  오늘: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)")
    
    if collection_days == 1:
        print(f"  📊 수집 범위: 최근 24시간 (일반 평일)")
        period_label = f"{today.strftime('%m월 %d일')} 브리핑"
    else:
        print(f"  📊 수집 범위: 최근 {collection_days}일")
        print(f"  🏖️ 포함된 휴일: {', '.join(holiday_info)}")
        start_date = (today - timedelta(days=collection_days-1)).strftime('%m월 %d일')
        end_date = today.strftime('%m월 %d일')
        period_label = f"{start_date} ~ {end_date} 모아보기 ({collection_days}일치)"
    
    return since, period_label

def clean_text(text):
    if not text: return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

def normalize_title(title):
    title = title.lower()
    title = re.sub(r'[^\w\s가-힣]', '', title)
    company_names = ['stratasys', 'markforged', 'bambu', 'creality', 'prusa',
                     'formlabs', 'ultimaker', 'makerbot', '3dsystems', 'hp',
                     '삼성', 'lg', '현대', '기아', '포스코', '한화', '링크솔루션']
    for company in company_names:
        title = title.replace(company, '')
    return re.sub(r'\s+', ' ', title).strip()

def calculate_similarity(title1, title2):
    words1 = set(normalize_title(title1).split())
    words2 = set(normalize_title(title2).split())
    if not words1 or not words2: return 0.0
    return len(words1 & words2) / len(words1 | words2)

def is_relevant_3d(title, summary):
    text = f"{title} {summary}".lower()
    return any(keyword.lower() in text for keyword in KEYWORDS_3D)

def fetch_articles(since):
    """지정된 시간부터 현재까지 기사 수집 + 중복 제거"""
    print(f"\n📰 뉴스 수집 중... (기준: {since.strftime('%m/%d %H:%M')} 이후)")
    articles = {"국내": [], "해외": [], "링크솔루션": []}
    all_collected_titles = []

    for region, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                print(f"  📡 {region} 수집: {url[:50]}...")
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:15]:  # 연휴 대비 최대 15개
                    published = datetime.now(KST)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(KST)
                        except: pass
                    
                    if published < since: continue

                    title = clean_text(entry.get("title", ""))
                    summary = clean_text(entry.get("summary", ""))
                    link = entry.get("link", "")

                    if not title: continue

                    if region != "링크솔루션" and not is_relevant_3d(title, summary):
                        continue

                    # 중복 검사
                    is_duplicate = False
                    for existing_title in all_collected_titles:
                        if calculate_similarity(title, existing_title) >= 0.7:
                            print(f"  🔄 중복 제거: '{title[:35]}...'")
                            is_duplicate = True
                            break
                    
                    if is_duplicate: continue

                    all_collected_titles.append(title)
                    articles[region].append({
                        "title": title,
                        "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                        "link": link,
                        "source": feed.feed.get("title", "Unknown"),
                        "published": published.strftime("%m/%d %H:%M")
                    })
                        
            except Exception as e:
                print(f"  ⚠️ 수집 오류: {e}")
                continue

    print(f"  ✅ 최종 수집 - 국내: {len(articles['국내'])}개, 해외: {len(articles['해외'])}개, 링크솔루션: {len(articles['링크솔루션'])}개")
    return articles

def generate_ai_briefing(articles):
    """Google Gemini AI로 브리핑 생성"""
    print("\n🤖 AI 브리핑 생성 중...")
    
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    print(f"  API 키 길이: {len(api_key)}자")
    
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY 없음. 기본 브리핑으로 대체합니다.")
        return create_fallback_briefing(articles)
        
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        domestic_text = "\n".join([
            f"제목: {a['title']}\n시간: {a['published']}\n링크: {a['link']}\n출처: {a['source']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "관련 기사 없음"
        
        international_text = "\n".join([
            f"제목: {a['title']}\n시간: {a['published']}\n링크: {a['link']}\n출처: {a['source']}\n---"
            for a in articles["해외"]
        ]) if articles["해외"] else "관련 기사 없음"
        
        linksolution_text = "\n".join([
            f"제목: {a['title']}\n시간: {a['published']}\n링크: {a['link']}\n출처: {a['source']}\n---"
            for a in articles["링크솔루션"]
        ]) if articles["링크솔루션"] else "관련 기사 없음"

        prompt = f"""
당신은 3D프린팅 전문 뉴스 큐레이터입니다.
수집된 기사들을 분석하여 브리핑을 작성해주세요.

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
   - 새롭게 업데이트된 내용만 포함 (기존 내용 반복 금지)

3. 해외 동향 작성 규칙:
   - 영어 제목을 반드시 자연스러운 한국어로 번역
   - 각 기사를 한 줄 한국어 요약으로 작성
   - 원문 링크 첨부

4. 국내/링크솔루션 동향:
   - 각 기사를 간결한 한 줄 요약으로 작성
   - 원문 링크 첨부

5. 형식:
   • [한글 제목/요약]
     🔗 [링크]

6. 기사가 없는 섹션: "새로운 소식이 없습니다."

7. 절대 포함하지 말 것: 인사말, 맺음말, 날짜 머리말

현재 날짜: {datetime.now(KST).strftime("%Y년 %m월 %d일")}
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
        result += "새로운 소식이 없습니다.\n\n"
    
    result += "🌍 해외 동향\n"
    if articles["해외"]:
        for a in articles["해외"][:5]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
    else:
        result += "새로운 소식이 없습니다.\n\n"
    
    result += "🏢 링크솔루션 관련 뉴스\n"
    if articles["링크솔루션"]:
        for a in articles["링크솔루션"][:5]:
            result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
    else:
        result += "새로운 소식이 없습니다.\n\n"
    
    return result

def send_email(subject, body):
    """Gmail 다중 발송"""
    print("\n📧 이메일 발송 중...")
    try:
        from_addr = os.environ.get("EMAIL_FROM", "").replace('\n', '').replace('\r', '').strip()
        raw_to = os.environ.get("EMAIL_TO", "").replace('\n', '').replace('\r', '').strip()
        app_password = os.environ.get("EMAIL_APP_PASSWORD", "").replace('\n', '').replace('\r', '').replace(' ', '').strip()

        to_list = [e.strip() for e in raw_to.split(',') if e.strip()]
        to_string = ", ".join(to_list)

        print(f"  발송자: {from_addr}")
        print(f"  수신자 ({len(to_list)}명): {to_string}")

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
    today = now.date()
    
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')} KST] 시스템 시작\n")
    
    # 🚨 휴일/주말 체크 (발송 여부 결정)
    is_holiday, holiday_name = is_holiday_or_weekend(today)
    
    if is_holiday:
        print(f"📅 오늘은 {holiday_name}입니다. 브리핑 발송을 건너뜁니다. 💤")
        print("다음 평일에 모아서 발송됩니다!")
        return

    print("📅 오늘은 평일입니다. 브리핑을 준비합니다!")
    
    # 1. 수집 기간 계산
    since, period_label = calculate_collection_period()
    
    # 2. 뉴스 수집
    articles = fetch_articles(since)
    
    # 3. AI 브리핑 생성
    briefing = generate_ai_briefing(articles)
    
    # 4. 이메일 구성
    subject = "[Lincsolution] 매일 보는 3D프린팅 뉴스"
    
    body = f"""안녕하세요!!

링크솔루션 정우민입니다!!
이메일은 3D프린팅 관련 뉴스를 정리하여 평일 오전 10시 자동 발송됩니다.
------------------------------------
📅 {period_label}

{briefing}
------------------------------------

감사합니다
우민짱"""
    
    # 5. 발송
    result = send_email(subject, body)
    
    if result:
        print("\n🎉 브리핑 발송 완료!")
    else:
        print("\n❌ 브리핑 발송 실패!")

if __name__ == "__main__":
    main()
