#!/usr/bin/env python3
"""
BTC 파생시장 지표 수집기 (GitHub Actions 실행용)

Binance Futures API는 GitHub Actions 호스팅 러너(미국 데이터센터 IP)에서
HTTP 451로 차단되므로, 대신 지리적 차단이 없는 OKX 공개 API(무인증)와
CoinGecko 공개 API를 사용한다. 결과는 data/btc_derivatives.csv에 한 줄
누적 기록한다(기존 행은 수정하지 않음 — score_history.md와 동일 원칙).

주의: 지표 구성이 마스터 지침 2-2③(Binance 심볼 기준: 계정/포지션/글로벌
3종 L/S 비율)과 다르다. OKX는 단일 롱숏비율(전체 계정 기준)만 제공하므로
`ls_ratio_accounts` 한 컬럼으로 단순화했다.
"""
import csv
import json
import os
import urllib.request
from datetime import datetime, timezone

CSV_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "btc_derivatives.csv")
INST_ID = "BTC-USDT-SWAP"
FLAT_BAND_PRICE = 0.1   # % — 가격 중립 밴드 (기존 state-matrix 캡션과 동일 기준)
FLAT_BAND_OI = 0.3      # % — OI 중립 밴드

FIELDNAMES = [
    "timestamp_utc", "price_usd", "price_change_pct_24h", "perp_volume_usd_24h",
    "oi_usd", "funding_rate_pct", "basis_pct", "ls_ratio_accounts",
    "oi_mcap_ratio_pct", "verdict",
]


def fetch_json(url):
    req = urllib.request.Request(url, headers={"User-Agent": "master-score-lab-btc-collector/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read().decode("utf-8"))


def okx_ticker():
    data = fetch_json(f"https://www.okx.com/api/v5/market/ticker?instId={INST_ID}")["data"][0]
    last = float(data["last"])
    open24h = float(data["open24h"])
    change_pct = (last - open24h) / open24h * 100 if open24h else 0.0
    volume_usd = float(data.get("volCcy24h", 0))
    return last, change_pct, volume_usd


def okx_open_interest(price):
    data = fetch_json(f"https://www.okx.com/api/v5/public/open-interest?instId={INST_ID}")["data"][0]
    oi_usd = data.get("oiUsd")
    if oi_usd not in (None, ""):
        return float(oi_usd)
    return float(data["oiCcy"]) * price


def okx_funding_rate():
    data = fetch_json(f"https://www.okx.com/api/v5/public/funding-rate?instId={INST_ID}")["data"][0]
    return float(data["fundingRate"]) * 100


def okx_basis():
    mark = float(fetch_json(f"https://www.okx.com/api/v5/public/mark-price?instId={INST_ID}")["data"][0]["markPx"])
    idx = float(fetch_json("https://www.okx.com/api/v5/market/index-tickers?instId=BTC-USDT")["data"][0]["idxPx"])
    return (mark - idx) / idx * 100 if idx else 0.0


def okx_long_short_ratio():
    data = fetch_json(
        f"https://www.okx.com/api/v5/rubik/stat/contracts/long-short-account-ratio?ccy=BTC&period=5m"
    )["data"]
    return float(data[0][1]) if data else None


def coingecko_market_cap():
    data = fetch_json("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd&include_market_cap=true")
    return float(data["bitcoin"]["usd_market_cap"])


def classify_verdict(price_change_pct, prev_oi, oi_usd):
    if prev_oi is None or prev_oi == 0:
        oi_change_pct = 0.0
    else:
        oi_change_pct = (oi_usd - prev_oi) / prev_oi * 100

    price_up = price_change_pct > FLAT_BAND_PRICE
    price_down = price_change_pct < -FLAT_BAND_PRICE
    oi_up = oi_change_pct > FLAT_BAND_OI
    oi_down = oi_change_pct < -FLAT_BAND_OI

    if price_up and oi_up:
        return "신규 롱 유입 가능성"
    if price_up and oi_down:
        return "숏 커버링 가능성"
    if price_down and oi_up:
        return "신규 숏 유입 가능성"
    if price_down and oi_down:
        return "롱 청산 가능성"
    if price_up:
        return "완만한 롱 우위"
    if price_down:
        return "완만한 숏 우위"
    return "중립·박스권"


def read_last_row():
    if not os.path.exists(CSV_PATH):
        return None
    with open(CSV_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    return rows[-1] if rows else None


def main():
    price, change_pct, volume_usd = okx_ticker()
    oi_usd = okx_open_interest(price)
    funding_pct = okx_funding_rate()
    basis_pct = okx_basis()
    ls_ratio = okx_long_short_ratio()
    market_cap = coingecko_market_cap()
    oi_mcap_pct = (oi_usd / market_cap * 100) if market_cap else 0.0

    prev = read_last_row()
    prev_oi = float(prev["oi_usd"]) if prev else None
    verdict = classify_verdict(change_pct, prev_oi, oi_usd)

    row = {
        "timestamp_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "price_usd": round(price, 2),
        "price_change_pct_24h": round(change_pct, 3),
        "perp_volume_usd_24h": round(volume_usd, 2),
        "oi_usd": round(oi_usd, 2),
        "funding_rate_pct": round(funding_pct, 5),
        "basis_pct": round(basis_pct, 4),
        "ls_ratio_accounts": round(ls_ratio, 4) if ls_ratio is not None else "",
        "oi_mcap_ratio_pct": round(oi_mcap_pct, 4),
        "verdict": verdict,
    }

    file_exists = os.path.exists(CSV_PATH) and os.path.getsize(CSV_PATH) > 0
    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)

    print(f"기록 완료: {row}")


if __name__ == "__main__":
    main()
