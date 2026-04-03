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

print("🚀 Lincsolution 철통 중복 제거 3D프린팅 뉴스 브리핑 시스템!")

KST = timezone(timedelta(hours=9))

# 추가 임시공휴일
ADDITIONAL_HOLIDAYS = {
    date(2025, 5, 6): "어린이날 대체공휴일",
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

# =============================================
# 🔧 강화된 중복 제거 시스템
# =============================================

def clean_text(text):
    """HTML 태그 제거 및 텍스트 정리"""
    if not text: return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

def make_dedup_key(title):
    """
    중복 비교용 핵심 키워드 추출
    - 소문자 변환, 특수문자 제거
    - 불필요한 단어 제거 (조사, 접속사 등)
    - 회사명 제거로 내용 중심 비교
    """
    key = title.lower()
    
    # 특수문자 제거
    key = re.sub(r'[^\w가-힣]', ' ', key)
    
    # 불필요한 단어 제거
    stopwords = [
        # 한국어 조사/접속사
        '이', '가', '을', '를', '은', '는', '의', '에', '서', '로', '으로',
        '와', '과', '도', '만', '에서', '에게', '까지', '부터', '보다',
        '그', '이', '저', '것', '수', '등', '및', '또는', '그리고',
        # 영어 관사/접속사
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was',
        # 뉴스 공통 단어
        '발표', '출시', '공개', '진행', '예정', '완료', '성공', '실시',
        '관련', '통해', '위한', '대한', '새로운', '최신', '국내', '해외'
    ]
    
    for word in stopwords:
        key = re.sub(r'\b' + word + r'\b', ' ', key)
    
    # 회사명 제거 (회사만 다르고 내용 같은 경우 처리)
    company_names = [
        'stratasys', 'markforged', 'bambu', 'creality', 'prusa', 'formlabs',
        'ultimaker', 'makerbot', '3dsystems', '3d systems', 'hp', 'carbon',
        '삼성', 'lg', '현대', '기아', '포스코', '한화', '두산', '롯데',
        '링크솔루션', 'linksolution', 'lincsolution'
    ]
    
    for company in company_names:
        key = key.replace(company, '')
    
    # 단어 정렬 (순서 무관하게 비교)
    words = sorted([w for w in key.split() if len(w) > 1])
    return ' '.join(words)

def is_duplicate(new_title, existing_titles, threshold=0.6):
    """
    강화된 중복 검사
    - 완전 일치, 유사도, 포함 관계 모두 검사
    """
    new_key = make_dedup_key(new_title)
    new_words = set(new_key.split())
    
    for existing_title in existing_titles:
        existing_key = make_dedup_key(existing_title)
        existing_words = set(existing_key.split())
        
        if not new_words or not existing_words:
            continue
        
        # 1. 완전 일치 검사
        if new_key == existing_key:
            print(f"  🔴 완전 중복: '{new_title[:35]}...'")
            return True
        
        # 2. 유사도 검사 (Jaccard 유사도)
        intersection = len(new_words & existing_words)
        union = len(new_words | existing_words)
        similarity = intersection / union if union > 0 else 0
        
        if similarity >= threshold:
            print(f"  🟡 유사 중복({similarity:.0%}): '{new_title[:35]}...'")
            return True
        
        # 3. 포함 관계 검사
        if len(new_words) >= 3 and len(existing_words) >= 3:
            if new_words.issubset(existing_words) or existing_words.issubset(new_words):
                print(f"  🟠 포함 중복: '{new_title[:35]}...'")
                return True
    
    return False

def is_relevant_3d(title, summary):
    """3D프린팅 관련성 검사"""
    text = f"{title} {summary}".lower()
    return any(keyword.lower() in text for keyword in KEYWORDS_3D)

# =============================================
# 🗓️ 공휴일/주말 처리 시스템
# =============================================

def is_holiday_or_weekend(check_date):
    """한국 기준 공휴일 또는 주말 여부 확인"""
    if check_date.weekday() >= 5:
        day_names = ['월', '화', '수', '목', '금', '토', '일']
        return True, f"{day_names[check_date.weekday()]}요일"
    
    kr_holidays = holidays.KR()
    if check_date in kr_holidays:
        return True, kr_holidays.get(check_date)
    
    if check_date in ADDITIONAL_HOLIDAYS:
        return True, ADDITIONAL_HOLIDAYS[check_date]
    
    return False, None

def calculate_collection_period():
    """수집 기간 계산"""
    now = datetime.now(KST)
    today = now.date()
    
    collection_days = 1
    check_date = today - timedelta(days=1)
    holiday_info = []
    
    while True:
        is_off, holiday_name = is_holiday_or_weekend(check_date)
        if not is_off:
            break
        collection_days += 1
        day_name = ['월', '화', '수', '목', '금', '토', '일'][check_date.weekday()]
        holiday_info.append(f"{check_date.strftime('%m/%d')}({day_name}) {holiday_name}")
        check_date -= timedelta(days=1)
    
    since = now - timedelta(days=collection_days)
    
    print(f"\n📅 수집 기간 분석:")
    print(f"  오늘: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)")
    
    if collection_days == 1:
        print(f"  📊 일반 평일 브리핑 (최근 24시간)")
        period_label = f"{today.strftime('%m월 %d일')} 브리핑"
    else:
        print(f"  📊 수집 범위: 최근 {collection_days}일 (휴일 포함)")
        for h in holiday_info:
            print(f"     🏖️ {h}")
        start_date = (today - timedelta(days=collection_days - 1)).strftime('%m월 %d일')
        end_date = today.strftime('%m월 %d일')
        period_label = f"📦 {start_date} ~ {end_date} 모아보기 ({collection_days}일치)"
    
    return since, period_label

# =============================================
# 📰 뉴스 수집 시스템 (3단계 중복 제거)
# =============================================

def fetch_articles(since):
    """
    뉴스 수집 + 3단계 중복 제거
    1단계: URL 중복 제거
    2단계: 제목 유사도 중복 제거  
    3단계: 섹션 간 중복 제거 (링크솔루션 우선)
    """
    print(f"\n📰 뉴스 수집 중... (기준: {since.strftime('%m/%d %H:%M')} 이후)")
    
    raw_articles = {"국내": [], "해외": [], "링크솔루션": []}
    
    # 1단계: URL 중복 제거용
    collected_urls = set()
    # 2단계: 전체 제목 중복 제거용
    all_titles = []
    
    for region, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                print(f"  📡 {region} 수집: {url[:50]}...")
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:15]:
                    # 발행 시간 처리
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
                    
                    if not title or not link:
                        continue
                    
                    # 3D프린팅 관련성 검사
                    if region != "링크솔루션" and not is_relevant_3d(title, summary):
                        continue
                    
                    # 1단계: URL 중복 제거
                    if link in collected_urls:
                        print(f"  🔵 URL 중복 제거: '{title[:35]}...'")
                        continue
                    
                    # 2단계: 제목 유사도 중복 제거
                    if is_duplicate(title, all_titles):
                        continue
                    
                    # 통과! 기사 추가
                    collected_urls.add(link)
                    all_titles.append(title)
                    raw_articles[region].append({
                        "title": title,
                        "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                        "link": link,
                        "source": feed.feed.get("title", "Unknown"),
                        "published": published.strftime("%m/%d %H:%M")
                    })
                    
            except Exception as e:
                print(f"  ⚠️ 수집 오류: {e}")
                continue
    
    # 3단계: 섹션 간 중복 제거 (링크솔루션 우선)
    print("\n  🔍 섹션 간 중복 제거 중...")
    linksolution_titles = [a["title"] for a in raw_articles["링크솔루션"]]
    
    # 국내 동향에서 링크솔루션과 중복되는 기사 제거
    filtered_domestic = []
    for article in raw_articles["국내"]:
        if is_duplicate(article["title"], linksolution_titles, threshold=0.5):
            print(f"  🟣 국내→링크솔루션 중복 이동: '{article['title'][:35]}...'")
        else:
            filtered_domestic.append(article)
    
    raw_articles["국내"] = filtered_domestic
    
    print(f"\n  ✅ 최종 수집 완료:")
    print(f"     국내: {len(raw_articles['국내'])}개")
    print(f"     해외: {len(raw_articles['해외'])}개")  
    print(f"     링크솔루션: {len(raw_articles['링크솔루션'])}개")
    
    return raw_articles

# =============================================
# 🤖 AI 브리핑 생성 (최종 중복 검증)
# =============================================

def generate_ai_briefing(articles):
    """Google Gemini AI로 브리핑 생성 + 최종 중복 검증"""
    print("\n🤖 AI 브리핑 생성 및 최종 중복 검증 중...")
    
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    print(f"  API 키 길이: {len(api_key)}자")
    
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY 없음. 기본 브리핑으로 대체합니다.")
        return create_fallback_briefing(articles)
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # AI에게 제공할 상세 정보 (제목+요약으로 정확한 내용 파악)
        domestic_text = "\n".join([
            f"제목: {a['title']}\n요약: {a['summary']}\n링크: {a['link']}\n시간: {a['published']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "관련 기사 없음"
        
        international_text = "\n".join([
            f"제목: {a['title']}\n요약: {a['summary']}\n링크: {a['link']}\n시간: {a['published']}\n---"
            for a in articles["해외"]
        ]) if articles["해외"] else "관련 기사 없음"
        
        linksolution_text = "\n".join([
            f"제목: {a['title']}\n요약: {a['summary']}\n링크: {a['link']}\n시간: {a['published']}\n---"
            for a in articles["링크솔루션"]
        ]) if articles["링크솔루션"] else "관련 기사 없음"

        prompt = f"""
당신은 3D프린팅 전문 뉴스 큐레이터이자 '초강력 중복 제거 전문가'입니다.
제공된 모든 기사의 제목과 요약을 꼼꼼히 읽고, 완전히 새롭고 고유한 사건들만 골라내어 브리핑을 작성하세요.

[국내 3D프린팅 기사]
{domestic_text}

[해외 3D프린팅 기사]
{international_text}

[링크솔루션 관련 기사]
{linksolution_text}

=== 🚨 철통 중복 제거 규칙 (최우선) 🚨 ===

1. **사건 중심 필터링**: 같은 사건, 같은 제품 출시, 같은 계약을 다루는 기사는 제목이나 언론사가 달라도 무조건 1개만 선택하세요.

2. **섹션 간 절대 중복 금지**: 
   - 링크솔루션 관련 내용이 국내 동향에도 있다면 링크솔루션 섹션에만 배치
   - 국내 동향에서는 완전히 삭제

3. **번역 기사 처리**: 해외 기사를 국내 언론사가 번역 보도한 경우, 해외 동향 원본만 남기고 국내 번역본은 삭제

4. **극도로 엄격한 기준**: 조금이라도 "이거 위에서 본 내용인데?" 싶으면 과감히 삭제

=== 작성 규칙 ===

1. 구조 (순서 변경 금지):
🇰🇷 국내 동향
🌍 해외 동향  
🏢 링크솔루션 관련 뉴스

2. 해외 동향:
   - 영어 제목 → 자연스러운 한국어 번역
   - 한 줄 한국어 요약

3. 형식:
• [한글 요약 제목]
  🔗 [링크]

4. 기사 없는 섹션: "새로운 소식이 없습니다."

5. 절대 금지: 인사말, 맺음말, 날짜, 설명문

현재 날짜: {datetime.now(KST).strftime("%Y년 %m월 %d일")}
"""

        response = model.generate_content(prompt)
        print("  ✅ AI 브리핑 생성 및 최종 중복 검증 완료")
        return response.text
        
    except Exception as e:
        print(f"  ⚠️ AI 오류: {e}")
        return create_fallback_briefing(articles)

def create_fallback_briefing(articles):
    """AI 실패 시 기본 브리핑"""
    result = ""
    sections = [
        ("🇰🇷 국내 동향", articles["국내"]),
        ("🌍 해외 동향", articles["해외"]),
        ("🏢 링크솔루션 관련 뉴스", articles["링크솔루션"])
    ]
    
    for section_name, items in sections:
        result += f"{section_name}\n"
        if items:
            for a in items[:5]:
                result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
        else:
            result += "새로운 소식이 없습니다.\n\n"
    
    return result

# =============================================
# 📧 이메일 발송
# =============================================

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

# =============================================
# 🎯 메인 실행
# =============================================

def main():
    now = datetime.now(KST)
    today = now.date()

    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')} KST] 시스템 시작\n")

    # 휴일/주말 체크
    is_off, off_name = is_holiday_or_weekend(today)

    if is_off:
        print(f"📅 오늘은 {off_name}입니다. 발송을 건너뜁니다. 💤")
        print("➡️ 다음 평일에 모아서 발송됩니다!")
        return

    print("📅 오늘은 평일입니다. 브리핑을 준비합니다! ✅")

    # 수집 기간 계산
    since, period_label = calculate_collection_period()

    # 뉴스 수집 (3단계 중복 제거 포함)
    articles = fetch_articles(since)

    # AI 브리핑 생성 (최종 중복 검증)
    briefing = generate_ai_briefing(articles)

    # 이메일 구성
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

    result = send_email(subject, body)

    if result:
        print("\n🎉 브리핑 발송 완료!")
    else:
        print("\n❌ 브리핑 발송 실패!")

if __name__ == "__main__":
    main()
