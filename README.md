# Master Score Lab — 사이트 배포 가이드

## 폴더 구성
```
index.html       홈 (히어로 + 4개 섹션 카드)
dashboard.html    Macro Dashboard 전체 (기존 파일 그대로 반영됨)
charts.html       TradingView 실시간 차트
blog.html         Blogger 연결 페이지 (movenine.blogspot.com 연결됨)
youtube.html      유튜브 채널 연결 페이지 (개설 후 링크/임베드 추가)
assets/site.css   공통 네비게이션·푸터 스타일
```

## GitHub Pages로 배포하기 (5분)

1. **저장소 생성**
   github.com에서 새 저장소를 만듭니다. 이름은 자유(예: `master-score-lab`).
   Public으로 설정합니다 (Pages 무료 사용 조건).

2. **파일 업로드**
   이 폴더 안의 모든 파일(하위 `assets/` 폴더 포함)을 저장소 루트에 그대로 올립니다.
   - GitHub 웹 UI에서 "Add file → Upload files"로 드래그 앤 드롭 가능
   - 또는 `git add . && git commit -m "site init" && git push`

3. **Pages 활성화**
   저장소 → **Settings → Pages**
   - Source: `Deploy from a branch`
   - Branch: `main` / 폴더: `/ (root)`
   - 저장 후 1~2분 내 아래 주소가 생성됩니다.
   `https://<github-아이디>.github.io/<저장소명>/`

4. **접속 확인**
   위 주소로 접속해서 홈 → 대시보드 → 차트 → 블로그 → 유튜브 네비게이션이 모두 정상 작동하는지 확인합니다.

## 대시보드 갱신할 때마다 할 일

`마스터_지침_클로드최적화_v2.4.md`의 0-7/0-8 규칙에 따라 새 버전이 나오면:

1. 새 대시보드 HTML 내용을 `dashboard.html`의 `<nav>`와 `<footer>` 사이 부분에 통째로 교체
2. `<title>` 태그도 새 버전 번호로 갱신
3. GitHub에 다시 업로드(또는 git push) → Pages가 자동으로 재배포됨 (수동 배포 작업 없음)

## 아직 채워야 할 항목

- [x] `blog.html` — Blogger 실제 주소로 링크 교체
- [ ] `youtube.html` — 채널 개설 후 구독 링크 + 최신 영상 임베드 추가
- [ ] (선택) 커스텀 도메인 연결: 저장소 Settings → Pages → Custom domain

## 참고

- `charts.html`은 TradingView 공식 무료 임베드 위젯(`s3.tradingview.com/tv.js`)을 사용합니다. 심볼만 바꿔서 자유롭게 추가 가능합니다.
- 전체 페이지가 동일한 다크 테마 색상(`#0b0d12` 배경 등)을 공유하므로, 이후 페이지를 추가해도 `assets/site.css`의 `<nav>`/`<footer>` 블록만 복사하면 톤이 유지됩니다.
