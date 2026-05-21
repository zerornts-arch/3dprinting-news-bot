---
layout: default
title: 뉴스레터 검색
---

<h1>🔍 뉴스레터 검색</h1>
<p>날짜(예: 2026-05-21) 또는 키워드(예: 바이오프린팅)로 검색하세요.</p>

<!-- 검색 입력창 -->
<div style="margin: 20px 0;">
  <input
    type="text"
    id="search-input"
    placeholder="🔍 날짜 또는 키워드 입력..."
    style="width:100%; padding:12px 16px; font-size:16px;
           border:2px solid #1d4ed8; border-radius:8px;
           box-sizing:border-box; outline:none;"
    oninput="performSearch()"
  />
</div>

<!-- 필터 버튼 -->
<div id="filter-buttons" style="margin-bottom:16px;">
  <button onclick="filterSection('all')" class="filter-btn active" id="btn-all">전체</button>
  <button onclick="filterSection('국내')" class="filter-btn" id="btn-국내">🇰🇷 국내</button>
  <button onclick="filterSection('국외')" class="filter-btn" id="btn-국외">🌍 국외</button>
  <button onclick="filterSection('미국이란')" class="filter-btn" id="btn-미국이란">⚔️ 미국이란</button>
</div>

<!-- 검색 결과 수 -->
<div id="search-count" style="color:#666; margin-bottom:12px; font-size:14px;"></div>

<!-- 검색 결과 목록 -->
<div id="search-results"></div>

<!-- 전체 포스트 데이터 (Jekyll이 자동 생성) -->
<script>
const allPosts = [
  {% for post in site.posts %}
  {
    title: {{ post.title | jsonify }},
    url: "{{ post.url | relative_url }}",
    date: "{{ post.date | date: '%Y-%m-%d' }}",
    dateKor: "{{ post.date | date: '%Y년 %m월 %d일' }}",
    content: {{ post.content | strip_html | truncate: 2000 | jsonify }}
  }{% unless forloop.last %},{% endunless %}
  {% endfor %}
];

let currentFilter = 'all';
let currentQuery = '';

function performSearch() {
  currentQuery = document.getElementById('search-input').value.trim().toLowerCase();
  renderResults();
}

function filterSection(section) {
  currentFilter = section;
  
  // 버튼 활성화 스타일 변경
  document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById('btn-' + section).classList.add('active');
  
  renderResults();
}

function highlight(text, query) {
  if (!query) return text;
  const regex = new RegExp(`(${query})`, 'gi');
  return text.replace(regex, '<mark style="background:#FEF08A; padding:1px 2px; border-radius:3px;">$1</mark>');
}

function renderResults() {
  const resultsDiv = document.getElementById('search-results');
  const countDiv = document.getElementById('search-count');
  
  // 필터링
  let filtered = allPosts.filter(post => {
    const matchSection = currentFilter === 'all' || post.content.includes(currentFilter);
    const matchQuery = !currentQuery || 
      post.title.toLowerCase().includes(currentQuery) ||
      post.content.toLowerCase().includes(currentQuery) ||
      post.date.includes(currentQuery);
    return matchSection && matchQuery;
  });
  
  // 검색어 없을 때 전체 목록 표시
  if (!currentQuery && currentFilter === 'all') {
    countDiv.innerHTML = `총 <strong>${allPosts.length}개</strong>의 뉴스레터가 아카이브되어 있습니다.`;
  } else {
    countDiv.innerHTML = `<strong>${filtered.length}개</strong>의 결과를 찾았습니다.`;
  }
  
  // 결과 없을 때
  if (filtered.length === 0) {
    resultsDiv.innerHTML = `
      <div style="text-align:center; padding:40px; color:#999;">
        <div style="font-size:48px; margin-bottom:12px;">🔍</div>
        <p style="font-size:16px;">"<strong>${currentQuery}</strong>"에 대한 결과가 없습니다.</p>
        <p style="font-size:14px;">다른 키워드로 검색해보세요.</p>
      </div>`;
    return;
  }
  
  // 결과 카드 생성
  resultsDiv.innerHTML = filtered.map(post => {
    // 검색어 주변 내용 미리보기 생성
    let preview = '';
    if (currentQuery && post.content.toLowerCase().includes(currentQuery)) {
      const idx = post.content.toLowerCase().indexOf(currentQuery);
      const start = Math.max(0, idx - 60);
      const end = Math.min(post.content.length, idx + 120);
      preview = '...' + post.content.substring(start, end) + '...';
    } else {
      preview = post.content.substring(0, 150) + '...';
    }
    
    return `
      <div style="background:#fff; border:1px solid #e5e7eb; border-radius:10px;
                  padding:18px 20px; margin-bottom:14px;
                  box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <div style="font-size:12px; color:#6b7280; margin-bottom:6px;">
          📅 ${highlight(post.dateKor, currentQuery)}
        </div>
        <a href="${post.url}" 
           style="font-size:17px; font-weight:700; color:#1d4ed8;
                  text-decoration:none; line-height:1.4; display:block; margin-bottom:8px;">
          ${highlight(post.title, currentQuery)}
        </a>
        <p style="font-size:13px; color:#6b7280; line-height:1.6; margin:0;">
          ${highlight(preview, currentQuery)}
        </p>
      </div>`;
  }).join('');
}

// 페이지 로드 시 전체 목록 표시
renderResults();
</script>

<!-- 스타일 -->
<style>
.filter-btn {
  padding: 7px 16px;
  margin: 0 6px 8px 0;
  border: 1px solid #d1d5db;
  border-radius: 20px;
  background: #fff;
  color: #374151;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}
.filter-btn:hover {
  border-color: #1d4ed8;
  color: #1d4ed8;
}
.filter-btn.active {
  background: #1d4ed8;
  color: #fff;
  border-color: #1d4ed8;
}
#search-input:focus {
  border-color: #1d4ed8;
  box-shadow: 0 0 0 3px rgba(29,78,216,0.15);
}
</style>
