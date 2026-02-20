"""
fetcher.py — place_id → 상세정보 조회
Step 2: Naver Map API /p/api/place/summary/{place_id} 호출

실제 API 구조:
  data.placeDetail.{id, name, category.category, address.roadAddress,
                    businessHours.description, visitorReviews.displayText,
                    blogReviews.total}
"""

import time
import random
import requests

API_BASE = "https://map.naver.com/p/api/place/summary"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://map.naver.com/",
    "Accept": "application/json",
}

SESSION = requests.Session()
SESSION.headers.update(HEADERS)


def _safe(obj, *keys, default=""):
    """중첩 dict 안전 접근"""
    for key in keys:
        if not isinstance(obj, dict):
            return default
        obj = obj.get(key)
        if obj is None:
            return default
    return obj if obj is not None else default


def _parse(raw: dict) -> dict | None:
    """API 응답 → CSV 행 dict 변환"""
    detail = _safe(raw, "data", "placeDetail", default=None)
    if not detail or not isinstance(detail, dict):
        return None

    return {
        "name":            _safe(detail, "name"),
        "address":         _safe(detail, "address", "roadAddress"),
        "phone":           _safe(detail, "phone"),
        "category":        _safe(detail, "category", "category"),
        "business_hours":  _safe(detail, "businessHours", "description"),
        "visitor_reviews": _safe(detail, "visitorReviews", "displayText"),
        "blog_reviews":    _safe(detail, "blogReviews", "total", default=""),
        "naver_place_id":  _safe(detail, "id"),
    }


def fetch_place_detail(place_id: str) -> dict | None:
    """
    place_id로 상세정보 조회 (재시도 1회)

    Args:
        place_id: 네이버 플레이스 ID

    Returns:
        상세정보 dict 또는 None (실패 시)
    """
    url = f"{API_BASE}/{place_id}"

    for attempt in range(2):
        try:
            resp = SESSION.get(url, timeout=10)
            resp.raise_for_status()
            parsed = _parse(resp.json())
            if parsed and parsed["name"]:
                time.sleep(random.uniform(0.5, 1.0))
                return parsed
            raise ValueError("name 필드 없음")
        except Exception as e:
            if attempt == 0:
                time.sleep(1.0)
            else:
                print(f"   [SKIP] place_id={place_id}: {e}")

    return None


def fetch_many(place_ids: list[str]) -> list[dict]:
    """
    여러 place_id를 순차 조회해 결과 목록 반환

    Args:
        place_ids: place_id 목록

    Returns:
        성공한 항목만 포함한 dict 목록
    """
    results = []
    total = len(place_ids)
    for i, pid in enumerate(place_ids, 1):
        print(f"   [{i}/{total}] {pid} 조회 중...", end=" ", flush=True)
        detail = fetch_place_detail(pid)
        if detail:
            results.append(detail)
            print(f"✅ {detail['name']}")
        else:
            print("❌ 실패")
    return results


# ── 단독 실행 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    test_ids = sys.argv[1:] if len(sys.argv) > 1 else [
        "1568480811",  # 런던 수원인계점
        "1056820662",  # 카페 오티티 인계본점
        "1037753649",  # 아띠몽 수원영동시장점
    ]

    print(f"▶ {len(test_ids)}개 place_id 조회\n")
    for pid in test_ids:
        print(f"{'─'*50}")
        print(f"place_id: {pid}")
        detail = fetch_place_detail(pid)
        if detail:
            for k, v in detail.items():
                print(f"  {k:20s}: {v}")
        else:
            print("  → 조회 실패")
