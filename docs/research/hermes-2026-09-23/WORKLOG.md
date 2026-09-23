# Hermes 패턴 선별 조사 — 작업·검증 기록

2026-09-23 (Asia/Seoul) · ChatGPT 웹 세션 · [PR #5](https://github.com/inlight37-design/decision-model_lab/pull/5)

## 요청과 결과

사용자는 `NousResearch/hermes-agent`에서 우리 프로젝트가 가져올 만한 것을 꼼꼼하게 분석하고 GitHub에 문서로 남기도록 요청했다. 이에 날짜 고정 [요약](README.md), [상세 분석](ANALYSIS.md), [적용 계획·수용 시험](ADOPTION_PLAN.md), [근거·검토 범위](EVIDENCE.md)를 작성했다. 루트 README 탐색 링크와 `NEXT-SESSION.md` 인계를 같은 PR에서 갱신했다.

이번 변경은 조사·설계 제안이다. Hermes 설치, 사용자 PC 변경, 실제 모델 호출, provider 추가, 런타임 코드 변경, main 직접 변경/병합은 수행하지 않았다.

## 고정한 판본

- 우리 저장소 시작점: `0865e3d9493c36921e94c01ad9f6c803a6d78363` (`main`).
- Hermes 관측 시작점: `c0d7294769a38c17ceae51d8f7995e66e1dcae27` (`main`, commit 시각 2026-09-23T04:02:02Z).
- 조사 브랜치: `chatgpt/hermes-patterns-20260923`.
- 시작 시 열린 PR 목록은 비어 있었다. 원격 브랜치에는 병합된 과거 작업 브랜치가 남아 있었다. 목록과 기존 인계를 확인했다.

## 유지한 전제

한 제품을 통째로 채택하지 않는다. Python 코어·native 구독 CLI·exec 우선, 유료 API 자동 전환 금지, 구성 축소 명시, blind 첫 초안·읽기 전용 논의자·단일 writer·미합의 보존을 유지한다. 보조 PC 기록은 기존 claude 세션의 관측으로 남겼다. 기존 D/E/F 원장, review 원문, design source/발행 아티팩트는 변경하지 않았다.

이번 Hermes 조사는 사용자가 별도로 요청한 연구다. 기존 V04-03 실측 우선순위를 바꾸거나 새 아키텍처 판본을 선언하지 않는다. 새로운 `H` 근거와 `HP` 작업 ID는 조사 내부 표기다.

## 접근 환경

GitHub 커넥터로 고정 commit의 문서와 코드를 읽었고 공개 공식 안내와 대조했다. 웹 컨테이너에서 일반 Git clone을 시도했으나 DNS 해석 실패로 checkout을 얻지 못했다. 따라서 로컬 전체 저장소 테스트를 실행했다고 주장하지 않는다. 문서 변경의 자동 검사는 GitHub Actions에서 확인했다.

사용자 PC·설치 CLI·인증 파일·구독 잔량은 이번 세션에서 관측하지 않았다. 연결된 로컬 worker 도구의 호출에 필요한 세션 token도 제공되지 않았으므로 이를 지어내거나 사용자 PC 실행에 사용하지 않았다.

## 체크포인트

### 방향과 판본 고정

프로젝트 `README.md`, `NEXT-SESSION.md`, `AGENTS.md`, `docs/COLLABORATION.md`, 원격 브랜치와 열린 PR, Hermes README/architecture를 먼저 확인하고 작업 기록을 커밋했다. Hermes의 자체 AIAgent와 native 하네스를 보존하는 우리 controller의 책임 차이를 조사 기준으로 삼았다.

### 주요 소스 대조와 문서 작성

스킬, frozen memory, 실제 session search, delegation 생성/수명주기, Codex App Server session/transport, MoA config/reference/accounting, provider/보조 호출/fallback 안내, 압축/저장/MCP/보안/라이선스를 기능별로 검토했다. 우리 `review_boundary.py`의 기존 순수 함수와 접점을 확인했다. 파일·범위·locator와 미검토 부분은 EVIDENCE에 명시했다.

요약·근거·상세 분석·적용 계획을 별도 커밋으로 보존했다. session search의 LLM/잘림 설명, native runtime 분류, MoA 주기·자료 범위 등 문서와 코드가 다른 지점을 별도로 기록했다. 제작자 benchmark를 우리 성능 향상으로 전이하지 않았다.

### PR·탐색·인계

[PR #5](https://github.com/inlight37-design/decision-model_lab/pull/5)를 생성했다. README에 날짜 고정 조사 링크를 추가하고, NEXT-SESSION에 열린 PR/브랜치·후속 시험 순서를 남겼다. 기존 환경 기록의 작성 주체를 명확히 했으며 해당 실험 결과 자체는 수정하지 않았다.

변경 파일 목록과 NEXT-SESSION patch를 확인했다. 문서 이외의 변경은 없으며, 과거 실험/리뷰 결과나 Windows 경로를 일괄 재작성하지 않았다. main 병합은 수행하지 않는다.

## 자동 검사 관측

**2026-09-23 확인한 문서 완성 체크포인트:** `6d6a99a145611d03a267f0a5bd1e3fca4373b01b`.

[GitHub Actions 실행](https://github.com/inlight37-design/decision-model_lab/actions/runs/35824579921)의 Python 3.12/3.13 job step 결과를 읽어 다음 단계의 `completed / success`를 확인했다.

| 검사 단계 | 관측 |
|---|---|
| text encoding / design tokens | 성공 |
| stdlib frontier checker / runtime inventory | 성공 |
| v0.1 contracts / v0.2 pilot-proof | 성공 |
| evidence registry schema | 성공 |
| full test suite / compile | 성공 |
| current code hashes 기록 | 성공 |

- [Python 3.12 job](https://github.com/inlight37-design/decision-model_lab/actions/runs/35824579921/job/107063432722)
- [Python 3.13 job](https://github.com/inlight37-design/decision-model_lab/actions/runs/35824579921/job/107063432926)

이는 우리 저장소의 기존 CI가 해당 변경판에서 성공했다는 뜻이다. 모든 외부 URL의 내용·모든 주장 의미·Hermes 전체 구현·실제 native 권한을 검증했다는 뜻이 아니다. 이 기록을 담은 후속 commit의 최종 CI는 **PR 본문의 고정 head SHA·실행 링크와 checks**를 기준으로 한다. 과거 green을 다른 head에 재사용하지 않는다.

## 수행하지 않은 것

Hermes 설치와 upstream 테스트, 모델 호출, 실제 Windows 프로세스 트리/ACL 시험, native 문맥·권한 conformance, MCP 설치·실행, 구독/과금 실측, benchmark 재현, UI 렌더링, 전체 코드·보안·의존성·라이선스 감사는 하지 않았다. 수용 시험 표는 앞으로 구현할 fixture이며 이번에 통과한 시험 목록이 아니다.

## 다음 세션

PR 변경과 해당 head의 CI를 검토하고, 저장소의 병합 권한 규칙에 따라 처리한다. 병합 시 NEXT-SESSION의 진행 중 PR 상태도 갱신한다.

실제 개발은 기존 V04-03 준비부터 이어간다. HP-01/02/03을 mock runner·native 문맥/권한·회계 시험에 반영하고, 스킬/recall/lesson/MCP/MoA/DB/App Server는 pilot 후 필요한 후보만 단계적으로 적용한다. 이 연구 문서 전체를 참여 모델의 공통 prompt에 자동 주입하지 않는다.
