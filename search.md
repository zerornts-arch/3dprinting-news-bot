---
layout: default
title: 뉴스레터 검색
---

<style>
/* ── 공통 ── */
header h1 {
  font-size: 21px !important;
  letter-spacing: -0.5px;
  word-break: keep-all;
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
  background: var(--mint-pale);
  color: var(--mint-dark);
  border-color: var(--mint);
}

/* ── 탭 ── */
.tab-wrap {
  display: flex;
  gap: 0;
  border: 2px solid var(--mint-dark);
  border-radius: 10px;
  overflow: hidden;
  margin: 20px 0 24px;
}
.tab-btn {
  flex: 1;
  padding: 12px 0;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  border: none;
  background: #fff;
  color: var(--mint-dark);
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}
.tab-btn.active {
  background: var(--mint-dark);
  color: #fff;
}
.tab-btn:first-child {
  border-right: 2px solid var(--mint-dark);
}

/* ── 검색 패널 ── */
.search-panel { display: none; }
.search-panel.active { display: block; }

/* ── 키워드 입력 ── */
#keyword-input {
  width: 100%;
  padding: 12px 16px;
  font-size: 16px;
  border: 2px solid var(--mint-dark);
  border-radius: 8px;
  box-sizing: border-box;
  outline: none;
  transition: box-shadow 0.2s;
}
#keyword-input:focus {
  box-shadow: 0 0 0 3px rgba(95,193,194,0.25);
}

/* ── 달력 ── */
.cal-wrap {
  background: #fff;
  border: 2px solid var(--mint-dark);
  border-radius: 12px;
  overflow: hidden;
  user-select: none;
}
.cal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: var(--mint-dark);
  padding: 14px 18px;
}
.cal-header span {
  font-size: 16px;
  font-weight: 800;
  color: #fff;
  letter-spacing: -0.3px;
}
.cal-nav {
  background: none;
  border: none;
  color: #fff;
  font-size: 20px;
  cursor: pointer;
  padding: 0 6px;
  line-height: 1;
  border-radius: 6px;
  transition: background 0.15s;
}
.cal-nav:hover { background: rgba(255,255,255,0.2); }
.cal-grid {
  display: grid;
  grid-template-columns: repeat(7, 1fr);
  gap: 0;
}
.cal-dow {
  text-align: center;
  padding: 10px 0 6px;
  font-size: 12px;
  font-weight: 700;
  color: #6b7280;
  background: #f8fafc;
}
.cal-dow:first-child { color: #ef4444; }
.cal-dow:last-child  { color: #3b82f6; }
.cal-day {
  text-align: center;
  padding: 9px 4px;
  font-size: 13px;
  cursor: pointer;
  border-radius: 6px;
  margin: 2px;
  transition: all 0.15s;
  color: #374151;
  position: relative;
}
.cal-day:hover:not(.empty):not(.no-data) {
  background: var(--mint-pale);
  color: var(--mint-dark);
  font-weight: 700;
}
.cal-day.has-data {
  font-weight: 700;
  color: var(--mint-dark);
}
.cal-day.has-data::after {
  content: '';
  display: block;
  width: 5px;
  height: 5px;
  background: var(--mint-dark);
  border-radius: 50%;
  margin: 2px auto 0;
}
.cal-day.selected {
  background: var(--mint-dark) !important;
  color: #fff !important;
  font-weight: 700;
}
.cal-day.selected::after {
  background: #fff !important;
}
.cal-day.empty, .cal-day.no-data {
  cursor: default;
  color: #d1d5db;
}
.cal-day.today {
  background: var(--mint-pale);
  font-weight: 700;
}
.cal-day.sunday { color: #ef4444; }
.cal-day.saturday { color: #3b82f6; }
.cal-day.sunday.has-data { color: #ef4444; }
.cal-day.saturday.has-data { color: #3b82f6; }
.cal-day.has-data.sunday { color: #ef4444; }
.cal-day.has-data.saturday { color: #3b82f6; }
.cal-day.selected.sunday,
.cal-day.selected.saturday { color: #fff !important; }

/* 날짜 선택 표시 배지 */
.date-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  background: var(--mint-pale);
  border: 1.5px solid var(--mint-light);
  border-radius: 20px;
  padding: 6px 14px;
  font-size: 14px;
  font-weight: 700;
  color: var(--mint-dark);
  margin-top: 12px;
}
.date-badge-clear {
  cursor: pointer;
  color: #93c5fd;
  font-size: 16px;
  line-height: 1;
  font-weight: 900;
  transition: color 0.15s;
}
.date-badge-clear:hover { color: #ef4444; }

/* ── 카테고리 필터 ── */
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
.filter-btn:hover  { border-color: var(--mint-dark); color: var(--mint-dark); }
.filter-btn.active { background: var(--mint-dark); color: #fff; border-color: var(--mint-dark); }
</style>

<!-- 홈 버튼 -->
<div style="margin-bottom:18px;">
  <a href="{{ site.baseurl }}/" class="home-btn">🏠 홈으로 돌아가기</a>
</div>

<h1>🔍 뉴스레터 검색</h1>

<!-- ── 탭 전환 ── -->
<div class="tab-wrap">
  <button class="tab-btn active" id="tab-keyword" onclick="switchTab('keyword')">
    🔤 키워드로 검색
  </button>
  <button class="tab-btn" id="tab-date" onclick="switchTab('date')">
    📅 날짜로 검색
  </button>
</div>

<!-- ── 키워드 검색 패널 ── -->
<div class="search-panel active" id="panel-keyword">
  <input
    type="text"
    id="keyword-input"
    placeholder="검색어를 입력하세요 (예: 바이오프린팅, Formlabs ...)"
    oninput="onKeywordInput()"
    autocomplete="off"
  />
</div>

<!-- ── 날짜 검색 패널 ── -->
<div class="search-panel" id="panel-date">
  <div class="cal-wrap">
    <div class="cal-header">
      <button class="cal-nav" onclick="moveMonth(-1)">&#8249;</button>
      <span id="cal-title"></span>
      <button class="cal-nav" onclick="moveMonth(1)">&#8250;</button>
    </div>
    <div class="cal-grid" id="cal-dow-row">
      <div class="cal-dow">일</div>
      <div class="cal-dow">월</div>
      <div class="cal-dow">화</div>
      <div class="cal-dow">수</div>
      <div class="cal-dow">목</div>
      <div class="cal-dow">금</div>
      <div class="cal-dow">토</div>
    </div>
    <div class="cal-grid" id="cal-body"></div>
  </div>
  <div id="date-badge-wrap"></div>
</div>

<!-- ── 카테고리 필터 ── -->
<div style="margin-top:20px; margin-bottom:10px;">
  <div id="filter-buttons">
    <button onclick="filterSection('all')"   class="filter-btn active" id="btn-all">전체</button>
    <button onclick="filterSection('국내')"  class="filter-btn" id="btn-국내">🇰🇷 국내</button>
    <button onclick="filterSection('국외')"  class="filter-btn" id="btn-국외">🌍 국외</button>
    <button onclick="filterSection('미국이란')" class="filter-btn" id="btn-미국이란">⚔️ 미국이란</button>
  </div>
</div>

<div id="search-count" style="color:#666; margin-bottom:12px; font-size:14px;"></div>
<div id="search-results">
  <div style="text-align:center; padding:40px; color:#999;">
    <p style="font-size:15px;">검색 데이터를 불러오는 중입니다...</p>
  </div>
</div>

<script>
/* ════════════════════════════════
   데이터 로딩
════════════════════════════════ */
let allArticles = [];
let currentFilter = 'all';
let currentKeyword = '';
let currentDate = '';   // 'YYYY-MM-DD' 또는 ''
let activeTab = 'keyword';

const baseurl = '{{ site.baseurl }}';

fetch(baseurl + '/search.json')
  .then(r => { if (!r.ok) throw new Error(r.status); return r.json(); })
  .then(init)
  .catch(() =>
    fetch('/search.json')
      .then(r => r.json())
      .then(init)
      .catch(() => {
        document.getElementById('search-results').innerHTML =
          `<div style="text-align:center;padding:40px;color:#999;">
             <p style="font-size:15px;">검색 데이터를 불러올 수 없습니다.</p>
             <p style="font-size:13px;">main.py 실행 후 다시 시도해주세요 ⚙️</p>
           </div>`;
      })
  );

function init(data) {
  allArticles = data;
  buildCalendar();
  renderResults();
}

/* ════════════════════════════════
   탭 전환
════════════════════════════════ */
function switchTab(tab) {
  activeTab = tab;
  document.getElementById('tab-keyword').classList.toggle('active', tab === 'keyword');
  document.getElementById('tab-date').classList.toggle('active', tab === 'date');
  document.getElementById('panel-keyword').classList.toggle('active', tab === 'keyword');
  document.getElementById('panel-date').classList.toggle('active', tab === 'date');

  // 반대 탭의 검색값 초기화
  if (tab === 'keyword') {
    currentDate = '';
    document.getElementById('date-badge-wrap').innerHTML = '';
    renderCalendar();          // 달력 선택 해제
  } else {
    currentKeyword = '';
    document.getElementById('keyword-input').value = '';
  }
  renderResults();
}

/* ════════════════════════════════
   키워드 검색
════════════════════════════════ */
function onKeywordInput() {
  currentKeyword = document.getElementById('keyword-input').value.trim().toLowerCase();
  renderResults();
}

/* ════════════════════════════════
   달력
════════════════════════════════ */
let calYear, calMonth;   // 현재 달력에 표시 중인 연/월

function buildCalendar() {
  const now = new Date();
  calYear  = now.getFullYear();
  calMonth = now.getMonth();   // 0-based
  renderCalendar();
}

// 데이터에 실제 존재하는 날짜 세트
function getDataDates() {
  return new Set(allArticles.map(a => a.date));
}

function moveMonth(delta) {
  calMonth += delta;
  if (calMonth > 11) { calMonth = 0;  calYear++; }
  if (calMonth < 0)  { calMonth = 11; calYear--; }
  renderCalendar();
}

function renderCalendar() {
  const dataDates = getDataDates();
  const today = new Date();
  const todayStr = toDateStr(today.getFullYear(), today.getMonth() + 1, today.getDate());

  document.getElementById('cal-title').textContent =
    `${calYear}년 ${String(calMonth + 1).padStart(2,'0')}월`;

  const firstDay = new Date(calYear, calMonth, 1).getDay(); // 0=일
  const lastDate = new Date(calYear, calMonth + 1, 0).getDate();

  let html = '';

  // 앞쪽 빈칸
  for (let i = 0; i < firstDay; i++) {
    html += `<div class="cal-day empty"></div>`;
  }

  for (let d = 1; d <= lastDate; d++) {
    const ds = toDateStr(calYear, calMonth + 1, d);
    const dow = (firstDay + d - 1) % 7;   // 0=일, 6=토
    const hasData  = dataDates.has(ds);
    const isToday  = ds === todayStr;
    const isSel    = ds === currentDate;
    const isSun    = dow === 0;
    const isSat    = dow === 6;

    let cls = 'cal-day';
    if (!hasData)  cls += ' no-data';
    if (hasData)   cls += ' has-data';
    if (isToday)   cls += ' today';
    if (isSel)     cls += ' selected';
    if (isSun)     cls += ' sunday';
    if (isSat)     cls += ' saturday';

    const click = hasData ? `onclick="selectDate('${ds}')"` : '';
    html += `<div class="${cls}" ${click}>${d}</div>`;
  }

  document.getElementById('cal-body').innerHTML = html;
}

function toDateStr(y, m, d) {
  return `${y}-${String(m).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
}

function selectDate(ds) {
  if (currentDate === ds) {
    // 같은 날짜 재클릭 → 선택 해제
    currentDate = '';
    document.getElementById('date-badge-wrap').innerHTML = '';
  } else {
    currentDate = ds;
    // 날짜 배지
    document.getElementById('date-badge-wrap').innerHTML =
      `<div class="date-badge">
         📅 ${ds} 뉴스
         <span class="date-badge-clear" onclick="clearDate()" title="선택 해제">✕</span>
       </div>`;
  }
  renderCalendar();
  renderResults();
}

function clearDate() {
  currentDate = '';
  document.getElementById('date-badge-wrap').innerHTML = '';
  renderCalendar();
  renderResults();
}

/* ════════════════════════════════
   카테고리 필터
════════════════════════════════ */
function filterSection(section) {
  currentFilter = section;
  document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('btn-' + section).classList.add('active');
  renderResults();
}

/* ════════════════════════════════
   하이라이트
════════════════════════════════ */
function highlight(text, query) {
  if (!query || !text) return text || '';
  const esc = query.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  return text.replace(new RegExp(`(${esc})`, 'gi'),
    '<mark style="background:#FEF08A;padding:1px 2px;border-radius:3px;">$1</mark>');
}

/* ════════════════════════════════
   결과 렌더링
════════════════════════════════ */
function renderResults() {
  const resultsDiv = document.getElementById('search-results');
  const countDiv   = document.getElementById('search-count');

  const query = activeTab === 'keyword' ? currentKeyword : '';
  const dateFilter = activeTab === 'date' ? currentDate : '';

  const filtered = allArticles.filter(a => {
    const matchCat  = currentFilter === 'all' || a.category === currentFilter;
    const matchQ    = !query ||
      a.title.toLowerCase().includes(query);
    const matchDate = !dateFilter || a.date === dateFilter;
    return matchCat && matchQ && matchDate;
  });

  // 카운트 문구
  const isDefault = !query && !dateFilter && currentFilter === 'all';
  countDiv.innerHTML = isDefault
    ? `총 <strong>${allArticles.length}개</strong>의 뉴스 기사가 아카이브되어 있습니다.`
    : `<strong>${filtered.length}개</strong>의 결과를 찾았습니다.`;

  // 결과 없음
  if (filtered.length === 0) {
    const msg = dateFilter
      ? `${dateFilter} 날짜의 뉴스가 없습니다.`
      : query
        ? `"<strong>${query}</strong>"에 대한 결과가 없습니다.`
        : '조건에 맞는 뉴스가 없습니다.';
    resultsDiv.innerHTML =
      `<div style="text-align:center;padding:40px;color:#999;">
         <div style="font-size:48px;margin-bottom:12px;">🔍</div>
         <p style="font-size:16px;">${msg}</p>
         <p style="font-size:14px;">다른 조건으로 검색해보세요.</p>
       </div>`;
    return;
  }

  resultsDiv.innerHTML = filtered.map(a => {
    const emoji = a.category === '국내' ? '🇰🇷' : a.category === '국외' ? '🌍' : '⚔️';
    const hlTitle = highlight(a.title, query);
    const hlDate  = highlight(a.date, query);

    return `
      <div style="background:#fff;border:1px solid #e5e7eb;border-radius:10px;
                  padding:18px 20px;margin-bottom:14px;
                  box-shadow:0 1px 3px rgba(0,0,0,0.06);">
        <div style="font-size:12px;color:#6b7280;margin-bottom:6px;">
          ${emoji} ${a.category} &nbsp;|&nbsp; 📅 ${hlDate}
        </div>
        <a href="${a.link}" target="_blank"
           style="font-size:16px;font-weight:700;color:var(--mint-dark);
                  text-decoration:none;line-height:1.45;display:block;">
          ${hlTitle}
        </a>
      </div>`;
  }).join('');
}
</script>
