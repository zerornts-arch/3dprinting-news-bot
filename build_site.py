#!/usr/bin/env python3
"""
Soft Elegant Mint — Static Site Builder
Jekyll 없이 Python으로 _posts + layouts → _site 생성
"""

import os
import re
import shutil
import yaml
from datetime import datetime
from pathlib import Path

# ── CONFIG ──────────────────────────────────────────────
BASE_DIR  = Path(__file__).parent
POSTS_DIR = BASE_DIR / "_posts"
SITE_DIR  = BASE_DIR / "_site"
ASSETS_DIR = BASE_DIR / "assets"

with open(BASE_DIR / "_config.yml", encoding="utf-8") as f:
    raw = f.read()
# strip commented lines for yaml parsing
clean = "\n".join(l for l in raw.splitlines() if not l.strip().startswith("#"))
config = yaml.safe_load(clean)

BASEURL = config.get("baseurl", "")
SITE_TITLE = config.get("title", "뉴스레터")
SITE_DESC  = config.get("description", "")

# ── HELPERS ─────────────────────────────────────────────
def parse_post(path: Path):
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)", text, re.DOTALL)
    if not m:
        return None, text
    front = yaml.safe_load(m.group(1)) or {}
    body  = m.group(2)
    return front, body

def md_to_html_simple(text: str) -> str:
    """Very light Markdown → HTML (enough for news posts)."""
    lines = text.split("\n")
    out   = []
    in_ul = False
    in_ol = False

    def close_lists():
        nonlocal in_ul, in_ol
        if in_ul:
            out.append("</ul>")
            in_ul = False
        if in_ol:
            out.append("</ol>")
            in_ol = False

    i = 0
    while i < len(lines):
        line = lines[i]

        # --- HR
        if re.match(r"^---+\s*$", line):
            close_lists()
            out.append('<hr>')
            i += 1; continue

        # --- Headings
        m = re.match(r"^(#{1,4})\s+(.*)", line)
        if m:
            close_lists()
            level = len(m.group(1))
            content = inline(m.group(2))
            out.append(f"<h{level}>{content}</h{level}>")
            i += 1; continue

        # --- Blockquote
        if line.startswith("> "):
            close_lists()
            content = inline(line[2:])
            out.append(f"<blockquote><p>{content}</p></blockquote>")
            i += 1; continue

        # --- Ordered list
        m = re.match(r"^\d+\.\s+(.*)", line)
        if m:
            if in_ul:
                out.append("</ul>"); in_ul = False
            if not in_ol:
                out.append("<ol>"); in_ol = True
            content = inline(m.group(1))
            out.append(f"  <li>{content}</li>")
            i += 1; continue

        # --- Unordered list
        if re.match(r"^[-*]\s+", line):
            if in_ol:
                out.append("</ol>"); in_ol = False
            if not in_ul:
                out.append("<ul>"); in_ul = True
            content = inline(re.sub(r"^[-*]\s+", "", line))
            out.append(f"  <li>{content}</li>")
            i += 1; continue

        # --- Empty line
        if line.strip() == "":
            close_lists()
            i += 1; continue

        # --- Normal paragraph
        close_lists()
        out.append(f"<p>{inline(line)}</p>")
        i += 1

    close_lists()
    return "\n".join(out)

def inline(text: str) -> str:
    """Inline markdown: bold, italic, code, links."""
    # code
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    # bold+italic
    text = re.sub(r"\*\*\*(.+?)\*\*\*", r"<strong><em>\1</em></strong>", text)
    # bold
    text = re.sub(r"\*\*(.+?)\*\*",     r"<strong>\1</strong>", text)
    # italic
    text = re.sub(r"\*(.+?)\*",         r"<em>\1</em>", text)
    # link: [text](url)
    text = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
                  r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)
    # small tag
    text = re.sub(r"<small>(.*?)</small>", r"<small>\1</small>", text)
    return text

def rel(path: str) -> str:
    return BASEURL + path

# ── 카테고리 분류 ───────────────────────────────────────
#
# 1차 분류: 섹션 헤더로 결정 (국내 동향 / 국외 동향 / 미국·이란 전쟁)
# 2차 분류: 기사 제목 키워드로 결정 (바이오 / 항공우주 / 산업·제조 / 소재·재료 / 소비자 제품 / 기타)
#
# 미국·이란 전쟁 섹션은 2차 분류 없이 그대로 유지

# 2차 분류 키워드 (우선순위 순)
SUB_CATEGORY_KEYWORDS = [
    ("바이오",       ["바이오", "의료", "임플란트", "세포", "연골", "뼈", "혈관", "장기", "피부",
                     "수술", "치료", "치과", "연하", "식품", "환자", "약물", "고혈압", "균사체",
                     "dental", "bio", "tissue", "scaffold"]),
    ("항공우주",     ["항공", "우주", "로켓", "위성", "drone", "무인기", "aerospace",
                     "nasa", "spacex", "로켓 랩", "rocket", "satellite"]),
    ("산업·제조",   ["산업", "제조", "공장", "생산", "부품", "금속", "자동차", "조선", "건설",
                     "군", "방산", "군사", "보병", "해군", "육군", "공군", "국방", "전투",
                     "metal", "metalfab", "양산", "라인"]),
    ("소재·재료",   ["소재", "재료", "필라멘트", "레진", "폴리머", "탄소", "실리콘", "나일론",
                     "peek", "tpu", "잉크", "분말", "수지", "세라믹", "토양",
                     "material", "powder", "resin"]),
    ("소비자 제품", ["bambu", "prusa", "creality", "formlabs", "anker",
                     "입문", "가정용", "신발", "패션", "장난감", "피규어", "슬라이서",
                     "리뷰", "비교", "데스크톱"]),
]

def classify_sub(title: str) -> str:
    """기사 제목으로 2차 세부 카테고리 반환. 해당 없으면 '기타'"""
    t = title.lower()
    for cat, keywords in SUB_CATEGORY_KEYWORDS:
        if any(kw.lower() in t for kw in keywords):
            return cat
    return "기타"

def classify_article(title: str, section: str) -> dict:
    """
    개별 기사의 1차(섹션) + 2차(키워드) 카테고리를 딕셔너리로 반환.
    반환: {"primary": "국내 동향", "sub": "바이오"}
    미국·이란 전쟁 섹션은 sub = None
    """
    # 1차: 섹션 헤더로 결정
    if "국내" in section:
        primary = "국내 동향"
    elif "국외" in section or "해외" in section:
        primary = "국외 동향"
    elif "이란" in section or "전쟁" in section or "미국" in section:
        primary = "미국·이란 전쟁"
    else:
        primary = "국내 동향"  # 폴백

    # 2차: 전쟁 섹션은 sub 없음
    if primary == "미국·이란 전쟁":
        sub = None
    else:
        sub = classify_sub(title)

    return {"primary": primary, "sub": sub}

def classify_post(body_md: str) -> list:
    """포스트 본문 전체에서 1차 카테고리 목록 추출 (포스트 필터용)"""
    cats = set()
    lines = body_md.splitlines()
    section = ""
    item_re = re.compile(r"^\d+\.\s+\*\*\[([^\]]+)\]")
    section_re = re.compile(r"^##\s+(.*)")
    for line in lines:
        line = line.strip()
        sm = section_re.match(line)
        if sm:
            section = sm.group(1)
        m = item_re.match(line)
        if m:
            result = classify_article(m.group(1), section)
            cats.add(result["primary"])
    return list(cats) if cats else ["국내 동향"]

def parse_articles(body_md: str, post_date_iso: str, post_url: str) -> list:
    """
    포스트 본문에서 개별 뉴스 기사를 파싱해 리스트로 반환.
    각 아이템: {title, url, source, section, cat, date_iso}
    형식 예)
      ## 🇰🇷 국내 동향
      1. **[제목](링크)**
         - <small>출처 | 05/21 11:05</small>
    """
    articles = []
    current_section = ""
    lines = body_md.splitlines()

    # 섹션 헤더 패턴
    section_re = re.compile(r"^##\s+(.*)")
    # 번호 기사 패턴: 1. **[제목](url)**
    item_re    = re.compile(r"^\d+\.\s+\*\*\[([^\]]+)\]\(([^)]+)\)\*\*")
    # small 태그 (출처/시간)
    small_re   = re.compile(r"<small>(.*?)</small>")

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # 섹션 감지
        m = section_re.match(line)
        if m:
            current_section = m.group(1).strip()
            i += 1
            continue

        # 기사 아이템 감지
        m = item_re.match(line)
        if m:
            art_title = m.group(1).strip()
            art_url   = m.group(2).strip()
            source    = ""

            # 다음 줄에서 <small> 출처 찾기
            if i + 1 < len(lines):
                next_line = lines[i + 1].strip()
                sm = small_re.search(next_line)
                if sm:
                    source = sm.group(1).strip()

            cat_info = classify_article(art_title, current_section)

            articles.append({
                "title":      art_title,
                "url":        art_url,
                "source":     source,
                "section":    current_section,
                "cat":        cat_info["primary"],   # 1차 (하위 호환)
                "sub":        cat_info["sub"],        # 2차 (None 가능)
                "date_iso":   post_date_iso,
                "post_url":   post_url,
            })
        i += 1

    return articles

# ── READ ALL POSTS ───────────────────────────────────────
posts    = []
articles = []   # 전체 기사 목록 (검색용)
for f in sorted(POSTS_DIR.glob("*.md"), reverse=True):
    fm, body = parse_post(f)
    if fm is None:
        continue
    # derive date from filename
    m = re.match(r"(\d{4}-\d{2}-\d{2})", f.name)
    date_str = m.group(1) if m else "2025-01-01"
    date_obj  = datetime.strptime(date_str, "%Y-%m-%d")

    slug = f.stem  # e.g. 2026-05-21-newsletter
    url  = f"{BASEURL}/{slug}/"

    auto_cats = classify_post(body)
    posts.append({
        "title":    fm.get("title", f.stem),
        "date":     date_obj,
        "date_str": date_obj.strftime("%Y년 %m월 %d일"),
        "date_iso": date_str,                         # "2026-05-21"
        "date_slash": date_obj.strftime("%m/%d"),     # "05/21"
        "date_ko":    date_obj.strftime("%m월%d일"),  # "05월21일"
        "date_ko2":   date_obj.strftime("%-m월 %-d일"), # "5월 21일"
        "url":      url,
        "slug":     slug,
        "body_md":  body,
        "body_html": md_to_html_simple(body),
        "categories": fm.get("categories", []),
        "tags":     fm.get("tags", []),
        "auto_cats": auto_cats,   # 자동 분류 카테고리 목록
    })
    # 기사 파싱 후 전역 목록에 추가
    arts = parse_articles(body, date_str, url)
    articles.extend(arts)

total = len(posts)

# ── CSS / SHARED STYLE CONTENT ───────────────────────────
css_content = (ASSETS_DIR / "css" / "mint9.css").read_text(encoding="utf-8")

def html_head(title: str, depth: int = 0) -> str:
    root = "../" * depth
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{title} — {SITE_TITLE}</title>
  <meta name="description" content="{SITE_DESC}">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Libre+Baskerville:ital,wght@0,400;0,700;1,400&display=swap" rel="stylesheet">
  <style>
{css_content}
  </style>
</head>"""

def site_header(active: str = "home", depth: int = 0) -> str:
    root = "../" * depth
    home_a  = f'class="active"' if active == "home"   else ""
    search_a= f'class="active"' if active == "search" else ""
    latest_url = posts[0]["url"] if posts else rel("/")
    return f"""
  <div class="top-bar">
    🌱 <strong>Vol.{total}</strong> — 평일 매일, 3D 프린팅 세계를 전합니다
  </div>
  <header class="site-header">
    <div class="header-inner">
      <a href="{root}index.html" class="brand">
        <div class="brand-mark">✦</div>
        <div class="brand-text">
          <div class="brand-name">우민짱의 3D 프린팅</div>
          <div class="brand-tag">뉴스레터 아카이브</div>
        </div>
      </a>
      <nav class="site-nav">
        <a href="{root}index.html" {home_a}>홈</a>
        <a href="{root}search.html" {search_a}>검색</a>
        <a href="{posts[0]['url'].lstrip('/') if posts else '#'}index.html">최신호</a>
      </nav>
      <a href="{root}search.html" class="header-cta">뉴스 검색 →</a>
    </div>
  </header>"""

def site_footer() -> str:
    year = datetime.now().year
    return f"""
  <footer class="site-footer">
    <div>© {year} <strong>{SITE_TITLE}</strong> · 자동 수집 아카이브 · 총 {total}호</div>
    <div class="footer-links">
      <a href="{rel('/index.html')}">홈</a>
      <a href="{rel('/search.html')}">아카이브 검색</a>
    </div>
  </footer>"""

# ── BUILD: INDEX ─────────────────────────────────────────
def build_index():
    latest = posts[0] if posts else {}

    # 최신호(posts[0]) 날짜의 기사 필터링
    latest_date = posts[0]["date_iso"] if posts else ""
    latest_date_str = posts[0]["date_str"] if posts else ""
    latest_articles = [a for a in articles if a["date_iso"] == latest_date]

    art_cards = ""
    for a in latest_articles:
        # 제목에서 " - 출처" 부분 제거
        dash_idx = a["title"].rfind(" - ")
        art_title = a["title"][:dash_idx] if dash_idx > 0 else a["title"]
        src_raw = a.get("source", "")
        src_label = src_raw.split("|")[0].strip() if src_raw else ""
        time_label = src_raw.split("|")[1].strip() if "|" in src_raw else latest_date_str

        primary = a.get("cat", "국내 동향")       # 1차: 국내 동향 / 국외 동향 / 미국·이란 전쟁
        sub     = a.get("sub")                     # 2차: 바이오 / 항공우주 / ... / 기타 / None

        # 1차 배지 색상
        if primary == "국내 동향":
            badge1_cls = "badge-domestic"
        elif primary == "국외 동향":
            badge1_cls = "badge-foreign"
        else:                                       # 미국·이란 전쟁
            badge1_cls = "badge-war"

        badge1_html = f'<span class="art-cat-badge {badge1_cls}">{primary}</span>'

        # 2차 배지 (전쟁 섹션은 표시 안 함)
        if sub:
            badge2_html = f'<span class="art-cat-badge art-sub-badge">{sub}</span>'
        else:
            badge2_html = ""

        art_cards += f"""
        <div class="art-card">
          <div class="art-card-top">
            <div class="art-badges">{badge1_html}{badge2_html}</div>
            <a class="art-title" href="{a['url']}" target="_blank" rel="noopener">{art_title}</a>
          </div>
          <div class="art-meta">
            <span class="art-source">📰 {src_label}</span>
            <span class="art-date">🗓 {time_label}</span>
            <a class="art-post-link" href="{a['post_url'].lstrip('/')}index.html">뉴스레터 보기 →</a>
          </div>
        </div>"""

    if not art_cards:
        art_cards = '<p style="color:var(--text-soft);padding:32px 0;">최신 기사를 불러오는 중입니다.</p>'

    html = html_head("홈") + f"""
<body>
{site_header("home")}
<main>
  <!-- HERO -->
  <section class="hero-section">
    <div class="hero-inner">
      <div class="hero-left">
        <div class="hero-eyebrow"><div class="eyebrow-line"></div>3D 프린팅 뉴스레터</div>
        <h1 class="hero-title">기술의 경계를<br><em>직접 탐험</em>하는<br>뉴스레터</h1>
        <p class="hero-desc">국내외 3D 프린팅 최신 뉴스, 업계 동향, 신제품 소식을<br>매일 자동으로 수집·아카이브합니다.</p>
        <div class="hero-actions">
          <a href="search.html" class="btn-primary">뉴스레터 검색하기 →</a>
          <a href="{latest.get('url','#').lstrip('/')}index.html" class="btn-ghost">최신호 읽기</a>
        </div>
      </div>
      <div>
        <div class="hero-card">
          <div class="hero-card-label">최신 발행호</div>
          <div class="hero-card-title">{latest.get('title','')}</div>
          <div class="hero-card-excerpt">국내외 3D 프린팅 뉴스를 한 눈에 — 매일 자동 수집되는 최신 브리핑입니다.</div>
          <div class="hero-card-divider"></div>
          <div class="hero-stats-row">
            <div class="hero-stat"><div class="hero-stat-val">{total}</div><div class="hero-stat-lbl">발행호</div></div>
            <div class="hero-stat"><div class="hero-stat-val">매일</div><div class="hero-stat-lbl">업데이트</div></div>
            <div class="hero-stat"><div class="hero-stat-val">자동</div><div class="hero-stat-lbl">수집</div></div>
          </div>
          <div class="hero-card-badge">🗓️ 최신호: {latest.get('date_str','')}</div>
        </div>
      </div>
    </div>
  </section>

  <div class="page-wrapper">
    <div class="section-header" style="margin-top:40px;">
      <div class="section-title">최신호 <span>뉴스 기사</span> <small style="font-size:.85rem;font-weight:400;color:var(--text-soft);margin-left:8px;">— {latest_date_str}</small></div>
      <a href="search.html" class="see-all">전체 아카이브 검색 →</a>
    </div>

    <div class="content-grid">
      <div>
        <div id="latest-articles">{art_cards}</div>
      </div>
      <aside class="sidebar">
        <div class="sidebar-box subscribe-box">
          <h3>뉴스레터 구독</h3>
          <p>최신 3D 프린팅 소식을 이메일로 받아보세요.</p>
          <input class="sub-input" type="email" placeholder="your@email.com">
          <button class="sub-btn">무료로 구독하기</button>
        </div>
        <div class="sidebar-box about-box">
          <div class="sidebar-title">뉴스레터 소개</div>
          <p>우민짱의 3D 프린팅 뉴스레터는 국내외 최신 3D 프린팅·적층제조 뉴스를 매일 자동으로 수집해 아카이브하는 뉴스레터입니다. 현재 <strong>{total}호</strong>까지 발행되었습니다.</p>
          <a href="search.html" class="btn-primary" style="display:block;text-align:center;margin-top:14px;font-size:.85rem;">📁 전체 아카이브 보기 →</a>
        </div>
      </aside>
    </div>
  </div>
</main>
{site_footer()}
</body>
</html>"""

    (SITE_DIR / "index.html").write_text(html, encoding="utf-8")
    print("✅ index.html 생성")

# ── BUILD: POSTS ─────────────────────────────────────────
def build_posts():
    for idx, p in enumerate(posts):
        prev_p = posts[idx + 1] if idx + 1 < len(posts) else None
        next_p = posts[idx - 1] if idx - 1 >= 0 else None

        # Recent posts sidebar
        recent_html = ""
        for rp in posts[:5]:
            weight = "700" if rp["slug"] == p["slug"] else "500"
            color  = "var(--mint-dark)" if rp["slug"] == p["slug"] else "var(--text-mid)"
            label  = rp["date"].strftime("%m/%d")
            title  = rp["title"][:30] + ("…" if len(rp["title"]) > 30 else "")
            recent_html += f"""
            <li>
              <a href="../../{rp['url'].lstrip('/')}index.html"
                 style="font-size:.83rem;font-weight:{weight};color:{color};text-decoration:none;line-height:1.4;display:block;">
                {label} — {title}
              </a>
            </li>"""

        tags_html = ", ".join(p["tags"]) if p["tags"] else "3d-printing"

        # prev/next
        prev_btn = ""
        if prev_p:
            t = prev_p["title"][:48] + ("…" if len(prev_p["title"]) > 48 else "")
            prev_btn = f"""<a href="../../{prev_p['url'].lstrip('/')}index.html" class="post-nav-item prev">
              <div class="post-nav-label">← 이전 호</div>
              <div class="post-nav-title">{t}</div>
            </a>"""
        else:
            prev_btn = "<div></div>"

        next_btn = ""
        if next_p:
            t = next_p["title"][:48] + ("…" if len(next_p["title"]) > 48 else "")
            next_btn = f"""<a href="../../{next_p['url'].lstrip('/')}index.html" class="post-nav-item next">
              <div class="post-nav-label">다음 호 →</div>
              <div class="post-nav-title">{t}</div>
            </a>"""

        html = html_head(p["title"], depth=2) + f"""
<body>
{site_header("post", depth=2)}
<main>
<div class="post-page">
  <div class="post-header">
    <div class="post-header-inner">
      <a href="../../index.html" class="post-back">← 홈으로</a>
      <div class="post-meta-row">
        <span class="post-cat-badge">뉴스레터</span>
        <span class="post-date-text">{p['date_str']}</span>
      </div>
      <h1 class="post-headline">{p['title']}</h1>
      <p class="post-subtitle">국내외 3D 프린팅 최신 소식 자동 브리핑</p>
    </div>
  </div>

  <div class="post-body-grid">
    <article class="post-content-area">
      {p['body_html']}
    </article>
    <aside class="post-sidebar">
      <div class="sidebar-box">
        <div class="sidebar-title">발행 정보</div>
        <p style="font-size:.85rem;color:var(--text-soft);line-height:1.7;">
          📅 <strong style="color:var(--mint-dark);">{p['date_str']}</strong> 발행<br>
          🏷️ {tags_html}
        </p>
      </div>
      <div class="sidebar-box">
        <div class="sidebar-title">최근 뉴스레터</div>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:10px;">{recent_html}</ul>
      </div>
      <div class="sidebar-box subscribe-box">
        <h3>뉴스레터 구독</h3>
        <p>평일 매일 오전 9시에 받아보세요.</p>
        <input class="sub-input" type="email" placeholder="your@email.com">
        <button class="sub-btn">무료 구독</button>
      </div>
    </aside>
  </div>

  <nav class="post-nav">
    {prev_btn}
    {next_btn}
  </nav>
</div>
</main>
{site_footer()}
</body>
</html>"""

        out_dir = SITE_DIR / p["url"].strip("/")
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "index.html").write_text(html, encoding="utf-8")

    print(f"✅ {total}개 포스트 페이지 생성")

# ── BUILD: SEARCH PAGE (기사 단위 검색 + 달력 UI) ────────────
def build_search():
    import json

    # 기사 전체를 JS 배열로 직렬화
    art_list = []
    for a in articles:
        art_list.append({
            "t":   a["title"],                              # 기사 제목
            "u":   a["url"],                                # 원문 URL (외부)
            "s":   a["source"],                             # 출처 (small 텍스트)
            "sec": a["section"],                            # 섹션 (국내/국외 등)
            "cat": a["cat"],                                # 1차 카테고리
            "sub": a.get("sub") or "",                      # 2차 카테고리 (없으면 빈문자열)
            "d":   a["date_iso"],                           # YYYY-MM-DD
            "pu":  a["post_url"].lstrip("/") + "index.html",# 뉴스레터 페이지
        })
    js_articles = json.dumps(art_list, ensure_ascii=False)

    # 달력에 표시할 날짜 목록 (포스트가 있는 날짜)
    post_dates = sorted({p["date_iso"] for p in posts})
    js_post_dates = json.dumps(post_dates, ensure_ascii=False)

    total_arts = len(articles)

    html = html_head("뉴스 검색") + f"""
<body>
{site_header("search")}
<main>
<div class="page-wrapper" style="padding-top:40px; padding-bottom:80px;">

  <div class="section-header" style="margin-top:0; margin-bottom:28px;">
    <div class="section-title">뉴스 기사 <span>검색</span></div>
    <span style="font-size:.82rem;color:var(--text-soft);">총 {total_arts}건의 기사 · {total}개 뉴스레터</span>
  </div>

  <!-- ── 검색 컨트롤 ── -->
  <div style="display:grid;grid-template-columns:1fr auto;gap:16px;align-items:start;margin-bottom:28px;">

    <!-- 키워드 입력 -->
    <div>
      <div style="position:relative;">
        <span style="position:absolute;left:16px;top:50%;transform:translateY(-50%);font-size:1.1rem;pointer-events:none;">🔍</span>
        <input id="q" type="text" placeholder="기사 제목 검색 (예: 바이오, 링크솔루션, 금속…)"
          style="width:100%;padding:13px 16px 13px 46px;border:1px solid var(--border);
                 border-radius:var(--radius-md);font-family:'Outfit',sans-serif;font-size:.95rem;
                 outline:none;background:white;color:var(--text);box-shadow:var(--shadow-sm);
                 transition:border-color .2s,box-shadow .2s;"
          oninput="doSearch()"
          onfocus="this.style.borderColor='var(--mint)';this.style.boxShadow='0 0 0 3px rgba(95,193,194,.15)'"
          onblur="this.style.borderColor='var(--border)';this.style.boxShadow='var(--shadow-sm)'">
      </div>
      <!-- 카테고리 필터 칩 (1차 + 2차) -->
      <div style="display:flex;gap:6px;flex-wrap:wrap;margin-top:10px;" id="cat-chips">
        <button class="tag-chip active-chip" data-cat="" onclick="setCat(this,'')">전체</button>
        <span style="width:1px;background:var(--border);margin:0 2px;"></span>
        <button class="tag-chip chip-domestic" data-cat="국내 동향"      onclick="setCat(this,'국내 동향')">🇰🇷 국내 동향</button>
        <button class="tag-chip chip-foreign"  data-cat="국외 동향"      onclick="setCat(this,'국외 동향')">🌍 국외 동향</button>
        <button class="tag-chip chip-war"      data-cat="미국·이란 전쟁" onclick="setCat(this,'미국·이란 전쟁')">⚔️ 미국·이란 전쟁</button>
        <span style="width:1px;background:var(--border);margin:0 2px;"></span>
        <button class="tag-chip chip-sub" data-cat="바이오"      onclick="setCat(this,'바이오')">바이오</button>
        <button class="tag-chip chip-sub" data-cat="항공우주"    onclick="setCat(this,'항공우주')">항공우주</button>
        <button class="tag-chip chip-sub" data-cat="산업·제조"   onclick="setCat(this,'산업·제조')">산업·제조</button>
        <button class="tag-chip chip-sub" data-cat="소재·재료"   onclick="setCat(this,'소재·재료')">소재·재료</button>
        <button class="tag-chip chip-sub" data-cat="소비자 제품" onclick="setCat(this,'소비자 제품')">소비자 제품</button>
        <button class="tag-chip chip-sub" data-cat="기타"        onclick="setCat(this,'기타')">기타</button>
      </div>
    </div>

    <!-- 달력 날짜 선택 -->
    <div style="background:white;border:1px solid var(--border);border-radius:var(--radius-lg);
                padding:18px 20px;box-shadow:var(--shadow-sm);min-width:260px;">
      <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:12px;">
        <button onclick="changeMonth(-1)" style="background:var(--mint-pale);border:1px solid var(--border);
          border-radius:6px;width:28px;height:28px;cursor:pointer;font-size:.9rem;color:var(--mint-dark);">‹</button>
        <div id="cal-header" style="font-size:.9rem;font-weight:700;color:var(--mint-dark);"></div>
        <button onclick="changeMonth(1)"  style="background:var(--mint-pale);border:1px solid var(--border);
          border-radius:6px;width:28px;height:28px;cursor:pointer;font-size:.9rem;color:var(--mint-dark);">›</button>
      </div>
      <!-- 요일 헤더 -->
      <div style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;margin-bottom:4px;">
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">일</div>
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">월</div>
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">화</div>
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">수</div>
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">목</div>
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">금</div>
        <div style="text-align:center;font-size:.68rem;color:var(--text-soft);font-weight:600;">토</div>
      </div>
      <div id="cal-grid" style="display:grid;grid-template-columns:repeat(7,1fr);gap:2px;"></div>
      <!-- 선택된 날짜 표시 -->
      <div style="margin-top:10px;padding-top:10px;border-top:1px solid var(--border-soft);
                  font-size:.78rem;color:var(--text-soft);display:flex;justify-content:space-between;align-items:center;">
        <span id="selected-date-label">날짜 전체</span>
        <button id="clear-date-btn" onclick="clearDate()"
          style="display:none;font-size:.72rem;color:var(--mint-dark);background:var(--mint-pale);
                 border:1px solid var(--border);border-radius:4px;padding:2px 8px;cursor:pointer;">
          초기화
        </button>
      </div>
    </div>
  </div>

  <!-- 결과 카운트 -->
  <div id="result-count"
    style="font-size:.83rem;color:var(--text-soft);margin-bottom:20px;padding:10px 16px;
           background:var(--mint-pale);border-radius:var(--radius-sm);display:inline-block;">
    전체 {total_arts}건의 기사를 검색할 수 있습니다
  </div>

  <!-- 결과 목록 -->
  <div id="results"></div>

</div>
</main>
{site_footer()}

<style>
/* 기사 카드 */
.art-card {{
  background: white;
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  padding: 16px 20px;
  margin-bottom: 10px;
  transition: border-color .2s, box-shadow .2s, transform .2s;
}}
.art-card:hover {{
  border-color: var(--mint);
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}}
.art-card-top {{
  display: flex;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 8px;
}}
.art-cat-badge {{
  display: inline-block;
  padding: 2px 9px;
  border-radius: 4px;
  font-size: .68rem;
  font-weight: 700;
  letter-spacing: .04em;
  white-space: nowrap;
  flex-shrink: 0;
  background: var(--mint-pale);
  color: var(--mint-dark);
  border: 1px solid var(--border);
  margin-top: 2px;
}}
.art-title {{
  font-size: .95rem;
  font-weight: 700;
  color: var(--text);
  line-height: 1.45;
  text-decoration: none;
}}
.art-title:hover {{ color: var(--mint-dark); text-decoration: underline; }}
.art-meta {{
  display: flex;
  gap: 14px;
  font-size: .75rem;
  color: var(--text-soft);
  align-items: center;
  flex-wrap: wrap;
}}
.art-source {{ color: var(--text-soft); }}
.art-date   {{ color: var(--mint-deep); font-weight: 600; }}
.art-post-link {{
  margin-left: auto;
  font-size: .72rem;
  color: var(--mint-dark);
  text-decoration: none;
  border-bottom: 1px dashed var(--mint-light);
  padding-bottom: 1px;
}}
.art-post-link:hover {{ color: var(--mint); border-color: var(--mint); }}

/* 달력 셀 */
.cal-day {{
  aspect-ratio: 1;
  display: flex; align-items: center; justify-content: center;
  border-radius: 6px;
  font-size: .78rem;
  cursor: default;
  color: var(--text-soft);
  position: relative;
}}
.cal-day.has-post {{
  background: var(--mint-pale);
  color: var(--mint-dark);
  font-weight: 700;
  cursor: pointer;
  border: 1px solid var(--border);
  transition: background .15s, border-color .15s;
}}
.cal-day.has-post:hover {{
  background: var(--mint-light);
  border-color: var(--mint);
}}
.cal-day.selected {{
  background: var(--mint-dark) !important;
  color: white !important;
  border-color: var(--mint-dark) !important;
}}
.cal-day.today {{
  border: 2px solid var(--mint) !important;
}}

/* 활성 카테고리 칩 */
.tag-chip.active-chip {{
  background: var(--mint-dark) !important;
  color: white !important;
  border-color: var(--mint-dark) !important;
}}
</style>

<script>
const ARTS       = {js_articles};
const POST_DATES = {js_post_dates};   // ["2026-05-21", ...]

// ── 상태 ──
let selectedDate = '';
let selectedCat  = '';

// ── 달력 ──
const today = new Date();
let calYear  = today.getFullYear();
let calMonth = today.getMonth(); // 0-indexed

function renderCalendar() {{
  const header = document.getElementById('cal-header');
  const grid   = document.getElementById('cal-grid');
  header.textContent = `${{calYear}}년 ${{calMonth+1}}월`;

  const firstDay = new Date(calYear, calMonth, 1).getDay(); // 0=일
  const lastDate = new Date(calYear, calMonth+1, 0).getDate();

  let html = '';
  // 빈 칸 (첫 주 앞)
  for (let i=0; i<firstDay; i++) html += '<div class="cal-day"></div>';

  for (let d=1; d<=lastDate; d++) {{
    const iso = `${{calYear}}-${{String(calMonth+1).padStart(2,'0')}}-${{String(d).padStart(2,'0')}}`;
    const hasPost = POST_DATES.includes(iso);
    const isSel   = iso === selectedDate;
    const isToday = iso === today.toISOString().slice(0,10);

    let cls = 'cal-day';
    if (hasPost) cls += ' has-post';
    if (isSel)   cls += ' selected';
    if (isToday) cls += ' today';

    const click = hasPost ? `onclick="selectDate('${{iso}}')"` : '';
    html += `<div class="${{cls}}" ${{click}} title="${{hasPost ? iso+' 뉴스레터 있음' : ''}}">${{d}}</div>`;
  }}
  grid.innerHTML = html;
}}

function changeMonth(delta) {{
  calMonth += delta;
  if (calMonth < 0)  {{ calMonth = 11; calYear--; }}
  if (calMonth > 11) {{ calMonth = 0;  calYear++; }}
  renderCalendar();
}}

function selectDate(iso) {{
  selectedDate = (selectedDate === iso) ? '' : iso; // 토글
  document.getElementById('selected-date-label').textContent =
    selectedDate ? `${{selectedDate}} 선택됨` : '날짜 전체';
  document.getElementById('clear-date-btn').style.display = selectedDate ? 'inline-block' : 'none';
  renderCalendar();
  doSearch();
}}

function clearDate() {{
  selectedDate = '';
  document.getElementById('selected-date-label').textContent = '날짜 전체';
  document.getElementById('clear-date-btn').style.display = 'none';
  renderCalendar();
  doSearch();
}}

// ── 카테고리 칩 ──
function setCat(btn, cat) {{
  document.querySelectorAll('#cat-chips .tag-chip').forEach(b => b.classList.remove('active-chip'));
  btn.classList.add('active-chip');
  selectedCat = cat;
  doSearch();
}}

// ── 검색 ──
function doSearch() {{
  const raw = document.getElementById('q').value.trim();
  const q   = raw.toLowerCase();
  const cnt = document.getElementById('result-count');
  const res = document.getElementById('results');

  const filtered = ARTS.filter(a => {{
    // 키워드 필터
    if (q && !a.t.toLowerCase().includes(q) && !a.s.toLowerCase().includes(q)) return false;
    // 카테고리 필터 (1차 or 2차 모두 매칭)
    if (selectedCat && a.cat !== selectedCat && a.sub !== selectedCat) return false;
    // 날짜 필터
    if (selectedDate && a.d !== selectedDate) return false;
    return true;
  }});

  const label = [];
  if (q)            label.push(`"${{raw}}"`);
  if (selectedCat)  label.push(selectedCat);
  if (selectedDate) label.push(selectedDate);

  cnt.textContent = label.length
    ? `${{label.join(' + ')}} 검색 결과: ${{filtered.length}}건`
    : `전체 {total_arts}건의 기사를 검색할 수 있습니다`;

  if (filtered.length === 0) {{
    res.innerHTML = `<div style="padding:48px 0;text-align:center;color:var(--text-soft);">
      <div style="font-size:2rem;margin-bottom:12px;">🔍</div>
      <div style="font-size:.95rem;">검색 결과가 없습니다.</div>
      <div style="font-size:.82rem;margin-top:8px;color:var(--mint-dark);">키워드·카테고리·날짜를 바꿔 다시 시도해보세요.</div>
    </div>`;
    return;
  }}

  res.innerHTML = filtered.map((a, i) => {{
    // 제목에서 출처 분리 ( - 매체명 )
    const dashIdx = a.t.lastIndexOf(' - ');
    const artTitle  = dashIdx > 0 ? a.t.slice(0, dashIdx) : a.t;
    const artSource = dashIdx > 0 ? a.t.slice(dashIdx+3) : (a.s || '');
    // 출처+날짜 표시용
    const srcLabel = a.s ? a.s.split('|')[0].trim() : artSource;
    const timeLabel = a.s && a.s.includes('|') ? a.s.split('|')[1].trim() : a.d;

    // 1차 배지 색상 클래스
    const badge1cls = a.cat === '국내 동향' ? 'badge-domestic'
                    : a.cat === '국외 동향' ? 'badge-foreign'
                    : 'badge-war';
    const badge1 = `<span class="art-cat-badge ${{badge1cls}}">${{a.cat}}</span>`;
    // 2차 배지 (전쟁 섹션 제외)
    const badge2 = a.sub ? `<span class="art-cat-badge art-sub-badge">${{a.sub}}</span>` : '';

    return `<div class="art-card">
      <div class="art-card-top">
        <div class="art-badges">${{badge1}}${{badge2}}</div>
        <a class="art-title" href="${{a.u}}" target="_blank" rel="noopener">${{artTitle}}</a>
      </div>
      <div class="art-meta">
        <span class="art-source">📰 ${{srcLabel || '출처 미상'}}</span>
        <span class="art-date">🗓 ${{timeLabel}}</span>
        <a class="art-post-link" href="${{a.pu}}">뉴스레터에서 보기 →</a>
      </div>
    </div>`;
  }}).join('');
}}

// ── 초기화 ──
// 가장 최신 달로 달력 이동
if (POST_DATES.length > 0) {{
  const latest = POST_DATES[POST_DATES.length - 1];
  calYear  = parseInt(latest.slice(0,4));
  calMonth = parseInt(latest.slice(5,7)) - 1;
}}
renderCalendar();
doSearch();
</script>
</body>
</html>"""

    (SITE_DIR / "search.html").write_text(html, encoding="utf-8")
    print(f"✅ search.html 생성 (기사 {len(articles)}건)")

# ── COPY ASSETS ──────────────────────────────────────────
def copy_assets():
    dest = SITE_DIR / "assets"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(ASSETS_DIR, dest)
    print("✅ assets/ 복사")

# ── MAIN ─────────────────────────────────────────────────
if __name__ == "__main__":
    if SITE_DIR.exists():
        shutil.rmtree(SITE_DIR)
    SITE_DIR.mkdir(parents=True)

    print(f"\n🏗️  빌드 시작 — {total}개 포스트\n")
    copy_assets()
    build_index()
    build_posts()
    build_search()
    print(f"\n✨ 빌드 완료! → {SITE_DIR}\n")
