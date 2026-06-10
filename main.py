import os
import json
import smtplib
import feedparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
from datetime import datetime, timedelta, timezone, date
import google.generativeai as genai
from bs4 import BeautifulSoup
import re
import holidays
from difflib import SequenceMatcher
from pathlib import Path

print("🚀 Lincsolution 뉴스 브리핑 시스템 v4.0 (HTML 뉴스레터)")

KST = timezone(timedelta(hours=9))

ADDITIONAL_HOLIDAYS = {
    date(2025, 5, 6): "어린이날 대체공휴일",
}

# =============================================
# 📡 다양한 뉴스 소스
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
    t = title.lower()
    t = re.sub(r'(연합뉴스|뉴시스|뉴스1|한국경제|조선일보|중앙일보|동아일보|머니투데이|아시아경제|이데일리|전자신문)', '', t)
    t = re.sub(r'[^\w가-힣\s]', '', t)
    stopwords = ['발표', '출시', '공개', '새로운', '최신', '속보', '단독', '종합', '위한', '통해', '대한', '관련', '등장']
    for word in stopwords:
        t = re.sub(r'\b' + word + r'\b', '', t)
    return re.sub(r'\s+', ' ', t).strip()

def is_duplicate_advanced(new_title, seen_titles, threshold=0.75):
    """중복 기사 판정.
    - 같은 사건을 여러 매체가 보도하는 경우(제목 유사) 중복으로 처리
    - threshold를 0.75로 올려 너무 엄격한 중복 차단 방지
    """
    new_norm = normalize_title_advanced(new_title)
    new_words = set(new_norm.split())
    if len(new_words) < 2:
        return False
    for seen in seen_titles:
        seen_norm = normalize_title_advanced(seen)
        seen_words = set(seen_norm.split())
        if not seen_words:
            continue
        if new_norm == seen_norm:
            return True
        similarity = SequenceMatcher(None, new_norm, seen_norm).ratio()
        if similarity >= threshold:
            return True
        # 단어 포함 비율도 동일하게 완화 (0.70 → 0.85)
        if len(new_words) > 0:
            intersection = len(new_words & seen_words)
            containment = intersection / len(new_words)
            if containment >= 0.85:
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
    if collection_days == 1:
        since = now - timedelta(hours=24)
    else:
        since = now - timedelta(days=collection_days)
    if collection_days == 1:
        period_label = f"{today.strftime('%m월 %d일')} 브리핑"
    else:
        start_date = (today - timedelta(days=collection_days - 1)).strftime('%m월 %d일')
        end_date = today.strftime('%m월 %d일')
        period_label = f"{start_date} ~ {end_date} 모아보기"
    return since, period_label

def fetch_articles(since):
    print(f"\n📰 뉴스 수집 중... (기준: {since.strftime('%m/%d %H:%M')} 이후)")
    articles = {"국내": [], "국외": [], "미국이란": []}
    global_seen_urls = set()
    section_seen_titles = {"국내": [], "국외": [], "미국이란": []}
    for region, feeds in RSS_FEEDS.items():
        emoji = {'국내': '🇰🇷', '국외': '🌍', '미국이란': '⚔️'}[region]
        print(f"\n  {emoji} {region} 수집 중...")
        region_count = 0
        # 국내는 구글뉴스 7개 쿼리 사용 → 더 많은 항목 탐색, 상한 15개
        max_entries = 100 if region == "국내" else 40
        region_max  = 15 if region == "국내" else 10
        for url in feeds:
            if region_count >= region_max:
                break
            try:
                feed = feedparser.parse(url)
                if not feed.entries:
                    continue
                feed_count = 0
                for entry in feed.entries[:max_entries]:
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
                    if region in ["국내", "국외"] and not is_relevant(title, summary, KEYWORDS_3D):
                        continue
                    elif region == "미국이란" and not is_relevant(title, summary, KEYWORDS_IRAN):
                        continue
                    clean_url = re.sub(r'\?.*', '', link)
                    if clean_url in global_seen_urls:
                        continue
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
                    if region_count >= region_max:
                        break
                if feed_count > 0:
                    source_name = feed.feed.get("title", url[:30])[:20]
                    print(f"    ✅ [{source_name}] {feed_count}개")
            except Exception as e:
                print(f"    ⚠️ 오류: {e}")
                continue
        print(f"  📊 {region} 최종: {region_count}개")
    return articles

def translate_titles(articles_list, model, section_name):
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
2. 한국어 번역 제목"""
    try:
        response = model.generate_content(translate_prompt)
        translated_lines = response.text.strip().split('\n')
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
                            break
    except Exception as e:
        print(f"  ⚠️ 번역 오류: {e}")
    return articles_list

def generate_briefing(articles):
    print("\n🤖 AI 브리핑 생성 중...")
    api_key = os.environ.get("GEMINI_API_KEY", "").replace('\n', '').replace('\r', '').strip()
    
    if api_key:
        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.5-flash')
            articles["국외"] = translate_titles(articles["국외"], model, "국외")
            articles["미국이란"] = translate_titles(articles["미국이란"], model, "미국이란")
            print("  ✅ 번역 완료")
        except Exception as e:
            print(f"  ⚠️ AI 오류: {e}")

    return articles

def build_html_email(period_label, articles):
    now_str = datetime.now(KST).strftime("%Y년 %m월 %d일")

    def article_card(article, idx):
        title = article.get('title', '')
        link = article.get('link', '#')
        source = article.get('source', '')
        published = article.get('published', '')
        source_clean = re.sub(r'(Google News.*|RSS.*)', '', source).strip()
        if len(source_clean) > 20:
            source_clean = source_clean[:20] + '…'

        return f"""
        <tr>
          <td style="padding:0 0 0 4px; vertical-align:top; width:18px; color:#1a73e8; font-size:13px; font-weight:700; padding-top:13px;">{idx}</td>
          <td style="padding:10px 0 10px 10px; border-bottom:1px solid #f0f0f0;">
            <a href="{link}" target="_blank" style="display:block; font-size:14px; font-weight:600; color:#1a1a1a; text-decoration:none; line-height:1.5; margin-bottom:4px; word-break:keep-all;">{title}</a>
            <span style="font-size:11px; color:#999;">{source_clean}&nbsp;&nbsp;{published}</span>
          </td>
        </tr>"""

    def section_block(emoji, title, color, articles_list, max_count):
        if not articles_list:
            items_html = '<tr><td colspan="2" style="padding:16px; color:#aaa; font-size:13px; text-align:center;">새로운 소식이 없습니다.</td></tr>'
        else:
            items_html = "".join([article_card(art, i) for i, art in enumerate(articles_list[:max_count], 1)])

        return f"""
  <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:20px; background:#fff; border-radius:12px; box-shadow:0 1px 4px rgba(0,0,0,0.08); overflow:hidden;">
    <tr>
      <td style="background:{color}; padding:12px 18px;">
        <span style="font-size:16px; font-weight:700; color:#fff; letter-spacing:-0.3px;">{emoji}&nbsp; {title}</span>
      </td>
    </tr>
    <tr>
      <td style="padding:4px 14px 4px 14px;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0">{items_html}</table>
      </td>
    </tr>
  </table>"""

    domestic_block  = section_block("🇰🇷", "국내 동향",              "#2563EB", articles["국내"],    15)  # 국내 상한 15개
    foreign_block   = section_block("🌍", "국외 동향",               "#059669", articles["국외"],    10)
    iran_block      = section_block("⚔️", "미국·이란 전쟁 관련 뉴스", "#DC2626", articles["미국이란"], 5)

    html = f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>3D프린팅 뉴스 브리핑</title>
</head>
<body style="margin:0; padding:0; background:#f4f6f9; font-family:'Apple SD Gothic Neo','Malgun Gothic','맑은 고딕',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" border="0" style="background:#f4f6f9;">
<tr><td align="center" style="padding:28px 16px 32px;">
  <table width="640" cellpadding="0" cellspacing="0" border="0" style="max-width:640px; width:100%;">
    <tr>
      <td bgcolor="#1d4ed8" style="background-color:#1d4ed8; border-radius:14px 14px 0 0; padding:28px 28px 24px; text-align:center;">
        <div style="font-size:11px; color:#93c5fd; letter-spacing:2px; text-transform:uppercase; margin-bottom:8px;">LINCSOLUTION</div>
        <div style="font-size:24px; font-weight:800; color:#ffffff; letter-spacing:-0.5px; margin-bottom:6px;">🖨️ 3D프린팅 뉴스 브리핑</div>
        <div style="font-size:13px; color:#bfdbfe;">{now_str} &nbsp;|&nbsp; 평일 오전 10시 자동발송</div>
      </td>
    </tr>
    <tr>
      <td style="background:#fff; padding:20px 28px 16px; border-left:1px solid #e8ecf0; border-right:1px solid #e8ecf0;">
        <p style="margin:0; font-size:14px; color:#444; line-height:1.7;">
          안녕하세요! 👋 &nbsp;<strong>링크솔루션 정우민</strong>입니다.<br>
          오늘의 3D프린팅 주요 뉴스를 정리해 드립니다.
        </p>
      </td>
    </tr>
    <tr>
      <td style="background:#fff; padding:0 28px 18px; border-left:1px solid #e8ecf0; border-right:1px solid #e8ecf0;">
        <div style="display:inline-block; background:#EFF6FF; border:1px solid #BFDBFE; border-radius:20px; padding:6px 16px;">
          <span style="font-size:13px; font-weight:700; color:#1d4ed8;">📅 &nbsp;{period_label}</span>
        </div>
      </td>
    </tr>
    <tr>
      <td style="background:#f4f6f9; padding:16px 16px 8px; border-left:1px solid #e8ecf0; border-right:1px solid #e8ecf0;">
        {domestic_block} {foreign_block} {iran_block}
      </td>
    </tr>
    <tr>
      <td style="background:#fff; border-top:1px solid #e8ecf0; border-radius:0 0 14px 14px; padding:22px 28px 24px; border-left:1px solid #e8ecf0; border-right:1px solid #e8ecf0; border-bottom:1px solid #e8ecf0; text-align:center;">
        <p style="margin:0 0 6px; font-size:15px; font-weight:700; color:#222;">감사합니다 😊</p>
        <p style="margin:0 0 14px; font-size:13px; color:#888;">링크솔루션 &nbsp;·&nbsp; 정우민 드림 &nbsp;(우민짱 🐱)</p>
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:16px;">
          <tr>
            <td style="text-align:center;">
              <a href="https://zerornts-arch.github.io/3dprinting-news-bot/" target="_blank" style="display:inline-block; background:#EFF6FF; border:1.5px solid #BFDBFE; border-radius:8px; padding:12px 28px; font-size:14px; font-weight:700; color:#1d4ed8; text-decoration:none; letter-spacing:-0.2px; transition:all 0.2s;">
                📚 지난 뉴스 모아보기
              </a>
            </td>
          </tr>
        </table>
        <hr style="border:none; border-top:1px solid #f0f0f0; margin:14px 0;">
        <table width="100%" cellpadding="0" cellspacing="0" border="0" style="margin-bottom:14px;">
          <tr>
            <td style="background:#FFFBEB; border:1px solid #FDE68A; border-radius:10px; padding:14px 18px; text-align:center;">
              <p style="margin:0 0 4px; font-size:13px; font-weight:700; color:#92400E;">☕ 후원 계좌</p>
              <p style="margin:0 0 2px; font-size:15px; font-weight:800; color:#78350F; letter-spacing:0.5px;">국민은행 &nbsp;051001-04-149838</p>
              <p style="margin:0; font-size:12px; color:#B45309;">작은 응원이 큰 힘이 됩니다 🙏</p>
            </td>
          </tr>
        </table>
        <p style="margin:0; font-size:11px; color:#bbb; line-height:1.6;">본 메일은 자동 발송됩니다. &nbsp;|&nbsp; 링크솔루션 3D프린팅 뉴스레터</p>
      </td>
    </tr>
  </table>
</td></tr>
</table>
</body>
</html>"""
    return html

def send_email(subject, articles, period_label):
    print("\n📧 이메일 발송 중...")
    try:
        from_addr    = os.environ.get("EMAIL_FROM", "").strip()
        raw_to       = os.environ.get("EMAIL_TO", "").strip()
        app_password = os.environ.get("EMAIL_APP_PASSWORD", "").replace(' ', '').strip()
        to_list = [e.strip() for e in raw_to.split(',') if e.strip()]

        if not from_addr or not to_list or not app_password:
            raise ValueError("이메일 설정 정보가 누락되었습니다.")

        html_body = build_html_email(period_label, articles)

        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(from_addr, app_password)
            success_count = 0
            for i, to_email in enumerate(to_list, 1):
                try:
                    msg = MIMEMultipart('alternative')
                    msg["Subject"] = Header(subject, "utf-8")
                    msg["From"]    = from_addr
                    msg["To"]      = to_email
                    msg.attach(MIMEText(html_body, 'html', 'utf-8'))
                    server.sendmail(from_addr, [to_email], msg.as_string())
                    success_count += 1
                except Exception as e:
                    print(f"    ❌ 발송 실패: {e}")

        return success_count > 0
    except Exception as e:
        return False

def save_newsletter_archive(period_label, articles):
    print("\n💾 웹사이트 아카이브 및 검색 데이터 저장 중...")
    today = date.today()
    date_str = today.strftime("%Y-%m-%d")
    filename = f"{date_str}-newsletter.md"
    filepath = Path("_posts") / filename

    # --- 1. 개별 기사 JSON 데이터 생성 및 업데이트 (검색용) ---
    search_file = Path("search.json")
    all_search_items = []
    
    # 기존 데이터 불러오기
    if search_file.exists():
        try:
            with open(search_file, 'r', encoding='utf-8') as f:
                all_search_items = json.load(f)
        except Exception:
            pass
            
    existing_links = {item.get('link') for item in all_search_items}
    
    # 새 데이터 추가
    for section_name, arts in articles.items():
        for art in arts:
            if art['link'] not in existing_links:
                all_search_items.append({
                    "title": art['title'],
                    "link": art['link'],
                    "source": re.sub(r'(Google News.*|RSS.*)', '', art.get('source', '')).strip(),
                    "date": date_str,
                    "category": section_name
                })
                
    # 최신순 정렬 및 저장
    all_search_items.sort(key=lambda x: x['date'], reverse=True)
    try:
        with open(search_file, 'w', encoding='utf-8') as f:
            json.dump(all_search_items, f, ensure_ascii=False, indent=2)
        print("  ✅ 개별 기사 검색용 데이터(search.json) 업데이트 완료")
    except Exception as e:
        print(f"  ❌ JSON 업데이트 실패: {e}")

    # --- 2. 기존 마크다운 포스트 저장 ---
    if filepath.exists():
        print(f"  📝 오늘자 아카이브가 이미 존재합니다.")
        return True

    filepath.parent.mkdir(exist_ok=True, parents=True)

    def build_section_markdown(emoji, title, articles_list, max_count):
        if not articles_list:
            return f"\n## {emoji} {title}\n\n새로운 소식이 없습니다.\n"
        lines = f"\n## {emoji} {title}\n\n"
        for i, art in enumerate(articles_list[:max_count], 1):
            art_source = re.sub(r'(Google News.*|RSS.*)', '', art.get('source', '')).strip()
            lines += f"{i}. **[{art['title']}]({art['link']})**\n"
            lines += f"   - <small>{art_source} | {art['published']}</small>\n\n"
        return lines

    domestic_md = build_section_markdown("🇰🇷", "국내 동향", articles["국내"], 15)  # 국내 상한 15개
    foreign_md = build_section_markdown("🌍", "국외 동향", articles["국외"], 10)
    iran_md = build_section_markdown("⚔️", "미국·이란 전쟁 관련 뉴스", articles["미국이란"], 5)
    now_str = datetime.now(KST).strftime("%Y년 %m월 %d일")

    jekyll_content = f"""---
layout: post
title: "3D프린팅 뉴스 브리핑 - {now_str}"
date: {date_str} 10:00:00 +0900
categories: [newsletter]
---
# 🖨️ 3D프린팅 뉴스 브리핑

> **{period_label}** | {now_str}

{domestic_md}
---
{foreign_md}
---
{iran_md}
"""
    try:
        filepath.write_text(jekyll_content, encoding="utf-8")
        return True
    except:
        return False

def main():
    now = datetime.now(KST)
    today = now.date()
    is_off, off_name = is_holiday_or_weekend(today)
    if is_off:
        return
    since, period_label = calculate_collection_period()
    articles = fetch_articles(since)
    articles = generate_briefing(articles)
    subject = f"[Lincsolution] 📅 {datetime.now(KST).strftime('%m월 %d일')} 3D프린팅 뉴스 브리핑"
    send_email(subject, articles, period_label)
    save_newsletter_archive(period_label, articles)

if __name__ == "__main__":
    main()
