# PR #22–#25 병합 검증 — 2026-09-24

작성: claude 세션, `aux-pc`(hostname `DESKTOP-L6EA2UJ`)의 Windows Python 3.12.6과 WSL `aux-pc-wsl` Ubuntu-24.04 Python 3.12.3. GitHub CLI 로그인 상태로 PR·CI를 직접 읽었다. 모델 호출, 실제 인증 폴더 연결, CLI 설치·로그인 재관측은 하지 않았다. 사용자가 이 세션에서 "확인하고 병합하고 정리해서 문서화하라"고 지시했다.

기준 main: `34975794dec2a45b9fd8a11f3133d2b202ebb8ee`. 구현 판단과 codex가 검토 중 고친 결함은 [codex 검토 기록](../2026-09-24-offline-progression/README.md)에 있고, 이 기록은 병합 전 확인과 병합 방식만 다룬다.

## 대상

| PR | 순서 | 브랜치 | 검증한 head | CI(정확한 head) |
|---|---|---|---|---|
| [#22](https://github.com/inlight37-design/decision-model_lab/pull/22) | 1 공유 가림·실행 허가·원장 기본 정책 | `codex/shared-policies-20260924` | `5f3a856ab2d089511786ddeb0203809885a2aacf` | [offline-checks](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960132984) 3.12·3.13 성공 |
| [#23](https://github.com/inlight37-design/decision-model_lab/pull/23) | 2 격리 연결 모델 | `codex/mount-model-20260924` | `6617ce5ede44d96b7f42e76e0417c145435612a9` | [offline-checks](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960254902) 3.12·3.13 성공 |
| [#24](https://github.com/inlight37-design/decision-model_lab/pull/24) | 3 참여자 상태·파생 gate | `codex/participant-gate-20260924` | `c0b5e18620185e62f4c2307eaef705df31b00393` | [offline-checks](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960299252) 3.12·3.13 성공 |
| [#25](https://github.com/inlight37-design/decision-model_lab/pull/25) | 4 모의 합성·원문 대조·결정 카드·Q4 미리보기 | `codex/mock-decision-20260924` | `e053d0de35f71396d701020e43a032e2c43dc806` | [offline-checks](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960752930) 3.12·3.13 성공 |

## 병합 방식과 이유

네 브랜치는 차례로 쌓여 있었다. 그런데 "공개 검사 정렬·짧은 실행 ID 충돌 방지" 수정이 #22·#23·#24에 서로 다른 커밋(`5f3a856`, `6617ce5`, `c0b5e18`)으로 따로 들어가 있었다. 그래서 #23은 #22의 head를, #24는 #23의 head를 품지 않았다. #25만 #24의 head를 병합으로 받아 두었다.

그대로 GitHub에서 순서대로 병합하면 #22 뒤의 #23과, #23 뒤의 #24가 `NEXT-SESSION.md` 3절에서 충돌했다. 임시 worktree에서 재현해 확인했다. 코드 파일은 충돌하지 않았고, 병합 결과의 코드는 각 PR head와 바이트까지 같았다. 다른 세션의 브랜치에는 push하지 않으므로([협업 규칙](../../COLLABORATION.md) 2절 5) 다음과 같이 처리했다.

1. 통합 브랜치 `claude/merge-offline-progression-20260924`를 main에서 만들고, #22 → #23 → #24 → #25를 순서대로 `--no-ff` 병합했다. 커밋 제목은 저장소 관례대로 `Merge PR #N <브랜치>: …`로 달았다.
2. 충돌한 `NEXT-SESSION.md`는 매번 뒤 브랜치 판을 택했다. 뒤 판이 앞 판을 이어 쓴 인계이기 때문이다. 이렇게 푼 병합 커밋 본문에 그 사실을 적었다.
3. 네 병합 뒤의 트리는 #25 head `e053d0d`의 트리와 **같다**(`git rev-parse HEAD^{tree}` 비교). 따라서 main에 들어가는 코드는 CI가 통과시킨 트리 그대로다. 네 PR의 head는 모두 통합 브랜치 이력에 있다.
4. 그 위에 인계 갱신과 이 기록을 한 커밋으로 더했다. 통합 PR [#26](https://github.com/inlight37-design/decision-model_lab/pull/26)의 CI 녹색을 확인한 뒤 병합 커밋으로 병합했다.

codex PR 네 개는 draft였다. 처음 연 세션은 Codex 자동 리뷰의 사용량 결정을 기다리느라 draft로 두었다. 준비 완료로 바꾸지 않고 통합 PR로 병합했다.

## 확인한 것

- **CI:** 위 표. 각 CI 실행의 `headSha`가 PR head와 같음을 `gh run view`로 대조했다.
- **로컬 전체 시험:** 병합 트리와 같은 `e053d0de35f71396d701020e43a032e2c43dc806`에서 다음을 실행했다.
  - Windows `python -m unittest discover -s tests`: 성공. skip은 Linux 전용 시험뿐이다.
  - WSL `DML_REQUIRE_BWRAP=1 python3 -m unittest discover -s tests`: 성공. skip은 Windows 레지스트리 시험 하나뿐이다.
  - skip을 통과로 세지 않는다.
- **코드 검토(읽고 따라간 것):**
  - `core/isolation.py`의 연결 모델: 옛 검사 다섯 가지가 새 규칙 셋(덮음, 안쪽 권한 확대, `never` 겹침)에 모두 포함된다. 옛 검사는 루트 연결, HOME과 그 위 연결, 작업 폴더와 읽기 전용 입력의 관계, 작업 폴더가 다른 연결을 품음, `never`와 시스템 연결의 겹침이었다. 읽기 전용 경로가 쓰기 경로의 조상이면 이전에는 조용히 덮였지만 이제는 거절된다.
  - `core/eligibility.py`에서 지운 중복 검사(근거 없음, 날짜 형식, 설치 버전 없음)는 `row_problems`가 모두 잡는다.
  - `app/state.py`·`app/controller.py`: 모든 참여자 전이가 `_transition` 한 곳에서 기대 상태와 시도 ID(`attempt IS ?`)를 함께 조건으로 쓴다. 공개 시점에는 모든 참여자가 끝난 상태여야 한다. 그래서 공개 사건의 초안 수(요청 − 탈락)는 수용된 초안 수와 같다. `synthesize()`는 잠금을 쥔 채 `view()`를 부르지만 두 잠금 모두 `RLock`이라 교착이 없다.
  - `app/store.py` 스키마 4 이전: 단계가 없거나 잘못된 옛 실행을 만나면 거래 전체를 롤백한다. 모호한 실행을 공개 전 단계로 되돌리지 않는다.
  - `app/synthesis.py`·`app/report.py`: 원문 오프셋·실행 ID·저장 해시를 대조한다. 모든 주장은 `unresolved`, 사실 검사는 `not_performed`다. 봉인 해시와 다른 공개 초안은 보고서로 내보내지 않는다.
  - `app/static/index.html`: 새 표·카드도 `h()`로 만들고 문자열은 텍스트 노드로만 넣는다(`innerHTML` 없음).
- **인계 2절·5절:** 병합 전후로 main의 원문과 같다.

## 발견

| 번호 | 무엇 | 판단 |
|---|---|---|
| M1 | 쌓인 브랜치에 같은 수정을 층마다 따로 커밋해, 순서대로 병합하면 인계 문서가 충돌했다 | 병합 방식으로 해결했다. 다시 막기 위해 [협업 규칙](../../COLLABORATION.md) 2절 5에 "아래 층에 고치고 위 층은 병합으로 받는다"를 더했다 |
| M2 | `tools/redaction.py`의 `Bearer` 패턴이 최소 길이 20자 조건을 잃었다(옛 `runtime_inventory.py`에는 있었다). help 문장의 "Bearer token"처럼 평범한 두 단어도 `<redacted>`가 된다 | 더 많이 가리는 쪽이라 안전 문제는 아니다. help 원문 증거가 조금 덜 읽힐 뿐이다. 병합을 막지 않고 인계 4절의 낮은 우선순위 후보에 넣었다 |
| M3 | 인계 머리말은 hostname `DESKTOP-L6EA2UJ`를 썼고 0절은 `aux-pc`라는 이름을 쓴다 | 이 세션이 OS 판·Windows Python 판·gh 경로·저장소 경로·WSL 배포판이 aux-pc 기록과 같음을 보고 같은 기기로 적었다. hostname 자체는 aux-pc 기록에 없다 |

병합을 막는 결함은 찾지 못했다.

## 확인하지 않은 것

- 실제 브라우저에서 본 Q4 두 배치·390px·다운로드. codex 세션도 이 세션도 브라우저로 보지 않았다(K27).
- 실제 모델 합성·품질, 실제 CLI 인증·문맥·실행 허가, K46·C3.
- 다른 기기(운용 PC)와 CI 밖의 Linux 배포판.

## 병합 뒤

- 인계 3절의 "진행 중" 줄을 지우고 병합 기록으로 바꿨다. 1·4절의 "이 브랜치" 표현을 main 기준으로 고쳤다. 순서표 1–4를 완료로 표시했다. 다음은 순서 5(실행 계약 판 설계)와 K46·C3 결정이다.
- 통합 PR로 들어간 codex 브랜치 넷은 GitHub의 자동 삭제 대상이 아니므로 병합한 이 세션이 원격에서 지운다([협업 규칙](../../COLLABORATION.md) 5절 6).
