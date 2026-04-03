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

print("🚀 Lincsolution 3D프린팅 뉴스 브리핑 시스템 (해외 번역 완벽 보장)")

KST = timezone(timedelta(hours=9))

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
    if not text: return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

def make_dedup_key(title):
    key = title.lower()
    key = re.sub(r'[^\w가-힣]', ' ', key)
    stopwords = [
        '이', '가', '을', '를', '은', '는', '의', '에', '서', '로', '으로',
        '와', '과', '도', '만', '그', '것', '수', '등', '및', '또는',
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at',
        'to', 'for', 'of', 'with', 'by', 'from', 'is', 'are', 'was',
        '발표', '출시', '공개', '새로운', '최신', '관련', '위한', '대한'
    ]
    for word in stopwords:
        key = re.sub(r'\b' + word + r'\b', ' ', key)
    
    company_names = [
        'stratasys', 'markforged', 'bambu', 'creality', 'prusa', 'formlabs',
        'ultimaker', 'makerbot', '3dsystems', 'hp', 'carbon',
        '삼성', 'lg', '현대', '기아', '포스코', '한화', '두산',
        '링크솔루션', 'linksolution', 'lincsolution'
    ]
    for company in company_names:
        key = key.replace(company, '')
    
    words = sorted([w for w in key.split() if len(w) > 1])
    return ' '.join(words)

def is_duplicate(new_title, existing_titles, threshold=0.6):
    new_key = make_dedup_key(new_title)
    new_words = set(new_key.split())
    
    for existing_title in existing_titles:
        existing_key = make_dedup_key(existing_title)
        existing_words = set(existing_key.split())
        
        if not new_words or not existing_words:
            continue
        
        if new_key == existing_key:
            print(f"  🔴 완전 중복: '{new_title[:35]}...'")
            return True
        
        intersection = len(new_words & existing_words)
        union = len(new_words | existing_words)
        similarity = intersection / union if union > 0 else 0
        
        if similarity >= threshold:
            print(f"  🟡 유사 중복({similarity:.0%}): '{new_title[:35]}...'")
            return True
        
        if len(new_words) >= 3 and len(existing_words) >= 3:
            if new_words.issubset(existing_words) or existing_words.issubset(new_words):
                print(f"  🟠 포함 중복: '{new_title[:35]}...'")
                return True
    
    return False

def is_relevant_3d(title, summary):
    text = f"{title} {summary}".lower()
    return any(keyword.lower() in text for keyword in KEYWORDS_3D)

# =============================================
# 🌍 핵심: 해외 뉴스 사전 번역 시스템
# =============================================

def pre_translate_foreign_articles(articles, model):
    """
    해외 기사를 AI 브리핑 생성 전에 미리 완전 한국어로 번역
    → 번역 누락 문제를 근본적으로 해결하는 핵심 기능
    """
    if not articles["해외"]:
        return articles
    
    print("\n🌍 해외 기사 사전 번역 중...")
    
    # 번역할 제목들 모음
    titles_to_translate = []
    for i, article in enumerate(articles["해외"]):
        titles_to_translate.append(f"{i+1}. {article['title']}")
    
    titles_text = "\n".join(titles_to_translate)
    
    translate_prompt = f"""당신은 전문 한영 번역가입니다. 다음 3D프린팅 관련 영어 뉴스 제목들을 자연스러운 한국어로 번역해주세요.

번역 규칙:
1. 번호는 그대로 유지하세요
2. 회사명, 제품명 등 고유명사는 적절히 한국어 표기하거나 원문 유지
3. 자연스럽고 읽기 쉬운 한국어 문장으로 번역
4. 각 번역은 한 줄로만 작성
5. 설명이나 부연 설명 없이 번역문만 출력

번역할 제목들:
{titles_text}

출력 형식 (반드시 준수):
1. [한국어 번역 제목]
2. [한국어 번역 제목]
3. [한국어 번역 제목]
..."""
    
    try:
        response = model.generate_content(translate_prompt)
        translated_lines = response.text.strip().split('\n')
        
        # 번역 결과를 각 기사에 적용
        translated_count = 0
        for line in translated_lines:
            line = line.strip()
            if not line:
                continue
            
            # "1. 번역내용" 형식에서 번호와 내용 분리
            match = re.match(r'^(\d+)\.\s*(.+)$', line)
            if match:
                idx = int(match.group(1)) - 1
                translated_title = match.group(2).strip()
                
                if 0 <= idx < len(articles["해외"]):
                    original = articles["해외"][idx]["title"]
                    articles["해외"][idx]["title_ko"] = translated_title
                    articles["해외"][idx]["title_original"] = original
                    translated_count += 1
                    print(f"  ✅ [{idx+1}] {translated_title}")
        
        print(f"\n  📊 번역 완료: {translated_count}/{len(articles['해외'])}개")
        
        # 번역되지 않은 기사는 원본 제목 유지
        for article in articles["해외"]:
            if "title_ko" not in article:
                article["title_ko"] = article["title"]
                article["title_original"] = article["title"]
        
    except Exception as e:
        print(f"  ⚠️ 사전 번역 오류: {e}")
        # 번역 실패 시 원본 제목 유지
        for article in articles["해외"]:
            article["title_ko"] = article["title"]
            article["title_original"] = article["title"]
    
    return articles

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
    
    since = now - timedelta(days=collection_days)
    
    print(f"\n📅 수집 기간 분석:")
    print(f"  오늘: {today.strftime('%Y-%m-%d')} ({['월','화','수','목','금','토','일'][today.weekday()]}요일)")
    
    if collection_days == 1:
        print(f"  📊 일반 평일 브리핑 (최근 24시간)")
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
# 📰 뉴스 수집
# =============================================

def fetch_articles(since):
    print(f"\n📰 뉴스 수집 중... (기준: {since.strftime('%m/%d %H:%M')} 이후)")
    
    raw_articles = {"국내": [], "해외": [], "링크솔루션": []}
    collected_urls = set()
    all_titles = []

    for region, feeds in RSS_FEEDS.items():
        for url in feeds:
            try:
                print(f"  📡 {region} 수집: {url[:50]}...")
                feed = feedparser.parse(url)
                
                for entry in feed.entries[:15]:
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
                    
                    if region != "링크솔루션" and not is_relevant_3d(title, summary):
                        continue
                    
                    if link in collected_urls:
                        print(f"  🔵 URL 중복: '{title[:35]}...'")
                        continue
                    
                    if is_duplicate(title, all_titles):
                        continue
                    
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

    # 섹션 간 중복 제거
    print("\n  🔍 섹션 간 중복 제거 중...")
    linksolution_titles = [a["title"] for a in raw_articles["링크솔루션"]]
    
    filtered_domestic = []
    for article in raw_articles["국내"]:
        if is_duplicate(article["title"], linksolution_titles, threshold=0.5):
            print(f"  🟣 국내→링크솔루션 중복: '{article['title'][:35]}...'")
        else:
            filtered_domestic.append(article)
    
    raw_articles["국내"] = filtered_domestic
    
    print(f"\n  ✅ 최종 수집:")
    print(f"     국내: {len(raw_articles['국내'])}개")
    print(f"     해외: {len(raw_articles['해외'])}개")
    print(f"     링크솔루션: {len(raw_articles['링크솔루션'])}개")
    
    return raw_articles

# =============================================
# 🤖 AI 브리핑 생성 (번역 완료된 기사 활용)
# =============================================

def generate_ai_briefing(articles):
    print("\n🤖 AI 브리핑 생성 중...")
    
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    print(f"  API 키 길이: {len(api_key)}자")
    
    if not api_key:
        print("  ⚠️ GEMINI_API_KEY 없음. 기본 브리핑으로 대체합니다.")
        return create_fallback_briefing(articles)
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 🌍 핵심: 해외 기사 사전 번역 먼저 실행!
        articles = pre_translate_foreign_articles(articles, model)
        
        # 국내 기사 정리
        domestic_text = "\n".join([
            f"제목: {a['title']}\n링크: {a['link']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "관련 기사 없음"
        
        # 해외 기사 정리 (이미 번역된 한국어 제목 사용)
        international_text = "\n".join([
            f"한국어제목: {a.get('title_ko', a['title'])}\n링크: {a['link']}\n---"
            for a in articles["해외"]
        ]) if articles["해외"] else "관련 기사 없음"
        
        # 링크솔루션 기사 정리
        linksolution_text = "\n".join([
            f"제목: {a['title']}\n링크: {a['link']}\n---"
            for a in articles["링크솔루션"]
        ]) if articles["링크솔루션"] else "관련 기사 없음"

        prompt = f"""
당신은 3D프린팅 전문 뉴스 큐레이터입니다.
아래 기사들로 브리핑을 작성해주세요.

[국내 3D프린팅 기사]
{domestic_text}

[해외 3D프린팅 기사 - 이미 한국어로 번역 완료]
{international_text}

[링크솔루션 관련 기사]
{linksolution_text}

=== 🚨 절대 준수 규칙 🚨 ===

1. **완전 한국어 출력**: 모든 제목과 내용은 반드시 한국어로만 작성하세요. 영어 단어나 문장이 포함되면 안 됩니다.

2. **해외 동향 작성 규칙**:
   - "한국어제목"을 그대로 사용하거나 더 자연스럽게 다듬어서 작성
   - 절대로 영어 원문을 사용하지 마세요
   - 한 줄 한국어 요약으로 작성

3. **중복 제거**: 같은 사건을 다루는 기사는 1개만 선택. 링크솔루션 내용이 국내 동향에 있으면 링크솔루션 섹션에만 배치.

4. **구조 (순서 변경 금지)**:
🇰🇷 국내 동향
🌍 해외 동향
🏢 링크솔루션 관련 뉴스

5. **형식**:
• [완전 한국어 제목/요약]
  🔗 [링크]

6. **기사 없는 섹션**: "새로운 소식이 없습니다."

7. **절대 금지**: 인사말, 맺음말, 날짜, 영어 표현

현재 날짜: {datetime.now(KST).strftime("%Y년 %m월 %d일")}
"""

        response = model.generate_content(prompt)
        print("  ✅ AI 브리핑 생성 완료")
        return response.text
        
    except Exception as e:
        print(f"  ⚠️ AI 오류: {e}")
        return create_fallback_briefing(articles)

def create_fallback_briefing(articles):
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
                # 해외 기사는 번역된 제목 사용
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
    briefing = generate_ai_briefing(articles)

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
