"""
crawler.py — 네이버 맵 크롤러 CLI 진입점

Usage:
  python crawler.py search "수원시청 카페" --output result.csv
  python crawler.py batch regions.txt --max-per-query 30 --output 경기도_매장리스트.csv
  python crawler.py nearby --lat 37.263 --lng 127.028 --radius 500 --category cafe
"""

import asyncio
import sys
import click

from searcher import search_place_ids
from fetcher import fetch_many
from exporter import save_csv


# ── 공통 헬퍼 ────────────────────────────────────────────────────────────────

async def _collect(query: str, max_count: int) -> list[dict]:
    """검색어 하나 → 상세정보 목록"""
    place_ids = await search_place_ids(query, max_count=max_count)
    if not place_ids:
        click.echo(f"   ⚠️  place_id를 찾을 수 없습니다: {query}")
        return []
    details = fetch_many(place_ids)
    click.echo(f"   → {len(details)}개 수집")
    return details


# ── CLI 그룹 ─────────────────────────────────────────────────────────────────

@click.group()
def cli():
    """네이버 지도 크롤러 — 영업시간 포함 장소 정보 수집기"""
    pass


# ── search 커맨드 ─────────────────────────────────────────────────────────────

@cli.command()
@click.argument("query")
@click.option("--output", "-o", default="output/result.csv", show_default=True,
              help="저장 경로")
@click.option("--max", "max_count", default=30, show_default=True,
              help="최대 수집 개수")
def search(query, output, max_count):
    """단일 검색어로 장소 정보 수집

    \b
    예시:
      python crawler.py search "수원시청 카페" --output result.csv
    """
    click.echo(f"🔍 검색: {query}  (최대 {max_count}개)")
    records = asyncio.run(_collect(query, max_count))
    save_csv(records, output)


# ── batch 커맨드 ──────────────────────────────────────────────────────────────

@cli.command()
@click.argument("file", type=click.Path(exists=True))
@click.option("--output", "-o", default="output/result.csv", show_default=True,
              help="저장 경로")
@click.option("--max-per-query", default=30, show_default=True,
              help="쿼리당 최대 수집 개수")
def batch(file, output, max_per_query):
    """파일의 검색어 목록을 순서대로 수집 후 단일 CSV 저장

    \b
    예시:
      python crawler.py batch regions.txt --max-per-query 30 --output 경기도_매장리스트.csv
    """
    with open(file, encoding="utf-8") as f:
        queries = [line.strip() for line in f if line.strip()]

    click.echo(f"📋 배치 시작: {len(queries)}개 쿼리  (쿼리당 최대 {max_per_query}개)")
    click.echo("─" * 50)

    all_records: list[dict] = []
    for i, query in enumerate(queries, 1):
        click.echo(f"[{i}/{len(queries)}] 🔍 {query}")
        records = asyncio.run(_collect(query, max_per_query))
        all_records.extend(records)

    click.echo("─" * 50)
    click.echo(f"📊 총 수집: {len(all_records)}개")
    save_csv(all_records, output)


# ── nearby 커맨드 (P2) ────────────────────────────────────────────────────────

@cli.command()
@click.option("--lat", required=True, type=float, help="위도")
@click.option("--lng", required=True, type=float, help="경도")
@click.option("--radius", default=500, show_default=True, help="반경 (미터)")
@click.option("--category", default="카페", show_default=True, help="업종 키워드")
@click.option("--output", "-o", default="output/nearby.csv", show_default=True,
              help="저장 경로")
@click.option("--max", "max_count", default=30, show_default=True,
              help="최대 수집 개수")
def nearby(lat, lng, radius, category, output, max_count):
    """좌표 기반 주변 장소 수집 (P2)

    \b
    예시:
      python crawler.py nearby --lat 37.263 --lng 127.028 --radius 500 --category 카페
    """
    # 좌표를 검색어로 변환해 searcher에 전달 (네이버 지도 URL 형식)
    # https://map.naver.com/p/search/{category}?c={lng},{lat},15,0,0,0,dh
    query = f"{category}"
    click.echo(f"📍 좌표 기반 검색: lat={lat}, lng={lng}, radius={radius}m, 업종={category}")
    click.echo(f"   ※ 좌표 검색은 검색어 '{category}' 로 동작합니다 (개선 예정)")
    records = asyncio.run(_collect(query, max_count))
    save_csv(records, output)


# ── 진입점 ───────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    cli()
