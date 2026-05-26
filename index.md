---
layout: default
title: 홈
---

<style>
  /* 왼쪽 메뉴바 제목 글자 크기 줄여서 한 줄로 만들기 */
  header h1 {
    font-size: 21px !important; /* 글자 크기를 살짝 줄여 한 줄로 맞춤 */
    letter-spacing: -0.5px;    /* 글자 간격을 좁힘 */
    word-break: keep-all;      /* 단어가 중간에 깨지지 않게 함 */
  }
</style>

# 🖨️ 우민짱의 3D 프린팅 뉴스레터

우민짱이 매일 수집하는 3D 프린팅 뉴스 아카이브합니다.

🔍 **[뉴스레터 검색하기 →](./search.html)**

## 📰 최근 뉴스레터

{% for post in site.posts limit:15 %}
- **[{{ post.title }}]({{ post.url | relative_url }})** - {{ post.date | date: "%Y년 %m월 %d일" }}
{% endfor %}

{% if site.posts.size == 0 %}
*곧 첫 번째 뉴스레터가 자동으로 아카이브될 예정입니다!*
{% endif %}

## 📊 통계
- 총 {{ site.posts.size }}개의 뉴스레터 아카이브됨
- 최근 업데이트: {{ site.time | date: "%Y년 %m월 %d일" }}
