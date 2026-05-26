---
layout: default
title: 홈
---

# 🖨️ 3D 프린팅 뉴스레터 아카이브

매일 자동으로 수집되는 3D 프린팅 뉴스를 아카이브합니다.

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
