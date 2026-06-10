---
layout: default
title: 뉴스레터 검색
---

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
.home-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 18px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  color: #374151;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s;
}
.home-btn:hover {
  background: #e2e8f0;
  color: #1d4ed8;
  border-color: #1d4ed8;
}
/* 💡 왼쪽 메뉴바 제목 글자 크기 조절 */
header h1 {
  font-size: 21px !important;
  letter-spacing: -0.5px;
  word-break: keep-all;
}
</style>

<!-- 🏠 홈으로 돌아가기 버튼 -->
<div style="margin-bottom: 20px;">
  <a href="{{ site.baseurl }}/" class="home-btn">
    🏠 홈으로 돌아가기
  </a>
</div>

<h1>🔍 뉴스레터 검색</h1>
<p>날짜(예: 2026-05-21) 또는 키워드(예: 바이오프린팅)로 검색하세요.</p>

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

<div id="filter-buttons" style="margin-bottom:16px;">
  <button onclick="filterSection('all')" class="filter-btn active" id="btn-all">전체</button>
  <button onclick="filterSection('국내')" class="filter-btn" id="btn-국내">🇰🇷 국내</button>
  <button onclick="filterSection('국외')" class="filter-btn" id="btn-국외">🌍 국외</button>
  <button onclick="filterSection('미국이란')" class="filter-btn" id="btn-미국이란">⚔️ 미국이란</button>
</div>

<div id="search-count" style="color:#666; margin-bottom:12px; font-size:14px;"></div>

<div id="search-results">
  <div style="text-align:center; padding:40px; color:#999;">
    <p style="font-size:15px;">검색 데이터를 불러오는 중입니다...</p>
  </div>
</div>

<script>
let allArticles = [];
let currentFilter = 'all';
let currentQuery = '';

// baseurl을 Jekyll 변수로 안전하게 처리
const baseurl = '{{ site.baseurl }}';
const jsonUrl = baseurl + '/search.json';

fetch(jsonUrl)
  .then(response => {
    if (!response.ok) throw new Error('HTTP ' + response.status);
    return response.json();
  })
  .then(data => {
    allArticles = data;
    renderResults();
  })
  .catch(error => {
    // baseurl 없이 절대경로로 재시도
    fetch('/search.json')
      .then(r => r.json())
      .then(data => {
        allArticles = data;
        renderResults();
      })
      .catch(() => {
        document.getElementById('search-results').innerHTML = 
          `<div style="text-align:center; padding:40px; color:#999;">
            <p style="font-size:15px;">검색 데이터를 불러올 수 없습니다.</p>
            <p style="font-size:13px;">main.py를 실행하면 search.json이 생성됩니다! ⚙️</p>
          </div>`;
      });
  });

function performSearch() {
  currentQuery = document.getElementById('search-input').value.trim().toLowerCase();
  renderResults();
}

function filterSection(section) {
  currentFilter = section;
  document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
  document.getElementById('btn-' + section).classList.add('active');
  renderResults();
}

function highlight(text, query) {
  if (!query) return text;
  const escaped = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const regex = new RegExp(`(${escaped})`, 'gi');
  return text.replace(regex, '<mark style="background:#FEF08A; padding:1px 2px; border-radius:3px;">$1</mark>');
}

function renderResults() {
  const resultsDiv = document.getElementById('search-results');
  const countDiv = document.getElementById('search-count');
  
  let filtered = allArticles.filter(article => {
    const matchSection = currentFilter === 'all' || article.category === currentFilter;
    const matchQuery = !currentQuery || 
      article.title.toLowerCase().includes(currentQuery) ||
      article.date.includes(currentQuery) ||
      (article.source && article.source.toLowerCase().includes(currentQuery));
    return matchSection && matchQuery;
  });
  
  if (!currentQuery && currentFilter === 'all') {
    countDiv.innerHTML = `총 <strong>${allArticles.length}개</strong>의 뉴스 기사가 아카이브되어 있습니다.`;
  } else {
    countDiv.innerHTML = `<strong>${filtered.length}개</strong>의 결과를 찾았습니다.`;
  }
  
  if (filtered.length === 0) {
    resultsDiv.innerHTML = `
      <div style="text-align:center; padding:40px; color:#999;">
        <div style="font-size:48px; margin-bottom:12px;">🔍</div>
        <p style="font-size:16px;">"<strong>${currentQuery}</strong>"에 대한 결과가 없습니다.</p>
        <p style="font-size:14px;">다른 키워드로 검색해보세요.</p>
      </div>`;
    return;
  }
  
  resultsDiv.innerHTML = filtered.map(article => {
    let emoji = article.category === '국내' ? '🇰🇷' : article.category === '국외' ? '🌍' : '⚔️';
    
    return `
      <div style="background:#fff; border:1px solid #e5e7eb; border-radius:10px;
                  padding:18px 20px; margin-bottom:14px;
                  box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <div style="font-size:12px; color:#6b7280; margin-bottom:6px;">
          ${emoji} ${article.category} | 📅 ${highlight(article.date, currentQuery)}
        </div>
        <a href="${article.link}" target="_blank" 
           style="font-size:17px; font-weight:700; color:#1d4ed8;
                  text-decoration:none; line-height:1.4; display:block; margin-bottom:8px;">
          ${highlight(article.title, currentQuery)}
        </a>
        <p style="font-size:13px; color:#6b7280; line-height:1.6; margin:0;">
          출처: ${highlight(article.source || '', currentQuery)}
        </p>
      </div>`;
  }).join('');
}
</script>
