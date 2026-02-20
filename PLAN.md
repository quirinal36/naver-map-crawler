# 개발 계획: 네이버 맵 크롤러

> PRD 기반 구현 계획 | 작성일: 2026-02-20

---

## 1. 프로젝트 구조

```
naver-map-crawler/
├── crawler.py          # 메인 진입점 (CLI)
├── searcher.py         # Step 1: 검색 → place_id 수집
├── fetcher.py          # Step 2: place_id → 상세정보 조회
├── exporter.py         # Step 3: CSV 저장
├── requirements.txt
├── regions.txt         # 배치 검색 쿼리 목록
└── output/
    └── 경기도_매장리스트.csv
```

---

## 2. 구현 단계

### Phase 1 — 환경 세팅 (P0)

| 작업 | 내용 |
|------|------|
| Python 환경 | 3.10+ 확인, venv 생성 |
| 의존성 설치 | `playwright`, `pandas`, `click` |
| Playwright 초기화 | `playwright install chromium` |

```txt
# requirements.txt
playwright
pandas
click
```

---

### Phase 2 — place_id 수집기 (P0): `searcher.py`

**목표**: 검색어 → place_id 목록 반환

**전략 (네트워크 인터셉트)**:
1. Playwright로 `https://map.naver.com/p/search/{검색어}` 로드
2. `route()` 또는 `on('response')` 로 네트워크 응답 감청
3. `/api/search` 또는 `/api/place/list` 응답에서 place_id 파싱
4. DOM 폴백: `a[href*="/place/"]` 패턴에서 ID 추출

```python
# 핵심 인터페이스
async def search_place_ids(query: str, max_count: int = 30) -> list[str]:
    """검색어로 place_id 목록 반환"""
```

**주의사항**:
- 페이지 로드 후 스크롤 다운으로 추가 결과 로드 (무한스크롤)
- 최대 `max_count`개 수집 후 중단

---

### Phase 3 — 상세정보 조회기 (P0): `fetcher.py`

**목표**: place_id → 상세정보 dict 반환

**API 엔드포인트**:
```
GET https://map.naver.com/p/api/place/summary/{place_id}
Headers:
  User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64)
  Referer: https://map.naver.com/
```

**응답 파싱 필드**:
```python
{
    "name":             data["placeDetail"]["name"],
    "address":          data["placeDetail"]["address"]["roadAddress"],
    "phone":            data["placeDetail"]["phone"],
    "category":         data["placeDetail"]["category"]["category"],
    "business_hours":   data["placeDetail"]["businessHours"]["description"],
    "visitor_reviews":  data["placeDetail"]["visitorReviews"]["displayText"],
    "blog_reviews":     data["placeDetail"]["blogReviews"]["total"],
    "naver_place_id":   data["placeDetail"]["id"],
}
```

**전략**:
- Playwright 세션의 `page.evaluate()` 로 fetch 호출 → 쿠키/세션 자동 포함
- 요청 간 0.5~1.0초 랜덤 딜레이
- 실패 시 1회 재시도 후 스킵

```python
# 핵심 인터페이스
async def fetch_place_detail(page, place_id: str) -> dict | None:
    """place_id로 상세정보 반환, 실패 시 None"""
```

---

### Phase 4 — CSV 출력기 (P0): `exporter.py`

- 인코딩: `utf-8-sig` (Excel 한글 호환)
- 컬럼 순서: `name, address, phone, category, business_hours, visitor_reviews, blog_reviews, naver_place_id`
- 중복 제거: `name + address` 기준 (P1)

---

### Phase 5 — CLI 통합 (P0): `crawler.py`

```bash
# 단일 검색
python crawler.py search "수원시청 카페" --output result.csv

# 배치 검색
python crawler.py batch regions.txt --max-per-query 30 --output 경기도_매장리스트.csv

# 좌표 기반 (P2, 나중에)
python crawler.py nearby --lat 37.263 --lng 127.028 --radius 500 --category cafe
```

**Click 명령 구조**:
```
crawler.py
├── search <query>   --output --max
├── batch <file>     --output --max-per-query
└── nearby           --lat --lng --radius --category --output
```

---

### Phase 6 — 테스트 (P1)

**단계별 검증**:

1. **fetcher 단독 테스트**: 알려진 place_id로 API 응답 확인
   ```bash
   python -c "import asyncio; from fetcher import fetch_place_detail; ..."
   # place_id: 1568480811 (런던 수원인계점)
   ```

2. **searcher 단독 테스트**: "수원시청 카페" 검색 → ID 목록 출력

3. **통합 테스트**: 단일 쿼리 end-to-end, CSV 생성 확인

4. **배치 테스트**: regions.txt 전체 실행

---

## 3. 구현 순서 (의존성 그래프)

```
[환경 세팅]
     ↓
[fetcher.py] ←─── 가장 먼저: place_id → 상세정보 (독립 테스트 가능)
     ↓
[searcher.py] ←── 검색 → place_id 목록 (Playwright 필요)
     ↓
[exporter.py] ←── CSV 저장 (간단)
     ↓
[crawler.py] ←─── CLI 통합
     ↓
[배치/중복제거] ← P1 기능 추가
```

> `fetcher.py`를 먼저 구현하는 이유: PRD에 테스트용 place_id가 제공되어 있어 즉시 검증 가능

---

## 4. 기술적 리스크 및 대응

| 리스크 | 가능성 | 대응 |
|--------|--------|------|
| 검색 결과 API 구조 변경 | 중 | DOM 폴백(링크 파싱) 병행 구현 |
| Playwright 감지 차단 | 중 | stealth 옵션, 랜덤 딜레이, User-Agent 설정 |
| `businessHours` 필드 없음 | 중 | `None` 처리, 빈 문자열로 CSV 저장 |
| IP 차단 | 저 | 요청 간격 준수, 세션 유지 |
| 무한스크롤 미작동 | 중 | 스크롤 + 네트워크 대기 로직 강화 |

---

## 5. 결과물 체크리스트

- [ ] `fetcher.py` — place_id로 상세정보 조회
- [ ] `searcher.py` — 검색어로 place_id 목록 수집
- [ ] `exporter.py` — CSV 저장 (utf-8-sig, 중복 제거)
- [ ] `crawler.py` — CLI (search / batch 명령)
- [ ] `requirements.txt`
- [ ] `regions.txt` (PRD 4.1 기준 10개 쿼리)
- [ ] `output/경기도_매장리스트.csv` — 실제 수집 결과

---

## 6. 즉시 시작 가능한 첫 번째 작업

```bash
# 1. 의존성 설치
pip install playwright pandas click
playwright install chromium

# 2. fetcher.py 구현 후 즉시 검증
python fetcher.py 1568480811
# → 런던 수원인계점 정보 출력 확인
```
