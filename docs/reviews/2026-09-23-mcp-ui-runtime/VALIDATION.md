# 검증 결과와 재현 범위

기준일 **2026-09-23 (Asia/Seoul)**. 검사 통과가 모델 품질·실제 구독 연결·인가·근거 진실성·접근성 전체 통과를 의미하지 않는다.

## 1. 확인한 GitHub CI

코드 및 UI commit **`85e3cb1f3641c52278dd1d391fe845024b23b7df`**의 [offline-checks 실행](https://github.com/inlight37-design/decision-model_lab/actions/runs/35756138070)을 GitHub API와 실제 job log로 확인했다.

| 항목 | 결과와 정확한 범위 |
|---|---|
| Python 3.12 / 3.13 matrix | 두 job completed / success |
| 3.13 전체 unittest 로그 | **112 tests / OK, skip 없음** |
| 추가 테스트 | 경계 투영 31개 + 대비 수식 6개 = 37개 |
| 기존 검사 | frontier 40개, v0.1 25/25, v0.2 합성 결속 검사 통과 |
| 원장 | v0.3 31개 + v0.4 29개 = **60개**의 구조 검사 통과 |
| 인코딩·디자인 토큰 | BOM 없는 UTF-8, 토큰 문법/행간 검사 통과 |
| compileall | tools/tests 통과 |

Python 3.13 [job](https://github.com/inlight37-design/decision-model_lab/actions/runs/35756138070/job/106842262463)에서 전체 로그를 읽었다. 3.12 [job](https://github.com/inlight37-design/decision-model_lab/actions/runs/35756138070/job/106842262035)은 check-run success를 확인했다. 이후 문서 정리 commit의 상태는 해당 PR Checks에서 별도로 확인한다. 이 문서 자신의 미래 commit SHA를 추정해서 쓰지 않는다.

기존 NEXT-SESSION의 75개 검사·59개 근거 표기는 이 검토 후의 현재값이 아니다. 기존 E/F 원장을 변경하거나 근거를 새로 승인한 것이 아니라 실제 기존 원장이 F29까지임을 확인했다.

Node 20 기반 action을 Node 24로 실행한다는 runner 경고가 있었다. 실패는 아니며 이번 변경에서 workflow/action 버전을 임의 업그레이드하지 않았다. 후속 유지보수 항목이다.

## 2. 로컬 새 코드 검사

대화 컨테이너 Python 3.13.5에서 새 테스트 **37개 OK**. GitHub clone은 DNS 해석 실패였으므로 컨테이너는 완전한 저장소 checkout이 아니다. 기존 파일을 모두 재구성했다고 주장하지 않는다. 전체 회귀 판단은 위 원격 CI에 근거한다. 사용자 PC의 C:\\ai 파일·CLI·인증 상태는 확인하지 않았다.

```bash
python -m unittest discover -s tests -p 'test_review_boundary.py' -v
python -m unittest discover -s tests -p 'test_design_contrast.py' -v
```

테스트한 것은 event 순서/epoch/중복, 취소와 종료 구분, UNKNOWN 예산, 봉인 응답 allowlist, quota 관측/미관측/stale 처리, 대비 수식이다. trusted adapter를 가장한 입력을 인증하는 서버, 실제 OS 프로세스의 생존·kill, 영속 저장소, MCP tool 실행은 없다.

## 3. UI 브라우저 smoke

Playwright Python + 컨테이너 `/usr/bin/chromium`의 headless 실행에서:

- 3폭(320/390/1280px) × 4합성 상태 × 2배치 × 2테마 = **48조합**에서 페이지 전체 가로 넘침 없음.
- JavaScript page error **0**, 외부 HTTP(S) request **0**. 시안은 외부 폰트·스크립트를 요구하지 않는다.
- 배치 전환 시 실제 DOM 순서, Enter로 상세 열기, Space로 테마 전환, 종료 불명 상태와 가짜 실행 버튼 부재 확인.
- light/dark/모바일 스크린샷 생성. 데스크톱 시안의 문구와 레이아웃을 시각 확인.

관리형 Chromium이 file:// 경로를 차단해 테스트에는 HTML 내용을 page.set_content로 넣었다. 정책을 비활성화하지 않았다. 파일 탐색기 더블클릭 환경의 동작을 검사한 것은 아니다.

```bash
# 선택 개발 의존성. 주 CI/requirements-design에 자동 추가하지 않았다.
python -m pip install playwright
python -m playwright install chromium
python tools/smoke_review_preview.py
# 시스템 Chromium을 쓰는 환경:
python tools/smoke_review_preview.py --browser /usr/bin/chromium
```

브라우저 smoke는 주 CI에 들어 있지 않다. 정식 UI build/테스트 구조가 정해질 때 버전을 고정해 통합한다. Windows 렌더링, 스크린리더, 모든 focus/대비, 200% 확대, 유저 테스트, XSS/보안 감사를 대신하지 않는다. HTML은 고정 합성 fixture이며 실제 모델 텍스트를 innerHTML로 넣기 위한 구현 예제가 아니다. Python 투영과 HTML은 아직 직접 연결하지 않았다.

## 4. 대비 감사: 알려진 실패가 있다

[contrast-audit.json](contrast-audit.json)은 확인한 token 값으로 계산한 66쌍 중 5쌍의 실패를 기록한다. 기준 token blob은 `c7ca934569ed612c120a111c53310402e518f64c`이다. **기존 디자인 전체 대비 통과라고 보고하지 않는다.**

```bash
python tools/audit_design_contrast.py          # 보고 모드; 실패 쌍도 출력하고 exit 0
python tools/audit_design_contrast.py --strict # 현재 원본에는 실패 5쌍이므로 exit 1 예상
```

주 CI에 추가된 것은 수식 회귀 테스트다. 기존 디자인 발행본과 저장소를 동기화하지 않은 채 원본 팔레트를 바꾸거나, 알려진 실패를 테스트 기대값으로 숨기지 않았다. 새 UI 시안은 독립 미발행 제안이다.

## 5. commit 기록

| Commit | 보존한 결과 |
|---|---|
| `cc511f5966a2e7055797bad6991875bdacf85d8c` | 요청 범위·기기 경계·재개 순서 checkpoint |
| `240067646d4fe8e10c1a665cf44ee423cef66f6e` | 순수 Python 경계 실험과 31개 테스트 |
| `85e3cb1f3641c52278dd1d391fe845024b23b7df` | 비교 UI·대비 감사·6개 추가 테스트·브라우저 smoke |

이후 종합 검토·19개 출처·인수인계 정리는 다음 commit으로 묶는다. 원본 handoff는 blob `b4c0bca6a9f3d8d4093c74db0cb27e3e4733815e` 그대로 루트의 날짜 붙은 파일에 보존한다. 최종 SHA는 PR/커밋 기록에서 확인한다.

## 6. 아직 완료되지 않은 것

실제 provider 연결은 **0건**이다. main PC CLI 인벤토리, 유효 권한·구독 인증·모델 가용성·과금, MCP verifier, 실제 영수증 발행자 검증, crash 복구, 다른 참여자의 파일 접근 방지, 모델 정확도 이득, Q8 화면 우열은 미검증이다. 메인 브랜치와 기존 발행 디자인을 자동 교체하지 않는다.
