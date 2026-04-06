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

print("🚀 Lincsolution 뉴스 브리핑 (완전 중복 차단 + 단순화 버전)")

KST = timezone(timedelta(hours=9))

ADDITIONAL_HOLIDAYS = {
    date(2025, 5, 6): "어린이날 대체공휴일",
}

# =============================================
# 📡 핵심 소스만 엄선 (중복 원인 완전 제거)
# =============================================
RSS_FEEDS = {
    # 🇰🇷 국내 3D프린팅 - 핵심 3개만
    "국내": [
        "https://news.google.com/rss/search?q=3D프린팅+OR+3D프린터+OR+적층제조&hl=ko&gl=KR&ceid=KR:ko",
        "https://rss.etnews.com/Section902.xml",
        "https://rss.zdnet.co.kr/news_list.xml",
    ],
    
    # 🌍 국외 3D프린팅 - 핵심 3개만  
    "국외": [
        "https://3dprintingindustry.com/feed/",
        "https://all3dp.com/feed/",
        "https://news.google.com/rss/search?q=3D+printing+OR+additive+manufacturing&hl=en-US&gl=US&ceid=US:en",
    ],
    
    # ⚔️ 미국-이란 전쟁 - 핵심 2개만
    "미국이란": [
        "https://news.google.com/rss/search?q=미국+이란+전쟁+OR+미국+이란+갈등&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=US+Iran+war+OR+US+Iran+conflict&hl=en-US&gl=US&ceid=US:en",
    ]
}

KEYWORDS_3D = [
    "3d printing", "3d printer", "additive manufacturing", "3d printed",
    "3d프린터", "3d프린팅", "적층제조", "3차원프린팅"
]

KEYWORDS_IRAN = [
    "이란", "iran", "미국이란", "us iran", "중동", "middle east",
    "핵", "nuclear", "제재", "sanction", "전쟁", "war", "갈등", "conflict"
]

def clean_text(text):
    if not text: return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

# =============================================
# 🔒 철통 중복 제거 (URL + 제목 정규화)
# =============================================

def normalize_title_for_dedup(title):
    """중복 비교용 제목 정규화"""
    # 소문자 변환
    t = title.lower()
    # 특수문자를 공백으로 변경
    t = re.sub(r'[^\w가-힣]', ' ', t)
    # 불용어 제거
    stopwords = [
        '이', '가', '을', '를', '은', '는', '의', '에', '서', '로', '으로',
        '와', '과', '도', '만', '등', '및', '또는', '그리고',
        'the', 'a', 'an', 'and', 'or', 'in', 'on', 'at', 'to',
        'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was',
        '발표', '출시', '공개', '새로운', '최신'
    ]
    for word in stopwords:
        t = re.sub(r'\b' + word + r'\b', ' ', t)
    
    # 단어 정렬 (순서 무관하게 비교)
    words = sorted([w for w in t.split() if len(w) > 1])
    return ' '.join(words)

def is_duplicate_content(new_title, existing_titles, threshold=0.4):
    """낮은 임계값으로 엄격한 중복 검사"""
    new_norm = normalize_title_for_dedup(new_title)
    new_words = set(new_norm.split())
    
    if not new_words:
        return False
    
    for existing in existing_titles:
        existing_norm = normalize_title_for_dedup(existing)
        existing_words = set(existing_norm.split())
        
        if not existing_words:
            continue
            
        # 완전 일치
        if new_norm == existing_norm:
            return True
            
        # Jaccard 유사도 (낮은 임계값으로 엄격하게)
        intersection = len(new_words & existing_words)
        union = len(new_words | existing_words)
        if union > 0 and intersection / union >= threshold:
            return True
            
        # 포함 관계
        if len(new_words) >= 2 and len(existing_words) >= 2:
            if new_words.issubset(existing_words) or existing_words.issubset(new_words):
                return True
    
    return False

def is_relevant(title, summary, keywords):
    """키워드 관련성 검사"""
    text = f"{title} {summary}".lower()
    return any(k.lower() in text for k in keywords)

# =============================================
# 🗓️ 공휴일/주말 처리
# =============================================

def is_holiday_or_weekend(check_date):
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
    
    since = now - timedelta(hours=36) if collection_days == 1 else now - timedelta(days=collection_days)
    
    print(f"\n📅 수집 기간:")
    print(f"  오늘: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)")
    
    if collection_days == 1:
        print(f"  📊 수집 범위: 최근 36시간")
        period_label = f"{today.strftime('%m월 %d일')} 브리핑"
    else:
        print(f"  📊 수집 범위: 최근 {collection_days}일")
        for h in holiday_info:
            print(f"     🏖️ {h}")
        start_date = (today - timedelta(days=collection_days - 1)).strftime('%m월 %d일')
        end_date = today.strftime('%m월 %d일')
        period_label = f"📦 {start_date} ~ {end_date} 모아보기 ({collection_days}일치)"
    
    return since, period_label

# =============================================
# 📰 뉴스 수집 (섹션별 독립 중복 관리)
# =============================================

def fetch_articles(since):
    print(f"\n📰 뉴스 수집 중... (기준: {since.strftime('%m/%d %H:%M')} 이후)")
    
    articles = {"국내": [], "국외": [], "미국이란": []}
    
    # 전체 시스템에서 URL 중복 완전 차단
    global_seen_urls = set()
    # 섹션별 제목 중복 차단
    section_seen_titles = {"국내": [], "국외": [], "미국이란": []}
    
    for region, feeds in RSS_FEEDS.items():
        emoji = {'국내': '🇰🇷', '국외': '🌍', '미국이란': '⚔️'}[region]
        print(f"\n  {emoji} {region} 수집 중...")
        region_count = 0
        
        for url in feeds:
            try:
                print(f"  📡 {url[:60]}...")
                feed = feedparser.parse(url)
                
                if not feed.entries:
                    print(f"     ⚠️ 빈 피드")
                    continue
                
                feed_count = 0
                for entry in feed.entries[:15]:  # 피드당 15개로 제한
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
                    
                    # 관련성 검사
                    if region in ["국내", "국외"]:
                        if not is_relevant(title, summary, KEYWORDS_3D):
                            continue
                    elif region == "미국이란":
                        if not is_relevant(title, summary, KEYWORDS_IRAN):
                            continue
                    
                    # 🔒 전체 시스템 URL 중복 차단
                    if link in global_seen_urls:
                        print(f"     ⛔ URL 중복: {title[:35]}...")
                        continue
                    
                    # 🔒 섹션 내 제목 중복 차단
                    if is_duplicate_content(title, section_seen_titles[region]):
                        print(f"     ⛔ 제목 중복: {title[:35]}...")
                        continue
                    
                    # 통과! 추가
                    global_seen_urls.add(link)
                    section_seen_titles[region].append(title)
                    articles[region].append({
                        "title": title,
                        "summary": summary[:120] + "..." if len(summary) > 120 else summary,
                        "link": link,
                        "source": feed.feed.get("title", "Unknown"),
                        "published": published.strftime("%m/%d %H:%M")
                    })
                    feed_count += 1
                    region_count += 1
                
                if feed_count > 0:
                    source_name = feed.feed.get("title", url[:30])[:20]
                    print(f"     ✅ [{source_name}] {feed_count}개")
                    
            except Exception as e:
                print(f"     ⚠️ 수집 오류: {e}")
                continue
        
        print(f"  📊 {region} 합계: {region_count}개")
    
    print(f"\n  ✅ 최종 수집 결과:")
    print(f"     🇰🇷 국내: {len(articles['국내'])}개")
    print(f"     🌍 국외: {len(articles['국외'])}개") 
    print(f"     ⚔️ 미국이란: {len(articles['미국이란'])}개")
    
    return articles

# =============================================
# 🌍 해외 기사 번역
# =============================================

def translate_foreign_titles(articles_list, model):
    """해외 기사 제목 한국어 번역"""
    if not articles_list:
        return articles_list
    
    print(f"\n  🌍 {len(articles_list)}개 기사 번역 중...")
    
    numbered_titles = "\n".join([f"{i+1}. {a['title']}" for i, a in enumerate(articles_list)])
    
    translate_prompt = f"""다음 영어 뉴스 제목들을 자연스러운 한국어로 번역해주세요.
번호를 유지하고, 번역문만 출력하세요.

{numbered_titles}

출력 형식:
1. [한국어 번역]
2. [한국어 번역]
..."""
    
    try:
        response = model.generate_content(translate_prompt)
        translated_lines = response.text.strip().split('\n')
        
        translated_count = 0
        for line in translated_lines:
            line = line.strip()
            match = re.match(r'^(\d+)\.\s*(.+)$', line)
            if match:
                idx = int(match.group(1)) - 1
                translated_title = match.group(2).strip()
                if 0 <= idx < len(articles_list):
                    articles_list[idx]["title_ko"] = translated_title
                    translated_count += 1
                    print(f"  ✅ [{idx+1}] {translated_title}")
        
        print(f"  📊 번역 완료: {translated_count}개")
        
    except Exception as e:
        print(f"  ⚠️ 번역 오류: {e}")
    
    # 번역 안된 것은 원본 유지
    for article in articles_list:
        if "title_ko" not in article:
            article["title_ko"] = article["title"]
    
    return articles_list

# =============================================
# 🤖 AI 브리핑 생성 (최대 개수 제한으로 중복 원천 차단)
# =============================================

def generate_briefing(articles):
    print("\n🤖 AI 브리핑 생성 중...")
    
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    print(f"  API 키 길이: {len(api_key)}자")
    
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY 없음. 기본 브리핑으로 대체합니다.")
        return create_simple_briefing(articles)
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 해외 기사 번역
        articles["국외"] = translate_foreign_titles(articles["국외"], model)
        
        # 미국이란 영어 기사 번역
        iran_english = [a for a in articles["미국이란"] if not any(ord(c) > 127 for c in a['title'][:10])]
        if iran_english:
            articles["미국이란"] = translate_foreign_titles(articles["미국이란"], model)
        
        # 각 섹션 텍스트 구성
        domestic_text = "\n".join([
            f"제목: {a['title']}\n링크: {a['link']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "관련 기사 없음"
        
        foreign_text = "\n".join([
            f"제목: {a.get('title_ko', a['title'])}\n링크: {a['link']}\n---"
            for a in articles["국외"]
        ]) if articles["국외"] else "관련 기사 없음"
        
        iran_text = "\n".join([
            f"제목: {a.get('title_ko', a['title'])}\n링크: {a['link']}\n---"
            for a in articles["미국이란"]
        ]) if articles["미국이란"] else "관련 기사 없음"

        prompt = f"""
당신은 뉴스 큐레이터입니다. 아래 기사들로 브리핑을 작성해주세요.

[국내 3D프린팅 기사]
{domestic_text}

[국외 3D프린팅 기사]
{foreign_text}

[미국-이란 관련 기사]
{iran_text}

=== 🚨 절대 준수 규칙 🚨 ===

1. **중복 완전 금지**: 같은 사건/내용을 다루는 기사는 무조건 1개만 선택하세요.

2. **개수 제한**: 각 섹션별로 **최대 5개**까지만 출력하세요. 아무리 기사가 많아도 5개를 넘지 마세요.

3. **완전 한국어**: 모든 제목과 내용은 한국어로만 작성하세요.

4. **구조 (반드시 이 순서)**:
🇰🇷 국내 동향
🌍 국외 동향  
⚔️ 미국 이란 전쟁 관련 뉴스

5. **형식**:
• [한국어 요약 제목]
  🔗 [링크]

6. **기사 없는 섹션**: "새로운 소식이 없습니다."

7. **절대 금지**: 인사말, 맺음말, 날짜, 영어 단어

현재 날짜: {datetime.now(KST).strftime("%Y년 %m월 %d일")}
"""

        response = model.generate_content(prompt)
        print("  ✅ AI 브리핑 생성 완료")
        return response.text
        
    except Exception as e:
        print(f"  ⚠️ AI 오류: {e}")
        return create_simple_briefing(articles)

def create_simple_briefing(articles):
    """AI 실패 시 기본 브리핑 (각 섹션 최대 5개)"""
    result = ""
    sections = [
        ("🇰🇷 국내 동향", articles["국내"]),
        ("🌍 국외 동향", articles["국외"]),
        ("⚔️ 미국 이란 전쟁 관련 뉴스", articles["미국이란"])
    ]
    
    for section_name, items in sections:
        result += f"{section_name}\n"
        if items:
            # 최대 5개만 출력하여 중복 가능성 원천 차단
            for a in items[:5]:
                title = a.get('title_ko', a['title'])
                result += f"• {title}\n  🔗 {a['link']}\n\n"
        else:
            result += "새로운 소식이 없습니다.\n\n"
    
    return result

# =============================================
# 📧 이메일 발송
# =============================================

def send_email(subject, body):
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

    since, period_label = calculate_collection_period()
    articles = fetch_articles(since)
    briefing = generate_briefing(articles)

    subject = "[Lincsolution] 매일 보는 3D프린팅 & 국제 뉴스"

    body = f"""안녕하세요!!

링크솔루션 정우민입니다!!
이메일은 관련 뉴스를 정리하여 평일 오전 10시경 자동 발송됩니다.
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
