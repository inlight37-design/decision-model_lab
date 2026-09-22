# v0.4 검증 기록과 한계

검사일 **2026-09-22**, Asia/Seoul. 이 문서는 실제로 수행한 작업만 기록한다. '설계됨', '기록 검사 통과', '모델 성능 검증', '운영 안전성 검증'은 서로 다른 상태다.

## 1. 실제 실행한 오프라인 검사

환경: 대화 컨테이너, **Python 3.13.5**. 작업 위치는 `/mnt/data/decision_model_work/snapshot`이며 사용자 PC나 Git checkout이 아니다. GitHub clone/raw 다운로드는 DNS 해석 실패였으므로 원격 읽기·게시에는 GitHub connector를 사용했다.

| 검사 | 실행 결과 |
|---|---|
| `python tools/check_frontier_protocol.py` | 내장 합성 완료 기록 PASS |
| `python -m unittest discover -s tests -p 'test_frontier_protocol.py' -v` | **30 tests, OK** |
| `python -m py_compile tools/check_frontier_protocol.py tests/test_frontier_protocol.py` | 문법 컴파일 성공 |
| CLI에 정상 합성 JSON 파일 전달 | exit 0 |
| CLI에 required_participants가 맞지 않는 합성 JSON 전달 | exit 1 |
| CLI에 깨진 JSON 전달 | exit 1 |

테스트의 주요 범위는 참여자/공급자 중복, quorum 부족, 상급 profile의 조용한 하향, peer 노출, 입력 snapshot 불일치, 자기 평가, dangling 참조, blind barrier 이전 검토, 호출/라운드 초과, 실패한 재시도의 비용 누락, funding flag, 근거 binding, vote/skip의 통과 승격, 검증 log 누락, 반례 은폐, unresolved 누락, 종료 불명 호출, 거절된 review coverage다. 허용 예산을 명시적으로 늘린 재시도와 토론 없는 cross_check의 정상 경로도 검사했다.

`30`은 unittest의 테스트 메서드 수다. 여러 실제 모델이나 30개 사용자 과제를 실행한 수가 아니다. 내장 예시의 source check와 digest는 가짜다. source log가 존재한다고 검사했다는 뜻도 아니다.

## 2. 검사한 코드와 게시한 코드의 동일성

로컬 UTF-8 byte로 Git blob SHA-1을 계산한 뒤 GitHub `fetch_file`의 blob SHA와 대조했다. Git blob 해시는 `blob <byte_length>\0<content>`에 대한 SHA-1이며 일반 파일 SHA-1과 다르다.

검증한 원격 snapshot: `8025e1dde0195f3a0992f8a65fada4545e438eda`.

| 파일 | byte 수 | 일치한 Git blob SHA |
|---|---:|---|
| `tools/check_frontier_protocol.py` | 9970 | `ac5ea12a9b0ba980a2869aac30b7881baee380fe` |
| `tests/test_frontier_protocol.py` | 4825 | `51126c641e44899c53392b5af2143ea2d4365202` |

따라서 **이 두 파일**은 로컬에서 검사한 내용과 원격 내용이 동일하다. 모든 새 문서의 byte hash까지 자동 대조했다고 확대하지 않는다. 문서 링크 전체나 source JSON 전체를 컨테이너에 내려받아 자동 검사한 것은 아니다.

## 3. Git 변경 범위

시작 head `634d34b2b6639ef60bd6469190cec053826b4385`와 문서 정리 head `407eb9e029404430c56de4c465b58a574a179dfe`를 GitHub compare로 확인했다. 이 구간은 12개 commit, 변경/추가 파일 11개다. 수정한 기존 파일은 root README, AGENTS, architecture 버전 지도이고 나머지는 새 v0.4 문서와 두 Python 파일이다. 이 기록과 최종 HANDOFF 저장은 뒤이은 문서 commit이다.

기존 `contracts/v0.2`, 기존 examples/tests/tools와 v0.1–v0.3 상세 문서의 변경은 위 비교에 없다. 기존 v0.2 검사 전체는 이번 환경에서 재실행하지 않았다. 새 tests 파일을 추가했다는 것과 기존 테스트 파일을 수정했다는 것을 구분한다.

PR #1은 조사 시 open, merged=false였고 같은 head branch를 가리켰다. 조회 결과 mergeable=false가 반환되었으나 그 원인을 검사하지 않았다. 충돌이라고 단정하지 않으며 자동 merge/rebase를 수행하지 않는다. GitHub Actions/CI 성공을 확인했다는 주장도 하지 않는다.

## 4. 조사 근거의 검증 수준

F01–F21의 원문 URL, publication/revision과 확인일, 살펴본 section, 한계, 관련 D10–D18을 [sources.json](sources.json)에 기록했다. 구체적으로 다음 경계를 유지한다.

- 제품 문서는 제공 방식의 근거다. Microsoft의 성능 수치는 제작자 보고, Perplexity의 독립 조사/합성은 기능 설명이며 이 저장소의 품질 실험이 아니다.
- Karpathy council은 commit에 고정한 `backend/council.py` 1–200행과 README를 검토했다. PAL은 clink/consensus 문서와 고정 commit의 Codex preset을 읽었다. 실행·설치·전체 코드 보안 감사는 하지 않았다.
- F09/F10/F11/F20은 abstract 수준 주장만 사용한다. F10 연결 PDF 접근과 Microsoft의 연결된 상세 기술 글 접근은 실패했다. 미확인 표에서 숫자를 가져오지 않았다.
- ReConcile/MoA/F12/F13은 HTML의 관련 방법·실험·한계 부분을 읽었다. 논문의 모든 증명·부록·실험을 재현한 것은 아니다.
- 메타데이터 후속 확인에서 F11의 전체 제목, F13의 정확한 제목과 2026-04-29/v1 이력을 원장에 반영했다. ReConcile의 자신감 재가중을 우리 workload의 검증된 calibration으로 오해하지 않도록 한계를 명확히 했다.
- Codex/Claude SDK/Antigravity 문서는 2026-09-22 재확인했다. 공식 설명이 실제 사용자 설치/설정/구독 상태를 증명하지는 않는다.

검색·커뮤니티는 발견 경로다. 읽지 못한 후기나 검색 snippet을 검증된 성과로 바꾸지 않았다. 21개 기록 중 세 개는 기존 E 근거의 재확인이며 21개의 새 독립 실험이 아니다. 인터넷 전체의 사례 전수 조사, 전체 참조의 자동 링크 검사, 모든 논문의 완전 검증을 주장하지 않는다.

## 5. checker가 보장하지 않는 것

이 프로그램은 `frontier-record-experiment/0`라는 **축소된 합성 완료 기록**만 검사한다. 일반적인 runner/JSON Schema/security validator가 아니다. 알 수 없는 추가 필드의 의미를 해석하지 않으며 설계의 모든 field/state/permission을 구현하지 않는다.

participant의 provider/quality, 입력 digest, source check의 passed 표시는 모두 입력 기록의 선언이다. 이를 실제 계정·모델·파일·원문과 대조하지 않는다. `supported` 처리의 외부 검사 참조 조건은 형식적 최소값일 뿐 근거의 충분성·정확성을 자동 판정하지 않는다. `source`라고 이름 붙인 가짜 증거를 진짜로 인증하는 기능이 없다. 기록 밖의 숨은 peer memory나 빠진 호출도 발견하지 못한다.

합성자는 이 축소 예시에서 참여자 중 하나이고, deliberate의 모든 참여자가 성공 review를 남기는 완료 경로만 허용한다. 별도 합성 profile, 부분 결과/축소 승인, 모든 상태 전이, 실제 병렬 event/취소·복구, 과금 관측, native 도구 내부 turn·fan-out, 파일/네트워크 권한 강제는 다음 구현 범위다. 실제 runtime 기록은 synthetic=false에서 거절한다.

## 6. 아직 하지 않은 검증

실제 Codex/Claude Code/agy 설치·로그인·모델 목록 조회·LLM 호출, MCP bridge, 구독 과금/extra-credit 차단, OS sandbox/자식 프로세스 종료, quota 계측/누계 정규화, 실제 source resolver, 사용자 workload 정확도·시간·한도 비교, 장기 복구/동시 작업 시험은 미실시다.

다음 순서는 [V04-01 inventory → V04-03 두 native 경로의 read-only pilot](03-evaluation-and-roadmap.md)이다. 오프라인 실험 뼈대인 V04-02는 만들었지만, 그것이 V04-01이나 실제 모델 평가를 대신하지 않는다. 합성 checker를 운영 권한/수용 gate로 바로 쓰지 않는다.
