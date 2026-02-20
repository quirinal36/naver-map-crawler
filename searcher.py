"""
searcher.py — 네이버 지도 검색어 → place_id 목록 수집
Step 1: Playwright로 검색 페이지 로드 후 place_id 추출

전략:
1. 네트워크 인터셉트: API 응답 JSON에서 place_id 파싱
2. DOM 폴백: a[href*='/place/'] 패턴에서 ID 추출
3. 무한스크롤: max_count 도달까지 반복
"""

import asyncio
import re
import json
from playwright.async_api import async_playwright

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)

def _ids_from_all_search(body: dict) -> list[str]:
    """allSearch 응답의 result.place.list[].id 직접 파싱"""
    ids = []
    place_list = (
        body.get("result", {}).get("place", {}).get("list", [])
        or body.get("result", {}).get("place", {}).get("filterList", [])
        or []
    )
    for item in place_list:
        pid = str(item.get("id", "")).strip()
        if pid.isdigit() and len(pid) >= 7:
            ids.append(pid)
    return ids


async def _scroll_and_collect(page, place_ids: list, max_count: int, timeout: float = 12.0):
    """검색 결과 패널 무한스크롤로 추가 결과 로드"""
    elapsed = 0.0
    interval = 1.5
    while len(place_ids) < max_count and elapsed < timeout:
        prev = len(place_ids)
        # 검색 결과 목록 패널 스크롤 (네이버 지도 특정 선택자)
        await page.evaluate("""
            () => {
                const panel = document.querySelector('#_pcmap_list_scroll_container')
                           || document.querySelector('.search_listview')
                           || document.querySelector('[class*="searchListView"]');
                if (panel) panel.scrollTop = panel.scrollHeight;
                else window.scrollTo(0, document.body.scrollHeight);
            }
        """)
        await asyncio.sleep(interval)
        elapsed += interval
        if len(place_ids) == prev:
            break  # 더 이상 새 결과 없음


async def _dom_fallback(page) -> list[str]:
    """DOM에서 place 링크 파싱 (폴백)"""
    hrefs = await page.evaluate("""
        () => Array.from(document.querySelectorAll('a[href*="/place/"]'))
                   .map(a => a.href)
    """)
    ids = []
    for href in hrefs:
        m = re.search(r"/place/(\d{7,})", href)
        if m and m.group(1) not in ids:
            ids.append(m.group(1))
    return ids


async def search_place_ids(query: str, max_count: int = 30, headless: bool = True) -> list[str]:
    """
    검색어로 네이버 지도를 검색해 place_id 목록 반환

    Args:
        query: 검색어 (예: '수원시청 카페')
        max_count: 최대 수집 개수
        headless: True=헤드리스, False=브라우저 표시

    Returns:
        place_id 문자열 목록
    """
    place_ids: list[str] = []
    seen: set[str] = set()

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=headless)
        context = await browser.new_context(user_agent=USER_AGENT)
        page = await context.new_page()

        # ── 네트워크 인터셉트 ──────────────────────────────────────────
        async def on_response(response):
            if len(place_ids) >= max_count:
                return
            if "allSearch" not in response.url:
                return
            try:
                body = await response.json()
                for pid in _ids_from_all_search(body):
                    if pid not in seen:
                        seen.add(pid)
                        place_ids.append(pid)
            except Exception:
                pass

        page.on("response", on_response)

        # ── 검색 페이지 로드 ──────────────────────────────────────────
        search_url = f"https://map.naver.com/p/search/{query}"
        print(f"🔍 검색 중: {query}")
        print(f"   URL: {search_url}")
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
            await asyncio.sleep(3)  # JS 렌더링 대기
        except Exception as e:
            print(f"   [경고] 페이지 로드 오류: {e}")

        # ── 무한스크롤 ────────────────────────────────────────────────
        await _scroll_and_collect(page, place_ids, max_count)

        # ── DOM 폴백 ──────────────────────────────────────────────────
        if not place_ids:
            print("   [폴백] DOM에서 place_id 파싱 시도...")
            dom_ids = await _dom_fallback(page)
            for pid in dom_ids:
                if pid not in seen:
                    seen.add(pid)
                    place_ids.append(pid)

        await browser.close()

    result = place_ids[:max_count]
    print(f"   → {len(result)}개 place_id 수집 완료")
    return result


# ── 단독 실행 ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    query = sys.argv[1] if len(sys.argv) > 1 else "수원시청 카페"
    max_n = int(sys.argv[2]) if len(sys.argv) > 2 else 10

    ids = asyncio.run(search_place_ids(query, max_count=max_n, headless=True))
    print("\n수집된 place_id 목록:")
    for i, pid in enumerate(ids, 1):
        print(f"  {i:2d}. {pid}  →  https://map.naver.com/p/entry/place/{pid}")
