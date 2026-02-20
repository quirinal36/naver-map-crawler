"""
exporter.py — 수집 결과 CSV 저장
Step 3: 중복 제거 후 utf-8-sig 인코딩으로 저장 (Excel 한글 호환)
"""

import os
import pandas as pd

COLUMNS = [
    "name",
    "address",
    "phone",
    "category",
    "business_hours",
    "visitor_reviews",
    "blog_reviews",
    "naver_place_id",
]


def deduplicate(records: list[dict]) -> list[dict]:
    """
    name + address 기준 중복 제거 (먼저 나온 항목 유지)

    Args:
        records: 상세정보 dict 목록

    Returns:
        중복 제거된 목록
    """
    seen: set[tuple] = set()
    result: list[dict] = []
    for r in records:
        key = (r.get("name", ""), r.get("address", ""))
        if key not in seen:
            seen.add(key)
            result.append(r)
    return result


def save_csv(records: list[dict], output_path: str, dedup: bool = True) -> int:
    """
    수집 결과를 CSV로 저장

    Args:
        records: 상세정보 dict 목록
        output_path: 저장 경로 (.csv)
        dedup: True이면 name+address 기준 중복 제거

    Returns:
        저장된 행 수
    """
    if not records:
        print("⚠️  저장할 데이터가 없습니다.")
        return 0

    before = len(records)
    if dedup:
        records = deduplicate(records)
        removed = before - len(records)
        if removed:
            print(f"   중복 제거: {removed}개 제거 ({before} → {len(records)})")

    os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)

    df = pd.DataFrame(records, columns=COLUMNS)
    df.to_csv(output_path, index=False, encoding="utf-8-sig")

    print(f"✅ {len(df)}개 저장: {output_path}")
    return len(df)


# ── 단독 실행 (샘플 데이터로 테스트) ────────────────────────────────────────
if __name__ == "__main__":
    sample = [
        {
            "name": "런던 수원인계점",
            "address": "경기 수원시 팔달구 권광로180번길 18-11",
            "phone": "",
            "category": "카페,디저트",
            "business_hours": "다음 날 01:00에 영업 종료",
            "visitor_reviews": "방문자 리뷰 859",
            "blog_reviews": 166,
            "naver_place_id": "1568480811",
        },
        {
            "name": "카페 오티티 인계본점",
            "address": "경기 수원시 팔달구 권광로180번길 21 1층 101호",
            "phone": "",
            "category": "카페,디저트",
            "business_hours": "21:50에 라스트오더",
            "visitor_reviews": "방문자 리뷰 1,829",
            "blog_reviews": 390,
            "naver_place_id": "1056820662",
        },
        # 중복 테스트용 (name+address 동일)
        {
            "name": "런던 수원인계점",
            "address": "경기 수원시 팔달구 권광로180번길 18-11",
            "phone": "",
            "category": "카페,디저트",
            "business_hours": "다음 날 01:00에 영업 종료",
            "visitor_reviews": "방문자 리뷰 859",
            "blog_reviews": 166,
            "naver_place_id": "1568480811",
        },
    ]

    print(f"입력: {len(sample)}개 (중복 1개 포함)")
    count = save_csv(sample, "output/test_output.csv")
    print(f"저장 완료: {count}개")

    # CSV 내용 확인
    import pandas as pd
    df = pd.read_csv("output/test_output.csv", encoding="utf-8-sig")
    print(f"\n── CSV 내용 ({len(df)}행) ──")
    print(df.to_string(index=False))
