#!/usr/bin/env python3
"""
로이터 ROI 페이지 웹패치 가능성 1회성 테스트 (GitHub Actions 러너에서 실행).

목적: 스크립트(urllib) 기반 요청이 실제로 200 OK + 유의미한 본문을 받는지,
아니면 봇 차단/구독 요구/리다이렉트로 막히는지 확인한다.
동기화 파이프라인에 편입하기 전 1회 실행 후 결과를 보고 삭제/보존을 결정한다.
"""
import urllib.error
import urllib.request

URL = "https://www.reuters.com/commentary/reuters-open-interest/"
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
            print("---- 본문 앞 1000자 ----")
            print(body[:1000])
    except urllib.error.HTTPError as e:
        body = e.read(1000).decode("utf-8", "replace")
        print(f"HTTPError: {e.code} {e.reason}")
        print("---- 응답 본문(앞 1000자) ----")
        print(body)
    except urllib.error.URLError as e:
        print(f"URLError: {e.reason}")


if __name__ == "__main__":
    main()
