#!/usr/bin/env python3
"""
로이터 ROI 개별 기사 URL 웹패치 가능성 1회성 테스트 (GitHub Actions 러너에서 실행).

목적: 인덱스 페이지(/commentary/reuters-open-interest/)는 DataDome 봇 차단이
확인되었으나, 개별 기사 URL도 동일하게 막히는지 확인한다.
"""
import urllib.error
import urllib.request

URL = (
    "https://www.reuters.com/commentary/reuters-open-interest/"
    "us-yield-curve-sends-stark-warning-consumers-cant-handle-rate-hikes-2026-09-14/"
)
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)


def main():
    req = urllib.request.Request(URL, headers={"User-Agent": BROWSER_UA, "Accept-Language": "en-US,en;q=0.9"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            body = resp.read().decode("utf-8", "replace")
            print(f"HTTP {resp.status} | final_url={resp.geturl()} | bytes={len(body)}")
            print("---- 본문 앞 1500자 ----")
            print(body[:1500])
    except urllib.error.HTTPError as e:
        body = e.read(1000).decode("utf-8", "replace")
        print(f"HTTPError: {e.code} {e.reason}")
        print("---- 응답 본문(앞 1000자) ----")
        print(body)
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")


if __name__ == "__main__":
    main()
