# PRD: 네이버 맵 크롤러

## 1. 개요

### 1.1 목적
경기도 관공서 주변 카페/음식점의 **영업시간 포함** 상세 정보를 수집하여 오프라인 리플릿 마케팅 타겟 리스트 생성

### 1.2 배경
- 카카오 API: 장소 목록 수집 가능하나 **영업시간 미제공**
- 네이버 검색 API: 페이지네이션 미지원, 데이터 부족
- 네이버 지도 내부 API: 영업시간 포함 상세 정보 제공 (브라우저 세션 필요)

---

## 2. 기능 요구사항

### 2.1 입력
```
검색어: "수원시청 카페" 또는 "성남시청 음식점"
또는
좌표 기반: { lat: 37.263, lng: 127.028, radius: 500, category: "카페" }
```

### 2.2 출력 (CSV)
| 필드 | 설명 | 예시 |
|------|------|------|
| name | 상호명 | 런던 수원인계점 |
| address | 도로명주소 | 경기 수원시 팔달구 권광로180번길 18-11 |
| phone | 전화번호 | 031-123-4567 |
| category | 업종 | 카페,디저트 |
| business_hours | 영업시간 | 다음 날 01:00에 영업 종료 |
| visitor_reviews | 방문자 리뷰 수 | 방문자 리뷰 859 |
| blog_reviews | 블로그 리뷰 수 | 166 |
| naver_place_id | 네이버 플레이스 ID | 1568480811 |

### 2.3 CLI 인터페이스
```bash
# 단일 검색
naver-map-crawler search "수원시청 카페" --output result.csv

# 배치 검색 (여러 지역)
naver-map-crawler batch regions.txt --output result.csv

# 좌표 기반 검색
naver-map-crawler nearby --lat 37.263 --lng 127.028 --radius 500 --category cafe
```

---

## 3. 기술 명세

### 3.1 네이버 지도 API 엔드포인트 (발견됨)

**검색 결과 페이지 (브라우저 필요)**
```
https://map.naver.com/p/search/{검색어}
```

**장소 상세 정보 API**
```
GET https://map.naver.com/p/api/place/summary/{place_id}

Headers:
  User-Agent: Mozilla/5.0 ...
  Referer: https://map.naver.com/

Response:
{
  "data": {
    "placeDetail": {
      "id": "1568480811",
      "name": "런던 수원인계점",
      "businessHours": {
        "description": "다음 날 01:00에 영업 종료"
      },
      "address": {
        "roadAddress": "경기 수원시 팔달구 권광로180번길 18-11"
      },
      "category": {
        "category": "카페,디저트"
      },
      "visitorReviews": {
        "displayText": "방문자 리뷰 859"
      },
      "blogReviews": {
        "total": 166
      }
    }
  }
}
```

### 3.2 크롤링 전략

**Step 1: 검색 결과에서 place_id 수집**
- Playwright/Puppeteer로 검색 페이지 로드
- 네트워크 응답 캡처하여 place_id 목록 추출
- 또는 DOM에서 place 링크 파싱

**Step 2: 각 place_id에 대해 상세 정보 조회**
- `/p/api/place/summary/{place_id}` 호출
- 브라우저 세션 쿠키 재사용 필요

**Step 3: 데이터 정제 및 CSV 저장**

### 3.3 권장 기술 스택
- **언어**: Python 3.10+ 또는 Node.js
- **브라우저 자동화**: Playwright (권장) 또는 Puppeteer
- **출력**: CSV (utf-8-sig for Excel 호환)

---

## 4. 사용 시나리오

### 4.1 배치 검색 입력 파일 (regions.txt)
```
수원시청 카페
수원시청 음식점
성남시청 카페
성남시청 음식점
고양시청 카페
고양시청 음식점
용인시청 카페
용인시청 음식점
부천시청 카페
부천시청 음식점
```

### 4.2 예상 실행
```bash
$ naver-map-crawler batch regions.txt --max-per-query 30 --output 경기도_매장리스트.csv

🔍 수원시청 카페 검색 중... 30개 수집
🔍 수원시청 음식점 검색 중... 30개 수집
🔍 성남시청 카페 검색 중... 28개 수집
...
✅ 총 287개 저장: 경기도_매장리스트.csv
```

---

## 5. 제약 사항

### 5.1 Rate Limiting
- 요청 간 0.5~1초 딜레이 권장
- 과도한 요청 시 IP 차단 가능

### 5.2 데이터 정확성
- 영업시간은 "현재 기준" 표시 (예: "21:50에 라스트오더")
- 정기휴무, 상세 시간표는 별도 API 필요

### 5.3 법적 고려
- 상업적 사용 시 네이버 이용약관 확인 필요
- 수집 데이터는 내부 마케팅 목적으로만 사용

---

## 6. 우선순위

| 기능 | 우선순위 | 비고 |
|------|----------|------|
| 키워드 검색 | P0 | 필수 |
| place_id → 상세정보 | P0 | 필수 |
| 영업시간 추출 | P0 | 핵심 기능 |
| CSV 출력 | P0 | 필수 |
| 배치 검색 | P1 | 10개 지역 반복 |
| 중복 제거 | P1 | 이름+주소 기준 |
| 좌표 기반 검색 | P2 | 있으면 좋음 |

---

## 7. 예상 결과물

```
📁 naver-map-crawler/
├── crawler.py (or index.js)
├── requirements.txt (or package.json)
├── README.md
└── output/
    └── 경기도_매장리스트.csv
```

---

## 8. 연동 방법

개발 완료 후 다음 중 하나로 제공:

1. **CLI 실행** - 내가 직접 실행
   ```bash
   python crawler.py "수원시청 카페" --output result.csv
   ```

2. **로컬 API 서버** - HTTP로 호출
   ```bash
   curl "http://localhost:8000/search?query=수원시청 카페"
   ```

3. **Python 모듈** - 내가 import해서 사용
   ```python
   from naver_crawler import search_places
   results = search_places("수원시청 카페")
   ```

---

## 9. 참고: 테스트용 place_id

동작 확인용 ID들:
- `1568480811` - 런던 수원인계점 (카페)
- `1056820662` - 카페 오티티 인계본점
- `1037753649` - 아띠몽 수원영동시장점

테스트 API 호출:
```bash
curl -s "https://map.naver.com/p/api/place/summary/1568480811" \
  -H "User-Agent: Mozilla/5.0" \
  -H "Referer: https://map.naver.com/" | jq
```
