# Claude Code 작업지시서 #2 — 디자인 확정 반영 + score_history.md 저장소 편입

> 이전 지시서(`CLAUDE_CODE_작업지시서_20260914.md`)의 후속 작업입니다. 이번 건으로 claude.ai 세션에서의
> 디자인 설계 작업은 마무리되고, 이후 실제 코드·git 작업은 전부 Claude Code에서 진행합니다.

---

## 1. 반영할 파일 (첨부된 `master-score-lab-site.zip`, 최신본)

```bash
unzip -o master-score-lab-site.zip -d /tmp/mslab-extract
cp -r /tmp/mslab-extract/master-score-lab-site/* ./
```

| 파일 | 변경 내용 |
|---|---|
| `dashboard.html` | **전면 교체** — 기존 "Blogger 전체 콘텐츠 임베드" 방식을 폐기하고, 축약형 카드 디자인(히어로+추이차트+배지형 경보+BTC 티저)으로 완전히 새로 작성됨. 전체 상세 리포트는 이제 이 페이지가 아니라 Blogger(`https://movenine.blogspot.com/`)로 링크만 건다. |
| `blog.html` | placeholder 제거, 실제 주소(`https://movenine.blogspot.com/`)로 연결 완료 |
| 나머지 (`index.html`, `btc.html`, `charts.html`, `youtube.html`, `assets/`) | 이전 지시서와 동일, 변경 없음 |

**중요**: `dashboard.html`에 Chart.js(CDN, `cdnjs.cloudflare.com/.../chart.umd.min.js`)를 사용합니다. 네트워크 차단 환경이 아니면 별도 조치 불필요.

---

## 2. `score_history.md`를 저장소 파일로 편입 (신규 작업)

지금까지 이 파일은 클로드 프로젝트 지식 첨부파일로만 존재했습니다. 앞으로는 **저장소 안의 실 파일**로 관리합니다.

1. 저장소에 위치 결정 (권장: 루트 또는 `/data/score_history.md` — 팀 컨벤션에 맞게 Claude Code가 판단해도 무방)
2. 현재까지의 누적 로그 내용을 그 경로에 커밋 (내용은 별도로 전달 — 아직 전달 안 됐다면 다음 메시지로 요청)
3. `dashboard.html`의 `<script>` 안 `labels`/각 `ds(...)` 배열이 **이 파일의 값과 항상 일치**하도록 유지 — 즉 앞으로 리포트를 갱신할 때마다:
   - `score_history.md`에 새 행 추가 (기존 행 수정 금지)
   - `dashboard.html`의 차트 데이터 배열에 같은 값을 한 항목 추가
   - 두 변경을 **같은 커밋**으로 묶어서 푸시 (파일 간 불일치 방지)

**현재 알려진 미기록 포인트**: 2026-09-14 Master Score 48점(v1.2 대시보드 값)이 아직 `score_history.md`에 한 줄로 기록되지 않았습니다. 이 데이터를 로그에 추가할 때, 하위 스코어 4개 원값도 함께 기록해야 합니다(0-12 규칙 — 유동성 +1, 금리스트레스 -2, 신용 +1, AI사이클 0). 기록 후 `dashboard.html` 차트에도 `09-14` 포인트를 추가하고, 차트 아래 각주("⏳ 아직 기록 전")는 제거합니다.

---

## 3. 커밋 & 푸시

```bash
git add .
git commit -m "dashboard: 축약형 디자인으로 전면 개편, score_history.md 저장소 편입"
git push origin main
```

---

## 4. 참고 문서 (같은 프로젝트, 이번 디자인의 근거)

- `홈페이지_대시보드_지침서_v1.0.md` — **이 디자인의 상세 규칙 문서**(색상 토큰, 차트 스타일 파라미터, 페이지 섹션 순서, 금지 사항). 앞으로 이 사이트를 수정할 때는 이 문서를 1차 기준으로 삼습니다. 저장소 `/docs`에 함께 커밋해두는 것을 권장합니다.
- `마스터_지침_클로드최적화_v2.8.md` — Blogger 전체 대시보드 규칙 (홈페이지와는 별개 문서, 참고만)
- `BTC_파생지표_독립형페이지_제작규칙_v1.2.md` — `btc.html` 규칙

### 데이터 소스 (변경 없음)
- BTC Derivatives Log: `https://docs.google.com/spreadsheets/d/1-NOv34PjewTj8JQqURz7xlTd81yzbFfiBa5tsM8MgPE/edit?usp=drive_link`
- Macro Collector (Dashboard_Data): `https://docs.google.com/spreadsheets/d/19tWdXi2Y52taNPhtTNgbs5NwrDcaggywqbBmsg9bfAg/edit?usp=drive_link`

---

## 5. 이번 작업 이후 (참고용, 지금 착수 아님)

- BTC 파생지표 1시간 주기 Claude API 자동 분석 파이프라인 — 설계는 합의됐으나 코드 미작성
- 매크로 트랙 고정 시각(2~3회) + 이벤트 트리거 자동화 — 설계만 합의, 코드 미작성
- 위 두 가지는 별도 작업지시서로 다시 요청할 예정입니다.
