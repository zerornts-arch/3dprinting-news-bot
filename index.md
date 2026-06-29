---
layout: default
title: 홈
---

<!-- ════════════════════════════════════════
     HERO SECTION
     ════════════════════════════════════════ -->
<section class="hero-section">
  <div class="hero-inner">

    <!-- LEFT: Text -->
    <div class="hero-left">
      <div class="hero-eyebrow">
        <div class="eyebrow-line"></div>
        3D 프린팅 뉴스레터
      </div>
      <h1 class="hero-title">
        기술의 경계를<br>
        <em>직접 탐험</em>하는<br>
        뉴스레터
      </h1>
      <p class="hero-desc">
        국내외 3D 프린팅 최신 뉴스, 업계 동향, 신제품 소식을<br>
        매일 자동으로 수집·아카이브합니다.
      </p>

    </div>

    <!-- RIGHT: Stats Card -->
    <div>
      <div class="hero-card">
        <div class="hero-card-label">이번 주 하이라이트</div>
        {% assign latest = site.posts.first %}
        <div class="hero-card-title">{{ latest.title }}</div>
        <div class="hero-card-excerpt">
          국내외 3D 프린팅 뉴스를 한 눈에 — 매일 자동 수집되는 최신 브리핑입니다.
        </div>
        <div class="hero-card-divider"></div>
        <div class="hero-stats-row">
          <div class="hero-stat">
            <div class="hero-stat-val">{{ site.posts.size }}</div>
            <div class="hero-stat-lbl">발행호</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-val">매일</div>
            <div class="hero-stat-lbl">업데이트</div>
          </div>
          <div class="hero-stat">
            <div class="hero-stat-val">자동</div>
            <div class="hero-stat-lbl">수집</div>
          </div>
        </div>
        <div class="hero-card-badge">
          🗓️ 최신호: {{ latest.date | date: "%Y년 %m월 %d일" }}
        </div>
      </div>
    </div>

  </div>
</section>

<!-- ════════════════════════════════════════
     MAIN CONTENT - 최신호 전체 본문
     ════════════════════════════════════════ -->
<div class="page-wrapper">

  {% assign latest = site.posts.first %}

  <!-- 최신호 헤더 -->
  <div class="latest-header">
    <div class="latest-badge-wrap">
      <span class="latest-live-badge">● LATEST</span>
      <span class="latest-date">{{ latest.date | date: "%Y년 %m월 %d일" }}</span>
    </div>
    <div class="latest-title-row">
      <h2 class="latest-title">{{ latest.title }}</h2>
      <a href="{{ '/search.html' | relative_url }}" class="see-all">전체 아카이브 검색 →</a>
    </div>
  </div>

  <!-- 최신호 본문 전체 렌더링 -->
  <div class="content-grid">
    <div class="latest-content-area">
      {{ latest.content }}
    </div>

    <!-- SIDEBAR -->
    <aside class="sidebar">

      <!-- 아카이브 목록 -->
      <div class="sidebar-box">
        <div class="sidebar-title">전체 아카이브</div>
        <ul style="list-style:none;display:flex;flex-direction:column;gap:10px;">
          {% for post in site.posts limit:10 %}
          <li>
            <a href="{{ post.url | relative_url }}"
               style="font-size:.83rem;font-weight:{% if forloop.first %}700{% else %}500{% endif %};
                      color:{% if forloop.first %}var(--mint-dark){% else %}var(--text-mid){% endif %};
                      text-decoration:none;line-height:1.4;display:flex;align-items:center;gap:6px;transition:color .2s;"
               onmouseover="this.style.color='var(--mint-dark)'"
               onmouseout="this.style.color='{% if forloop.first %}var(--mint-dark){% else %}var(--text-mid){% endif %}'">
              {% if forloop.first %}<span style="background:var(--mint-dark);color:#fff;font-size:.6rem;padding:1px 5px;border-radius:3px;font-weight:700;flex-shrink:0;">최신</span>{% endif %}
              {{ post.date | date: "%m/%d" }} — {{ post.title | truncate: 28 }}
            </a>
          </li>
          {% endfor %}
        </ul>
        {% if site.posts.size > 10 %}
        <a href="{{ '/search.html' | relative_url }}" style="display:block;margin-top:12px;font-size:.8rem;color:var(--mint-dark);font-weight:600;text-decoration:none;">전체 {{ site.posts.size }}호 보기 →</a>
        {% endif %}
      </div>

      <!-- ABOUT -->
      <div class="sidebar-box about-box">
        <div class="sidebar-title">뉴스레터 소개</div>
        <p>
          우민짱의 3D 프린팅 뉴스레터는 국내외 최신 3D 프린팅·적층제조 뉴스를 매일 자동으로 수집해 아카이브하는 뉴스레터입니다. 현재 <strong>{{ site.posts.size }}호</strong>까지 발행되었습니다.
        </p>
      </div>

    </aside>
  </div>

</div>

<style>
/* ── 최신호 헤더 ── */
.latest-header {
  margin-top: 48px;
  margin-bottom: 28px;
}
.latest-badge-wrap {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 10px;
}
.latest-live-badge {
  background: var(--mint-dark);
  color: #fff;
  font-size: .7rem;
  font-weight: 800;
  letter-spacing: .08em;
  padding: 4px 10px;
  border-radius: 4px;
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.latest-date {
  font-size: .85rem;
  color: var(--text-soft);
  font-weight: 500;
}
.latest-title-row {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.latest-title {
  font-size: 1.4rem;
  font-weight: 800;
  color: var(--text);
  letter-spacing: -.02em;
  line-height: 1.3;
}

/* ── 최신호 본문 영역 ── */
.latest-content-area {
  min-width: 0;
  background: var(--white);
  border: 1px solid var(--border);
  border-radius: var(--radius-lg);
  padding: 32px 36px;
  box-shadow: var(--shadow-sm);
}

/* 본문 내 마크다운 스타일 (post-content-area 와 동일하게) */
.latest-content-area h1,
.latest-content-area h2,
.latest-content-area h3,
.latest-content-area h4 {
  color: var(--text);
  line-height: 1.35;
  margin: 28px 0 12px;
  font-weight: 700;
}
.latest-content-area h1 { font-size: 1.5rem; }
.latest-content-area h2 {
  font-size: 1.1rem;
  padding: 10px 16px;
  background: var(--mint-pale);
  border-left: 3px solid var(--mint);
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  margin-top: 32px;
}
.latest-content-area h3 { font-size: 1rem; color: var(--mint-dark); }
.latest-content-area h4 { font-size: .95rem; }

.latest-content-area p {
  font-size: .93rem;
  color: var(--text-mid);
  line-height: 1.8;
  margin: 0 0 14px;
}
.latest-content-area blockquote {
  border-left: 3px solid var(--mint);
  background: var(--mint-pale);
  padding: 12px 16px;
  border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
  margin: 16px 0;
  font-style: italic;
  color: var(--text-mid);
  font-size: .9rem;
}
.latest-content-area a {
  color: var(--mint-dark);
  text-decoration: underline;
  text-decoration-color: var(--mint-light);
  text-underline-offset: 3px;
  transition: color .2s;
}
.latest-content-area a:hover { color: var(--mint); }
.latest-content-area ul,
.latest-content-area ol {
  margin: 0 0 14px 20px;
}
.latest-content-area li {
  font-size: .9rem;
  color: var(--text-mid);
  line-height: 1.75;
  margin-bottom: 8px;
}
.latest-content-area li strong { color: var(--text); }
.latest-content-area li > strong > a {
  color: var(--mint-dark);
  font-weight: 700;
}
.latest-content-area li > strong > a:hover { color: var(--mint); }
.latest-content-area strong { color: var(--text); font-weight: 700; }
.latest-content-area hr {
  border: none;
  border-top: 1px solid var(--border);
  margin: 28px 0;
}
.latest-content-area small {
  font-size: .75rem;
  color: var(--text-soft);
}

@media (max-width: 600px) {
  .latest-content-area { padding: 20px 18px; }
  .latest-title { font-size: 1.15rem; }
}
</style>
