#!/usr/bin/env python3
"""
BTC Derivatives Log 구글시트 동기화 + 해석 계산 (GitHub Actions 실행용)

로컬 Python(바이낸스 API 수집)이 계속 "BTC Derivatives Log" 구글시트에
적재하고, 이 스크립트는 GitHub Actions에서 그 시트를 공개 CSV 내보내기
URL로 읽어와 저장소 data/btc_derivatives_log.csv로 그대로 미러링한다
(시트 자체가 누적 로그이므로 매번 전체를 최신 상태로 덮어쓴다).

이후 원본 컬럼은 그대로 두고, 가격×OI 매트릭스 + TopTrader L/S 계정/포지션
디버전스를 기준으로 "해석(자동)" 컬럼을 계산해 덧붙인다.

전제: 시트가 "링크가 있는 모든 사용자에게 공개(뷰어)"로 공유되어 있어야
인증 없이 CSV 내보내기가 가능하다. 비공개로 바뀌면 이 스크립트는 실패한다.
"""
import csv
import io
import os
import urllib.error
import urllib.request
from typing import Literal, Optional

SHEET_ID = "1-NOv34PjewTj8JQqURz7xlTd81yzbFfiBa5tsM8MgPE"
SHEET_GID = "0"  # 시트 탭이 여러 개이고 로그가 첫 탭이 아니면 실제 gid로 교체

# 시트 공유가 켜져 있어도 /export 엔드포인트가 302→400을 내는 경우가 있어
# gviz/tq CSV 엔드포인트를 1순위로, /export를 2순위 폴백으로 시도한다.
CANDIDATE_URLS = [
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&gid={SHEET_GID}",
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}",
]

# 브라우저에 가까운 UA — 일부 Google 엔드포인트가 스크립트성 UA에 다르게 응답하는 경우 대비
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "btc_derivatives_log.csv")

FLAT_BAND_PRICE = 0.1   # % — 가격 중립 밴드. 반드시 OI와 동일한 행 간(약 10분) 기준으로 적용한다
FLAT_BAND_OI = 0.3      # % — OI 중립 밴드 (행 간 기준)

PRICE_COL = "가격"           # 24h변동%가 아니라 이 컬럼을 행 간 비교에 사용한다 (표시용 24h%와 시간창이 다름)
PRICE_CHG_COL = "24h변동%"   # 표시(화면 노출)용으로만 별도 보존, 해석 로직에는 사용하지 않음
OI_COL = "OI(BTC)"
LS_ACCOUNTS_COL = "TopTrader L/S(계정) 추세"
LS_POSITIONS_COL = "TopTrader L/S(포지션) 추세"

Direction = Literal["up", "flat", "down"]

ARROW_UP = {"▲", "up", "UP", "상승"}
ARROW_DOWN = {"▼", "down", "DOWN", "하락"}


def _try_fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": BROWSER_UA})
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.geturl(), resp.read().decode("utf-8-sig")


def fetch_csv_rows():
    last_err = None
    for url in CANDIDATE_URLS:
        try:
            final_url, text = _try_fetch(url)
            print(f"성공: {url} -> {final_url} ({len(text)} bytes)")
            reader = csv.DictReader(io.StringIO(text))
            # 시트 서식이 데이터 범위보다 넓게 걸려 있으면 빈 헤더(무명) 열이 섞여
            # 나오므로 제거한다 — 실 데이터 열만 남긴다.
            fieldnames = [f for f in reader.fieldnames if f]
            rows = [{k: v for k, v in row.items() if k} for row in reader]
            if not rows:
                print(f"경고: {url} 응답에 데이터 행이 없음, 다음 후보 시도")
                continue
            return rows, fieldnames
        except urllib.error.HTTPError as e:
            body = e.read(500).decode("utf-8", "replace")
            print(f"실패: {url} -> HTTP {e.code} {e.reason}\n응답 본문(앞 500자): {body}")
            last_err = e
        except urllib.error.URLError as e:
            print(f"실패: {url} -> {e.reason}")
            last_err = e
    raise last_err if last_err else RuntimeError("모든 후보 URL이 실패했습니다")


def to_float(s):
    try:
        return float(str(s).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def parse_trend_final(value: Optional[str]) -> Optional[float]:
    """'1.3652→1.3753' 형태에서 최종값(마지막 화살표 뒤 숫자)만 추출한다."""
    if not value:
        return None
    tail = str(value).split("→")[-1].strip()
    return to_float(tail)


def trend_direction(value, prev_num: Optional[float] = None, cur_num: Optional[float] = None, band: float = 0.0) -> Optional[Direction]:
    """숫자 비교로 방향을 판정한다. 비교할 값이 하나라도 없으면 None(데이터 부족)을 반환한다."""
    if value:
        v = str(value).strip()
        if v in ARROW_UP:
            return "up"
        if v in ARROW_DOWN:
            return "down"
    if prev_num is None or cur_num is None or prev_num == 0:
        return None
    diff_pct = (cur_num - prev_num) / prev_num * 100
    if diff_pct > band:
        return "up"
    if diff_pct < -band:
        return "down"
    return "flat"


_VERDICT_MATRIX: dict[tuple[Direction, Direction], str] = {
    ("up", "up"): "신규 롱 유입 가능성",
    ("up", "flat"): "완만한 롱 우위 가능성",
    ("up", "down"): "숏 커버링 가능성",
    ("flat", "up"): "포지션 확대 가능성",
    ("flat", "flat"): "중립·박스권",
    ("flat", "down"): "정리·관망 가능성",
    ("down", "up"): "신규 숏 유입 가능성",
    ("down", "flat"): "완만한 숏 우위 가능성",
    ("down", "down"): "롱 청산 가능성",
}


def classify_verdict(price_dir: Direction, oi_dir: Direction) -> str:
    key = (price_dir, oi_dir)
    if key not in _VERDICT_MATRIX:
        raise ValueError(f"Unexpected direction pair: {key!r}")
    return _VERDICT_MATRIX[key]


def interpret(rows):
    for i, row in enumerate(rows):
        prev_price = to_float(rows[i - 1].get(PRICE_COL)) if i > 0 else None
        cur_price = to_float(row.get(PRICE_COL))
        price_dir = trend_direction(None, prev_price, cur_price, FLAT_BAND_PRICE)

        prev_oi = to_float(rows[i - 1].get(OI_COL)) if i > 0 else None
        cur_oi = to_float(row.get(OI_COL))
        oi_dir = trend_direction(None, prev_oi, cur_oi, FLAT_BAND_OI)

        if price_dir is None or oi_dir is None:
            row["해석(자동)"] = "데이터 부족"
            continue

        verdict = classify_verdict(price_dir, oi_dir)

        prev_acc = parse_trend_final(rows[i - 1].get(LS_ACCOUNTS_COL)) if i > 0 else None
        cur_acc = parse_trend_final(row.get(LS_ACCOUNTS_COL))
        acc_dir = trend_direction(None, prev_acc, cur_acc, band=0.0)

        prev_pos = parse_trend_final(rows[i - 1].get(LS_POSITIONS_COL)) if i > 0 else None
        cur_pos = parse_trend_final(row.get(LS_POSITIONS_COL))
        pos_dir = trend_direction(None, prev_pos, cur_pos, band=0.0)

        if acc_dir in ("up", "down") and pos_dir in ("up", "down") and acc_dir != pos_dir:
            verdict += " · 계정/포지션 L/S 디버전스(소액↔대형 반대 포지셔닝 가능성)"

        row["해석(자동)"] = verdict
    return rows


def main():
    rows, fieldnames = fetch_csv_rows()
    if not rows:
        print("시트에 데이터가 없습니다 — 동기화 생략")
        return

    rows = interpret(rows)
    out_fields = list(fieldnames) + ["해석(자동)"]

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=out_fields)
        writer.writeheader()
        writer.writerows(rows)

    print(f"동기화 완료: {len(rows)}건 → {OUT_PATH}")


if __name__ == "__main__":
    main()
