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
import urllib.request

SHEET_ID = "1-NOv34PjewTj8JQqURz7xlTd81yzbFfiBa5tsM8MgPE"
SHEET_GID = "0"  # 시트 탭이 여러 개이고 로그가 첫 탭이 아니면 실제 gid로 교체
EXPORT_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={SHEET_GID}"

OUT_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "btc_derivatives_log.csv")

FLAT_BAND_PRICE = 0.1   # % — 가격 중립 밴드 (btc.html state-matrix 캡션과 동일 기준)
FLAT_BAND_OI = 0.3      # % — OI 중립 밴드

PRICE_CHG_COL = "24h변동%"
OI_COL = "OI(BTC)"
OI_TREND_COL = "OI추세"
LS_ACCOUNTS_COL = "TopTrader L/S(계정) 추세"
LS_POSITIONS_COL = "TopTrader L/S(포지션) 추세"

ARROW_UP = {"▲", "up", "UP", "상승"}
ARROW_DOWN = {"▼", "down", "DOWN", "하락"}


def fetch_csv_rows():
    req = urllib.request.Request(EXPORT_URL, headers={"User-Agent": "master-score-lab-btc-sync/1.0"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        text = resp.read().decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    return list(reader), reader.fieldnames


def to_float(s):
    try:
        return float(str(s).replace(",", "").replace("%", "").strip())
    except (TypeError, ValueError):
        return None


def trend_direction(value, prev_num=None, cur_num=None, band=0.0):
    """추세 컬럼이 화살표/텍스트면 그대로 방향을 읽고, 숫자면 전 행 대비로 판정한다."""
    if value:
        v = str(value).strip()
        if v in ARROW_UP:
            return "up"
        if v in ARROW_DOWN:
            return "down"
    if prev_num is not None and cur_num is not None and prev_num != 0:
        diff_pct = (cur_num - prev_num) / prev_num * 100
        if diff_pct > band:
            return "up"
        if diff_pct < -band:
            return "down"
        return "flat"
    return "flat"


def classify_verdict(price_dir, oi_dir):
    if price_dir == "up" and oi_dir == "up":
        return "신규 롱 유입 가능성"
    if price_dir == "up" and oi_dir == "down":
        return "숏 커버링 가능성"
    if price_dir == "down" and oi_dir == "up":
        return "신규 숏 유입 가능성"
    if price_dir == "down" and oi_dir == "down":
        return "롱 청산 가능성"
    if price_dir == "up":
        return "완만한 롱 우위"
    if price_dir == "down":
        return "완만한 숏 우위"
    if oi_dir == "up":
        return "포지션 확대(방향 미확정)"
    if oi_dir == "down":
        return "포지션 정리·관망"
    return "중립·박스권"


def interpret(rows):
    for i, row in enumerate(rows):
        price_chg = to_float(row.get(PRICE_CHG_COL)) or 0.0
        price_dir = "up" if price_chg > FLAT_BAND_PRICE else "down" if price_chg < -FLAT_BAND_PRICE else "flat"

        prev_oi = to_float(rows[i - 1].get(OI_COL)) if i > 0 else None
        cur_oi = to_float(row.get(OI_COL))
        oi_dir = trend_direction(row.get(OI_TREND_COL), prev_oi, cur_oi, FLAT_BAND_OI)

        verdict = classify_verdict(price_dir, oi_dir)

        acc_dir = trend_direction(row.get(LS_ACCOUNTS_COL))
        pos_dir = trend_direction(row.get(LS_POSITIONS_COL))
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
