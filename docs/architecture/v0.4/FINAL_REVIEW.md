# PR #1 최종 검토 — 2026-09-22

## 판정과 범위

**아래 결함 수정과 검사를 기준으로 연구·설계 저장소의 main 반영에 적합하다.** 실제 다중 provider orchestrator는 아직 구현되지 않았으며, 이 검토는 모델 품질·구독 과금·OS 권한 강제의 검증을 뜻하지 않는다.

검토 시작점은 PR head `87f1845d7e6b70a1fac6d7679b54e34148ff343f`, base `244e8a1b3fef3a43263e9bff416c67f2cfc0b59f`다. 당시 PR은 31 commits/23 changed files이며 main보다 31개 앞서고 뒤처진 commit은 없었다. GitHub가 다시 계산한 mergeable 상태는 true/clean이었다. 이전 조회의 mergeable=false를 실제 충돌로 단정하지 않았다.

사용자가 최종 검토·수정 후 main 병합을 명시적으로 요청했다. 병합 시 검토한 head SHA를 지정하며, 최종 병합 SHA와 상태는 [PR #1](https://github.com/inlight37-design/decision-model_lab/pull/1)에서 확인한다. 문서에 미래 commit을 추정해 적지 않는다.

검토는 해당 commit의 전체 archive를 별도 디렉터리에 내려받아 수행했다. 기존 `C:/ai/decision-model_lab` snapshot은 덮어쓰지 않았다. 변경 파일의 역할·버전 관계, 근거 원장과 결정, 실제 검사 코드·테스트, 기존 PR 리뷰를 읽고 핵심 외부 근거를 아래 범위로 재확인했다.

## 발견한 문제와 수정

| 문제 | 영향 | 수정과 확인 |
|---|---|---|
| 출처 원장과 ADR 연결이 일부 단방향 | 결정에서 출처를 찾는 인계 경로가 불완전함 | D01의 E22, D02의 E11/E15/E17, D10의 F06, D11의 F02를 추가. E06→D01과 F09→D17도 원장에 반영. D01–D18 전체 양방향 일치 회귀 검사 추가 |
| 실패한 check를 claim의 `check_refs`에서 빼면 `supported` 통과 | 같은 기록에 있는 반대 근거를 은폐할 수 있음 | 각 claim이 자신을 대상으로 기록된 모든 check를 참조하도록 강제. 누락 거절과 반대 근거를 보존한 qualified 정상 경로 검사 |
| JSON 중복 키가 마지막 값으로 덮어써짐 | `paid_fallback: true, paid_fallback: false`처럼 상충하는 정책 기록이 통과 | 중복 키를 파싱 단계에서 거절. funding/예산/report 중복 사례를 실제 CLI subprocess로 검사 |
| 비표준·비유한 수가 추가 필드에 남을 수 있음 | JSON 기록의 해석이 parser마다 달라지거나 관측값이 유효한 것처럼 남음 | NaN/Infinity/-Infinity 및 `1e999`의 float overflow를 거절. 직접 validate와 CLI 모두 검사 |
| 현재 안내와 과거 기록의 경계가 불명확 | v0.3을 최신 설계로 읽거나 과거 30개 검사·미병합 상태를 현재로 오해할 수 있음 | v0.4 안내와 역사적 검증 기록을 구분하고 최신 테스트 수·검토 위치 연결. P3 생략 설계와 checker가 지원하는 deliberate 완료 경로의 차이 명시 |

기존 자동 리뷰의 [출처 연결 지적](https://github.com/inlight37-design/decision-model_lab/pull/1#discussion_r4069904438)을 포함한다. 추가 회귀 검사는 수정 전 실패를 재현했고 수정 후 통과했다. 기존 v0.2 schema·fixture·검사 코드는 변경하지 않았다.

## 실제 실행한 검사

환경: Windows, Python 3.12, 저장소 밖 별도 가상환경. `requirements-design.txt`의 `jsonschema==4.26.0`을 설치했다. 최초 시스템 Python 실행의 v0.2 오류는 이 의존성 부재였으며, 설치 후 기존 28개가 통과했다.

```bash
python -m pip install -r requirements-design.txt
python -m unittest discover -s tests -v
python tools/validate_design.py
python tools/validate_v02.py
python tools/check_frontier_protocol.py
python -m compileall -q tools tests
```

| 검사 | 결과와 의미 |
|---|---|
| 전체 unittest | **71개 통과**: v0.2 28개 + frontier/CLI 40개 + 문서 참조 3개 |
| v0.1 `validate_design.py` | **25/25** 오프라인 검사 통과 |
| v0.2 validator / frontier demo | 각 합성 fixture PASS |
| Python 문법 컴파일 | tools/tests 성공 |
| JSON/문서 구조 추가 검사 | JSON 파일·JSON fenced 예제 파싱, fence 균형·UTF-8 replacement 문자 검사 |
| 문서 참조 회귀 검사 | E01–E31/F01–F21 중복·유효 결정 ID, D01–D18 양방향 동일성, Markdown 상대 파일 링크 대상 존재 |

문서 링크 검사는 코드 블록 밖의 inline Markdown 파일 링크를 대상으로 한다. 외부 URL 전수 가용성, 모든 heading anchor, Mermaid 시각 렌더링이나 출처 내용의 진실을 자동 검증하지 않는다. 71은 테스트 메서드 수이며 사용자 과제·모델 호출 수가 아니다. GitHub Actions 실행 기록은 검토 당시 0건이므로 이 결과를 CI 성공이라고 부르지 않는다.

## 근거 신뢰성 재확인

전체 원장 52개 기록의 구조·결정 연결은 검사했으며, 외부 본문은 다음 핵심 자료를 표적 재확인했다. 모든 논문·외부 프로젝트를 재현한 것은 아니다. 원문 URL과 고정 version은 [v0.3 원장](../v0.3/sources.json), [v0.4 원장](sources.json)에 보존한다.

| 재확인 자료 | 확인한 주장과 한계 |
|---|---|
| E02/E03·F17: OpenAI non-interactive/MCP 제거/App Server | exec read-only 기본값, MCP server 제거와 외부 MCP client의 구분. 실제 설치 설정을 확인한 것은 아님 |
| F18: Claude SDK 정책 | 6월 15일 변경 보류 안내가 아래 과거 credit 표보다 우선. 계정별 실제 과금은 미검증 |
| F19: Antigravity headless | workspace 쓰기 허용과 승인 soft-denial 시 exit 0 의미. 실제 OS 격리 시험은 아님 |
| F01/F02/F03: Microsoft·Perplexity | Critique/Council 구분, 세 회사 독립 조사·소수 발견, effort와 지출 상한의 구분. 기능 설명·제작자 보고임을 유지 |
| F04/F05/E22: 고정 commit의 council/PAL/Lite-Harness | 공통 평가 목록·자기 초안 포함, sandbox 우회 preset, startThread/권한 no-op/환경 변수 변경을 정적 코드로 재확인. 설치·실행은 하지 않음 |
| F07/F10/F11/F13/F20 | abstract/판본의 모델 다양성·debate 비교 한계·미합의 보존·judge 편향을 대조. 이번 재확인으로 전체 방법·실험 재현을 주장하지 않음 |
| F08/F12: MoA·debate 실패 논문 | MoA Table 2의 65.1/57.5는 선호 승률이며 사실 정확도가 아님. F12의 실험 모델과 오류 전이 조건을 확인 |
| E16/E19/E21: SWE-Pruner·Switchyard·Fusion | 각각 버전별 해결 수/token, 저가 단독 대비 이득 한계, 해결당 비용과 총지출 증가를 구분한 수치와 해석을 대조 |
| F16/F21: Anthropic compiler/harness 보고 | 대규모 팀의 비용·시험 의존성, 생성/평가 분리와 최종 반복이 최선은 아니라는 한계를 유지 |

대조한 범위에서 핵심 주장과 원문의 모순은 발견하지 않았다. 제품/제작자 결과는 독립 재현으로, abstract 확인은 전체 논문 검증으로 승격하지 않았다. 남은 원장 항목은 기존 inspection/limitations 기록을 유지하며 이번에 모두 다시 읽었다고 주장하지 않는다.

## 남는 한계와 다음 완료 조건

기록의 provider/quality/digest/source-check 상태는 입력의 선언이다. 실제 artifact와 원문을 읽는 resolver, 서명/provenance, 기록 밖의 누락 호출·peer memory 탐지는 없다. 이번 반대 근거 수정도 **기록 안에 존재하는 check의 은폐**를 막는 범위다.

실제 CLI adapter·MCP bridge·구독 한도 계측·과금 차단·sandbox·취소/복구·실제 workload 품질/경제성은 미검증이다. 다음 작업은 [V04-01 inventory → V04-03 두 native 경로의 읽기 전용 pilot](03-evaluation-and-roadmap.md)이다. 이 순서와 미검증 상태를 유지한 채 연구 자료를 main에 통합한다.
