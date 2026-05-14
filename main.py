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
from difflib import SequenceMatcher

print("🚀 Lincsolution 뉴스 브리핑 시스템 v3.0 (국내외 각 10개 + 24시간 엄격분리)")

KST = timezone(timedelta(hours=9))

ADDITIONAL_HOLIDAYS = {
    date(2025, 5, 6): "어린이날 대체공휴일",
}

# =============================================
# 📡 다양한 뉴스 소스 (수집량 증가)
# =============================================
RSS_FEEDS = {
    "국내": [
        "https://news.google.com/rss/search?q=3D프린팅+OR+적층제조+OR+바이오프린팅&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.naver.com/main/rss/section.naver?sid1=105",
        "https://rss.daum.net/news/digital",
        "https://rss.etnews.com/Section902.xml",
    ],
    "국외": [
        "https://3dprintingindustry.com/feed/",
        "https://all3dp.com/feed/",
        "https://3dprint.com/feed/",
        "https://news.google.com/rss/search?q=3D+printing+OR+additive+manufacturing&hl=en-US&gl=US&ceid=US:en",
    ],
    "미국이란": [
        "https://news.google.com/rss/search?q=미국+이란&hl=ko&gl=KR&ceid=KR:ko",
        "https://news.google.com/rss/search?q=US+Iran&hl=en-US&gl=US&ceid=US:en",
    ]
}

KEYWORDS_3D = [
    "3d printing", "3d printer", "additive manufacturing", "3d printed",
    "3d프린터", "3d프린팅", "적층제조", "3차원프린팅", "바이오프린팅", "3d 프린팅"
]

KEYWORDS_IRAN = [
    "이란", "iran", "미국", "중동", "전쟁", "war", "갈등", "conflict",
    "핵", "nuclear", "제재", "sanction", "호르무즈"
]

def clean_text(text):
    if not text: return ""
    soup = BeautifulSoup(text, 'html.parser')
    text = soup.get_text()
    return re.sub(r'\s+', ' ', text).strip()

def normalize_title_advanced(title):
    """고급 제목 정규화"""
    t = title.lower()
    t = re.sub(r'(연합뉴스|뉴시스|뉴스1|한국경제|조선일보|중앙일보|동아일보|머니투데이|아시아경제|이데일리|전자신문)', '', t)
    t = re.sub(r'[^\w가-힣\s]', '', t)
    stopwords = ['발표', '출시', '공개', '새로운', '최신', '속보', '단독', '종합', '위한', '통해', '대한', '관련', '등장']
    for word in stopwords:
        t = re.sub(r'\b' + word + r'\b', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def is_duplicate_advanced(new_title, seen_titles, threshold=0.55):
    """3단계 강력한 중복 검사"""
    new_norm = normalize_title_advanced(new_title)
    new_words = set(new_norm.split())
    
    if len(new_words) < 2:
        return False
    
    for seen in seen_titles:
        seen_norm = normalize_title_advanced(seen)
        seen_words = set(seen_norm.split())
        
        if not seen_words:
            continue
        
        # 1단계: 완전 일치
        if new_norm == seen_norm:
            print(f"    🔴 완전중복: {new_title[:35]}...")
            return True
        
        # 2단계: 문자열 유사도
        similarity = SequenceMatcher(None, new_norm, seen_norm).ratio()
        if similarity >= threshold:
            print(f"    🟠 유사중복({similarity:.0%}): {new_title[:35]}...")
            return True
        
        # 3단계: 핵심 단어 포함도
        if len(new_words) > 0:
            intersection = len(new_words & seen_words)
            containment = intersection / len(new_words)
            if containment >= 0.70:
                print(f"    🟡 포함중복({containment:.0%}): {new_title[:35]}...")
                return True
    
    return False

def is_relevant(title, summary, keywords):
    text = f"{title} {summary}".lower()
    return any(k.lower() in text for k in keywords)

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
    
    # 🔥 핵심 변경: 어제 기사 완전 차단을 위한 24시간 엄격 분리
    if collection_days == 1:
        # 평일: 정확히 24시간 전부터 수집 (어제 발송 이후 ~ 지금까지)
        since = now - timedelta(hours=24)
    else:
        # 주말/연휴 후: 해당 일수만큼 과거로
        since = now - timedelta(days=collection_days)
    
    print(f"\n📅 수집 기간:")
    if collection_days == 1:
        period_label = f"{today.strftime('%m월 %d일')} 브리핑 (최근 24시간)"
    else:
        start_date = (today - timedelta(days=collection_days - 1)).strftime('%m월 %d일')
        end_date = today.strftime('%m월 %d일')
        period_label = f"📦 {start_date} ~ {end_date} 모아보기 ({collection_days}일치)"
        for h in holiday_info:
            print(f"  🏖️ {h}")
    
    return since, period_label

def fetch_articles(since):
    """강화된 뉴스 수집 - 10개 확보를 위한 넉넉한 수집"""
    print(f"\n📰 뉴스 수집 중... (기준: {since.strftime('%m/%d %H:%M')} 이후)")
    
    articles = {"국내": [], "국외": [], "미국이란": []}
    global_seen_urls = set()
    section_seen_titles = {"국내": [], "국외": [], "미국이란": []}
    
    for region, feeds in RSS_FEEDS.items():
        emoji = {'국내': '🇰🇷', '국외': '🌍', '미국이란': '⚔️'}[region]
        print(f"\n  {emoji} {region} 수집 중...")
        region_count = 0
        
        for url in feeds:
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    continue
                
                feed_count = 0
                # 10개를 확보하기 위해 더 많은 기사 검토 (40개로 증가)
                for entry in feed.entries[:40]:
                    published = datetime.now(KST)
                    if hasattr(entry, "published_parsed") and entry.published_parsed:
                        try:
                            published = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc).astimezone(KST)
                        except:
                            pass
                    
                    # 🔥 24시간 이전 기사 엄격 필터링
                    if published < since:
                        continue
                    
                    title = clean_text(entry.get("title", ""))
                    summary = clean_text(entry.get("summary", ""))
                    link = entry.get("link", "")
                    
                    if not title or not link:
                        continue
                    
                    # 키워드 필터
                    if region in ["국내", "국외"] and not is_relevant(title, summary, KEYWORDS_3D):
                        continue
                    elif region == "미국이란" and not is_relevant(title, summary, KEYWORDS_IRAN):
                        continue
                    
                    # URL 중복 제거
                    clean_url = re.sub(r'\?.*', '', link)
                    if clean_url in global_seen_urls:
                        continue
                    
                    # 강화된 중복 검사
                    if is_duplicate_advanced(title, section_seen_titles[region]):
                        continue
                    
                    global_seen_urls.add(clean_url)
                    section_seen_titles[region].append(title)
                    articles[region].append({
                        "title": title,
                        "summary": summary[:150] + "..." if len(summary) > 150 else summary,
                        "link": link,
                        "source": feed.feed.get("title", "Unknown"),
                        "published": published.strftime("%m/%d %H:%M")
                    })
                    feed_count += 1
                    region_count += 1
                
                if feed_count > 0:
                    source_name = feed.feed.get("title", url[:30])[:20]
                    print(f"    ✅ [{source_name}] {feed_count}개")
                    
            except Exception as e:
                print(f"    ⚠️ 오류: {e}")
                continue
        
        print(f"  📊 {region} 최종: {region_count}개")
    
    print(f"\n  ✅ 전체 수집 결과:")
    print(f"     🇰🇷 국내: {len(articles['국내'])}개")
    print(f"     🌍 국외: {len(articles['국외'])}개")
    print(f"     ⚔️ 미국이란: {len(articles['미국이란'])}개")
    
    return articles

def translate_titles(articles_list, model, section_name):
    """국외 기사 제목 한국어 번역 (강화된 버전)"""
    if not articles_list:
        return articles_list
    
    english_articles = [a for a in articles_list if re.search(r'[a-zA-Z]{5,}', a['title'])]
    if not english_articles:
        return articles_list
    
    print(f"\n  🌍 {section_name} {len(english_articles)}개 기사 번역 중...")
    
    titles_to_translate = "\n".join([f"{i+1}. {a['title']}" for i, a in enumerate(english_articles)])
    
    translate_prompt = f"""다음 영어 뉴스 제목들을 자연스러운 한국어로 번역해주세요.
3D프린팅, 적층제조 등 전문용어는 한국 업계 표준 용어로 번역하세요.
특수문자나 마크다운 없이 번호와 번역문만 출력하세요.

{titles_to_translate}

출력 형식 (다른 설명 없이 이 형식만):
1. 한국어 번역 제목
2. 한국어 번역 제목
3. 한국어 번역 제목"""
    
    try:
        response = model.generate_content(translate_prompt)
        translated_lines = response.text.strip().split('\n')
        
        translated_count = 0
        for line in translated_lines:
            line = re.sub(r'[*#`]', '', line).strip()
            match = re.match(r'^(\d+)[\.\)]\s*(.+)$', line)
            if match:
                idx = int(match.group(1)) - 1
                translated_title = match.group(2).strip()
                if 0 <= idx < len(english_articles):
                    original_title = english_articles[idx]['title']
                    for article in articles_list:
                        if article['title'] == original_title:
                            article['title'] = translated_title
                            article['title_original'] = original_title
                            translated_count += 1
                            print(f"    ✅ [{idx+1}] {translated_title}")
                            break
        
        print(f"  📊 번역 완료: {translated_count}개")
        
    except Exception as e:
        print(f"  ⚠️ 번역 오류: {e}")
    
    return articles_list

def generate_briefing(articles):
    """AI 브리핑 생성 - 국내 10개, 국외 10개, 미국이란 5개"""
    print("\n🤖 AI 브리핑 생성 중...")
    
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    print(f"  API 키 길이: {len(api_key)}자")
    
    if not api_key:
        return create_simple_briefing(articles)
    
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        # 🔥 국외 및 미국이란 기사 제목 한국어 번역 실행
        articles["국외"] = translate_titles(articles["국외"], model, "국외")
        articles["미국이란"] = translate_titles(articles["미국이란"], model, "미국이란")
        
        domestic_text = "\n".join([
            f"제목: {a['title']}\n링크: {a['link']}\n---"
            for a in articles["국내"]
        ]) if articles["국내"] else "관련 기사 없음"
        
        foreign_text = "\n".join([
            f"제목: {a['title']}\n링크: {a['link']}\n---"
            for a in articles["국외"]
        ]) if articles["국외"] else "관련 기사 없음"
        
        iran_text = "\n".join([
            f"제목: {a['title']}\n링크: {a['link']}\n---"
            for a in articles["미국이란"]
        ]) if articles["미국이란"] else "관련 기사 없음"

        prompt = f"""당신은 뉴스 큐레이터입니다. 아래 기사들로 브리핑을 작성해주세요.

[국내 3D프린팅 기사]
{domestic_text}

[국외 3D프린팅 기사 - 이미 한국어로 번역 완료]
{foreign_text}

[미국-이란 관련 기사 - 이미 한국어로 번역 완료]
{iran_text}

=== 🚨 절대 준수 규칙 🚨 ===
1. 완전 한국어로만 작성
2. 같은 사건 기사는 1개만 선택 (중복 절대 금지)
3. 📌 개수 규칙: 국내 동향 최대 10개 / 국외 동향 최대 10개 / 미국이란 최대 5개
4. 구조 순서: 🇰🇷 국내 동향 → 🌍 국외 동향 → ⚔️ 미국 이란 전쟁 관련 뉴스
5. 형식: • [한국어 제목]\n  🔗 [링크]
6. 기사 없는 섹션: "새로운 소식이 없습니다."
7. 인사말, 맺음말, 날짜, 영어 표현 절대 금지
8. 국외 기사는 반드시 번역된 한국어 제목으로만 표시

현재 날짜: {datetime.now(KST).strftime("%Y년 %m월 %d일")}"""

        response = model.generate_content(prompt)
        print("  ✅ AI 브리핑 생성 완료")
        return response.text
        
    except Exception as e:
        print(f"  ⚠️ AI 오류: {e}")
        return create_simple_briefing(articles)

def create_simple_briefing(articles):
    """AI 실패 시 기본 브리핑 - 10개씩 출력"""
    result = ""
    sections = [
        ("🇰🇷 국내 동향", articles["국내"], 10),
        ("🌍 국외 동향", articles["국외"], 10),
        ("⚔️ 미국 이란 전쟁 관련 뉴스", articles["미국이란"], 5)
    ]
    
    for section_name, items, max_count in sections:
        result += f"{section_name}\n"
        if items:
            for a in items[:max_count]:
                result += f"• {a['title']}\n  🔗 {a['link']}\n\n"
        else:
            result += "새로운 소식이 없습니다.\n\n"
    
    return result

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

def main():
    now = datetime.now(KST)
    today = now.date()

    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')} KST] 시스템 시작\n")

    is_off, off_name = is_holiday_or_weekend(today)
    if is_off:
        print(f"📅 오늘은 {off_name}입니다. 발송을 건너뜁니다. 💤")
        return

    print("📅 오늘은 평일입니다. 브리핑을 준비합니다! ✅")

    since, period_label = calculate_collection_period()
    articles = fetch_articles(since)
    briefing = generate_briefing(articles)

    subject = "[Lincsolution] 매일 보는 3D프린팅 뉴스"
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
