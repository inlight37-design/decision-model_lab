# 병합 뒤 재검토·실제 확인 — 2026-09-24

작성: codex, 사용자 PC `aux-pc`의 Windows와 WSL2 `Ubuntu-24.04`(`aux-pc-wsl`), GitHub 및 실제 IAB Chromium 브라우저. 기준 main은 `eec60e93ef6c95639181eb8cd251506c16290075`다. 사용자는 이번 작업에서 권한·도구 부족으로 미뤘던 실험을 허용했다. 그 범위에서 K46 모델 호출 하나를 승인 장부에 기록하고 실행했다. 화면 검증은 새 시험 전용 원장을 썼으며 기존 사용자 원장은 열지 않았다.

## 결론

**병합과 코드 보존은 확인됐고, 실제 브라우저 확인과 K46 관측을 보완했다.** 새로 재현된 결함은 Windows 출력 리디렉션에서 inventory dry-run이 종료되는 인코딩 문제이며 작은 수정과 회귀 시험으로 처리했다. 실행 계약 G4·G6과 Codex 문맥 C3는 남았다. 현재 화면 서버는 계속 모의 실행기만 사용한다.

- **GitHub:** #22–#27 병합, #22→#23→#24→#25 부모 연결, 정확한 PR head의 Python 3.12·3.13 push CI 성공을 확인했다. 재검토 시작 시 원격 브랜치는 main뿐이고 열린 PR은 없었다. [상세 SHA·실행 링크](GITHUB.md)
- **표현 정리:** #25 head와 완전히 같은 Git 트리는 문서 정리 전 통합 커밋 `fbb7225eaeec72360731d58db214da7375411375`다. 현재 main은 문서만 다르며 코드·시험은 동일하다. 기존 CI 링크는 PR 합성 merge 실행이었으나, 같은 head의 push 실행도 성공했고 실제 checkout SHA까지 대조했다.
- **실제 화면:** 모의 실행→봉인→공개→합성, A/B 배치, 작은 화면, 수동 입력 거절·수용과 일부 브라우저 보안 경계를 확인했다. 다운로드 완료와 취소 확인창 클릭 성공은 확인하지 못했다.
- **K46:** 현재 설치 버전의 실제 고정 helper에서 쓰기와 인증 파일 열기 거절을 확인했다. C3는 `failed`, Codex 실행 허가는 `false`를 유지한다.

## 반영과 구조 판단

| 범위 | 주인 모듈 | 부류 제거·국소 수정 | 이번 결과 |
|---|---|---|---|
| Windows inventory 출력 | `tools/runtime_inventory.py` | 국소 수정 | CLI 진입점에서 stdout/stderr를 UTF-8로 설정. CP949 파이프 실행 반례를 회귀 시험으로 고정 |
| G4 계획·기록·실행 일치 | `app/cli_executor.py`, `core/adapters.py` | 부류 제거 제안 | `describe`와 `execute`의 재계획을 불변 계획 하나로 대체하는 설계. 아직 미구현 |
| G6 모의/실제 출처 | `app/controller.py`, `app/store.py` | 부류 제거 제안 | 현재 executor 객체가 아닌 시도별 영속 출처로 화면·보고를 파생하는 설계. 아직 미구현 |
| K46 관측·허가 구분 | `tools/w2/observe.py`, `core/eligibility.py` | 기존 경로 관측 | 기존 수용 관문으로 실제 결과를 확인하고 새 관측 사본에 전송·권한만 갱신. 문맥 판정·허가 정책 유지 |

가림의 `Bearer token` 과잉 가림은 안전한 쪽의 기존 동작으로 남겼다. 이번 검토에서 가림 범위를 느슨하게 바꾸지 않았다. main 보호는 `protected=false`, repository rulesets는 비어 있었다. 필수 CI 검사를 보호 설정으로 강제하는 것을 권고하며 설정은 변경하지 않았다.

## 직접 실행한 오프라인 검증

기준 main `eec60e93ef6c95639181eb8cd251506c16290075`에서 Windows Python 3.12.6과 WSL Python 3.12.3의 전체 시험이 성공했다. 양쪽 모두 `jsonschema==4.26.0`을 사용한 결과를 최종 근거로 삼았다. Windows의 skip은 Linux 전용 경로, WSL `DML_REQUIRE_BWRAP=1`의 유일한 skip은 Windows 레지스트리 시험이다. 로컬 Python 3.13은 실행하지 않았으며 원격 CI로 별도 확인했다.

인코딩·디자인 토큰·frontier protocol·inventory manifest·v0.1/v0.2 계약·근거 원장·compileall 검사도 양쪽에서 성공했다. WSL 시스템의 기존 jsonschema 판은 고정 요구와 달라, 전역 환경을 바꾸지 않고 임시 venv에 고정 의존성을 설치한 뒤 다시 검증했다. Windows `python -S`로 설치 전 표준 라이브러리 경로도 확인했다.

**새 인코딩 반례:** `PYTHONIOENCODING=cp949`와 파이프 출력에서 inventory dry-run의 em dash가 `UnicodeEncodeError`를 일으켰다. CLI 진입점의 UTF-8 설정 뒤 실제 subprocess로 성공과 한글·기호 보존을 확인했다. 수정본 inventory 시험과 최종 통합 전체 시험은 Windows·WSL 모두 성공했고 `git diff --check`도 성공했다. 최종 수정본에서도 Windows는 Linux 전용 경로만, WSL 필수 bubblewrap 모드는 Windows 레지스트리만 건너뛰었다. GitHub에 올린 정확한 head의 CI 결과는 이 변경 PR의 Checks와 본문에서 확인한다.

## 실제 브라우저와 HTTP 확인

Windows의 새 시험 서버를 IAB Chromium에서 열었다. 모의 CLI 참여자가 답을 봉인한 뒤 공개하고 모의 합성을 저장하는 흐름을 실제 화면에서 진행했다. 이 화면 동작은 공급자 모델 호출이 아니다.

| 확인 | 관측 결과 | 범위 |
|---|---|---|
| Q4 A/B | 1280×900과 390×844에서 두 배치 확인. 작은 화면의 viewport 390, 문서 내용 폭 375로 문서 전체 가로 넘침 없음 | 해당 Chromium·시험 결과의 시각 확인. 접근성·모든 화면 크기·교차 브라우저 검증은 아님 |
| 수동 전달 | 다른 실행 표식은 `manual_refused`, 올바른 표식은 수용. 수용 뒤 독립 0·미확인 1 표시 | 합성 문자열 사용. 원본 앱 사용·입력 전체 소비·독립성 증명은 아님 |
| 교차 출처 | 다른 localhost 포트의 페이지에서 단순 GET과 Authorization 사전 요청 모두 브라우저 `TypeError`, iframe 표시 거절 | 실제 서로 다른 출처의 브라우저 요청으로 확인한 범위 |
| API 인증·출처 | 인증된 요청의 잘못된 Origin/Host는 403, 토큰 없는 요청은 401 | 해당 요청을 HTTP로 직접 확인 |
| 보고 API | 공개 결과 200, `a1-draft-report/2` 및 `a1-decision-report/1` JSON 확인 | API JSON 회수 확인 |
| 취소 | HTTP 취소 200, 취소 뒤 보고 409, 새 브라우저 탭에서 영속 취소 상태 표시 | 취소 버튼의 native confirm 자동화는 CDP 대기로 멈춰 새 탭으로 복구. 클릭 경로 성공으로 기록하지 않음 |
| 다운로드 | 버튼 뒤 console 오류 없음. 다운로드 이벤트는 3초 안에 오지 않았고 파일 저장을 확인하지 못함 | 다운로드 완료는 미확인. API 보고 성공으로 대체 주장하지 않음 |

**Q4 권고는 A(결정 우선)**다. 판단 이유와 조건을 먼저 읽고 근거 대조로 내려가는 순서가 첫 화면에 적합해 보였다. 이는 이번 화면 검토의 제안이며 사용자 선호 실험이나 최종 선택이 아니다. Q4 상태는 `unresolved`로 둔다. 디자인 토큰과 발행 아티팩트는 변경하지 않았다.

시각 근거: [A 데스크톱](q4-a-desktop.png), [B 데스크톱](q4-b-desktop.png), [A 좁은 화면](q4-a-mobile.png), [B 좁은 화면](q4-b-mobile.png). 모두 합성 시험 데이터이며 URL fragment 토큰은 이미지에 없다. 일반 Edge 연결도 시도했으나 도구가 `Browser is not available: edge`를 반환해 교차 브라우저 검증은 진행하지 못했다.

## K46 실제 관측과 남은 C3

[새 관측 기록](../../experiments/w2-isolation/2026-09-24-k46-confirmation/README.md)과 [공개 요약](../../experiments/w2-isolation/2026-09-24-k46-confirmation/summary.json)에 고정 필드만 남겼다. 실제 원 출력·세션 ID·임의 파일 이름·계정 식별자는 공개 기록에 넣지 않았다.

- WSL Codex 0.156.1에서 `discussant-2`, 요청 모델 `gpt-6-luna`, 구독 경로로 한 번 실행했다. 승인 상한 Codex 1·Claude 0을 한 번 기록했고 Codex 1회를 모두 썼다. 추가 호출이나 예산 초기화는 없었다.
- 고정 helper는 `write=denied:EROFS`, `input=ok`, `auth=denied:EACCES`를 반환했다. 이번 nonce의 완료 명령 하나와 결과를 대조했고 `k46.verified=true`, `gate=ok`, `boundary_violations=[]`, `as_expected=true`였다. stdin 전달 및 PID namespace 전체 자손 종료도 확인했다.
- 이는 이 버전·구성·고정 명령의 실제 집행 관측이다. 모든 유출 경로·네트워크·토큰 갱신·실제 controller/server 연결을 검증한 것은 아니다. CLI가 제공 모델을 보고하지 않아 실제 모델 일치도 미확인이다.
- 새 manifest 사본의 Codex 전송·권한만 갱신했다. 문맥은 `failed` 그대로이며 새 사본으로 허가를 계산해도 `context_conformance is failed` 때문에 `eligible=false`다.

앱 도구 캐시·플러그인 metadata 변경과 큰 입력 토큰 수는 추가 조사가 필요한 단서다. 어떤 내용이 모델 문맥에 들어갔다는 증명도, 없었다는 증명도 아니다. C3의 다음 단계는 **최종 지시문·도구·스킬을 모델 전달 직전에 확인할 수 있는 진단이 있는지**부터 조사하는 것이다. `--ignore-user-config` 하나로 계정 플러그인·원격 MCP·스킬까지 없어진다고 가정하지 않는다. 관측 구성을 바꾸면 새 계약 변형으로 다룬다.

## 순서 5: 실행 계약 설계 제안

G4·G6은 모델 호출 없이 다시 재현했다. Claude의 공통 자료 유무에 따라 argv가 달라져도 같은 `discussant-1`이다. `describe()`와 `execute()`는 계획을 각각 만들며, 관측 b1과 `--keep-session`은 prepare 뒤 argv를 바꾸기도 한다. controller는 실제 실행 함수를 부르지 않은 대체 executor에도 모의 문구를 표시하고, 과거 실행의 보고 출처를 현재 executor에서 읽는다. 현재 모의 전용 서버에서는 표시가 맞지만 K17 연결 전에 계약을 완결해야 한다.

권고는 기존 `prepare()`와 실행기 인터페이스를 다음처럼 정리하는 것이다. **아직 설계 제안이며 사용자 결정 전 구현·기존 증거 승격을 하지 않았다.**

1. **최종 불변 계획을 한 번 만든다.** 요청 모델, 실제 최종 argv, 입력 매핑, 실행 파일/설치 버전, 격리 연결, stderr 판정 표식, 실행 종류를 고정한다. 관측 변형도 이 단계 전에 적용한다. controller는 이 계획의 안전한 기록을 시도 ID와 저장한 뒤 같은 객체를 실행한다. 기록 실패 시 실행하지 않고, 실행 직전 허가를 재확인해도 argv는 다시 만들지 않는다.
2. **판은 정규화한 실행 틀과 정책을 식별한다.** argv 전체를 그대로 hash해 매 시도마다 관측을 무효화하지 않는다. 질문·임시 경로·run ID·nonce는 계약 판에서 제외하고 역할로 치환한다. 자료 유무, 출력 변형, profile·sandbox, 세션 보존, 연결 역할과 ro/rw 정책처럼 실행 의미가 다른 부분은 구분한다. 실제 값·입력 hash는 시도 계획에 별도로 고정한다. 요청 모델도 계획·결과의 명시적 식별자로 보존하며, 모델별 관측 분리 여부는 판 정책에서 정한다.
3. **옛 증거는 명시적으로 대응시킨다.** `discussant-1/2`를 새 fingerprint로 자동 승격하지 않는다. 최종 argv·변형·격리 정책·설치 버전의 증거를 검토해 대응표를 만들거나 다시 관측한다. K46 성공도 모든 새 변형의 호환성을 뜻하지 않는다.
4. **실행 종류는 시도에 영속화한다.** `mock`/`real`/`synthetic`/`unknown`을 저장하고 화면·보고는 그 기록을 읽는다. 재시작 뒤 현재 executor가 과거 출처를 바꾸지 않게 한다. 복원 근거 없는 옛 행은 `unknown`으로 둔다. controller의 `MockExecutor.FLAVOR` 의존과 고정 모의 문구를 함께 없앤다.

## 남은 결정·작업

| 항목 | 권고 또는 다음 행동 |
|---|---|
| Q4 | A를 기본 후보로 권고. 사용자가 A/B 최종 선택 |
| 실행 계약 판 | 위 정규화·변형·옛 증거 대응 정책 결정 후 G4/G6 구현, 그 뒤 K17 |
| C3·Claude 문맥 | 증거 기준을 유지하고 지원되는 진단을 먼저 조사. 정책 완화는 별도 명시 결정이며 `observed`로 바꾸지 않음 |
| K09 | K46 관측을 바탕으로 최소 인증·설정 연결을 설계하고 해당 새 구성에서 재관측 |
| 브라우저 잔여 | 실제 다운로드 파일 저장과 취소 확인창 클릭 완료, 접근성·교차 브라우저 확인 |
| main 보호 | 필수 상태 검사 적용 여부 결정. 이번 설정 변경 없음 |

운용 PC, agy/B4, 실제 모델 합성·품질·B3 사용량 비교, 실제 실행기의 서버 연결은 이번 확인 범위 밖이다. 현재의 오프라인·브라우저·K46 성공을 이 항목들의 성공으로 확대하지 않는다.
