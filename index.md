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
      <div class="hero-actions">
        <a href="{{ '/search.html' | relative_url }}" class="btn-primary">뉴스레터 검색하기 →</a>
      </div>
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
     MAIN CONTENT
     ════════════════════════════════════════ -->
<div class="page-wrapper">

  <!-- SECTION TITLE + LIST/SIDEBAR GRID -->
  <div class="section-header" style="margin-top:48px;">
    <div class="section-title">전체 <span>아카이브</span></div>
    <a href="{{ '/search.html' | relative_url }}" class="see-all">검색으로 찾기 →</a>
  </div>

  <div class="content-grid">

    <!-- POST LIST -->
    <div>
      <ul class="post-list">
        {% for post in site.posts %}
        <li>
          <a href="{{ post.url | relative_url }}" class="post-list-item{% if forloop.first %} post-list-item--latest{% endif %}">
            {% if forloop.first %}
            <div class="post-latest-badge">최신호</div>
            {% endif %}
            <div class="post-num">{{ forloop.index | prepend: '00' | slice: -2, 2 }}</div>
            <div class="post-content">
              <div class="post-category">뉴스레터</div>
              <div class="post-title">{{ post.title }}</div>
              <div class="post-excerpt">
                국내외 3D 프린팅 최신 소식 — {{ post.date | date: "%Y년 %m월 %d일" }} 브리핑
              </div>
              <div class="post-date">{{ post.date | date: "%Y년 %m월 %d일" }}</div>
            </div>
          </a>
        </li>
        {% endfor %}
      </ul>
    </div>

    <!-- SIDEBAR -->
    <aside class="sidebar">

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
/* 최신호 강조 */
.post-list-item--latest {
  position: relative;
  background: var(--mint-pale2);
  border-left: 3px solid var(--mint);
  border-radius: var(--radius-sm);
  padding-left: 16px !important;
}
.post-list-item--latest .post-title {
  color: var(--mint-dark);
}
.post-list-item--latest .post-num {
  color: var(--mint-light);
}
.post-latest-badge {
  position: absolute;
  top: 20px;
  right: 16px;
  background: var(--mint-dark);
  color: white;
  font-size: .65rem;
  font-weight: 700;
  letter-spacing: .06em;
  padding: 3px 8px;
  border-radius: 4px;
  text-transform: uppercase;
}
@media (max-width: 600px) {
  .post-latest-badge { font-size: .6rem; padding: 2px 6px; }
}
</style>
