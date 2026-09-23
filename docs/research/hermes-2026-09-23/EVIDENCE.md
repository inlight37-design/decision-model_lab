# 근거·판본·검토 범위

2026-09-23 조사 기록. [요약](README.md) · [상세 분석](ANALYSIS.md) · [적용 계획](ADOPTION_PLAN.md)

## 기록 방법

이 문서의 `H01` 등은 **이번 조사 내부 참조**이며 프로젝트 E/F 근거 원장 등록을 뜻하지 않는다. 새로운 성능 수치나 운영 검증 결과를 원장에 추가하지 않았다.

- **코드 관측:** 고정 commit의 구현 본문을 읽어 해당 분기·구조를 확인했다. 실행 확인과 다르다.
- **문서 확인:** 프로젝트 또는 제작자의 안내를 읽었다. 실제 동작을 모두 입증하지 않는다.
- **제작자 자체 보고:** benchmark·비용·성능 홍보는 원문에 그런 주장이 있다는 뜻이다. 독립 재현이 아니다.
- **우리 제안:** 근거를 바탕으로 한 설계 판단이다. 기존 결정의 자동 변경이나 구현 완료가 아니다.

모든 아래 upstream URL은 동일한 `c0d7294769a38c17ceae51d8f7995e66e1dcae27` 판본이다. 관측한 main commit 시각은 **2026-09-23T04:02:02Z**이다. tag/release를 검토 대상으로 삼은 것이 아니며, 현재 움직이는 main 링크로 근거를 대체하지 않는다. 별도 발표일을 알 수 없는 문서는 발표일 미확인으로 취급한다.

## project

우리 프로젝트의 기준판: `0865e3d9493c36921e94c01ad9f6c803a6d78363`.

| ID | 읽은 원문 | 이번 판단에 사용하는 내용 | 제한 |
|---|---|---|---|
| P01 | [README](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/README.md) | 경제성·상급 모델 협업, native 우선, 연구/오프라인 검사와 실제 연결 구별 | README를 운영 검증으로 간주하지 않음 |
| P02 | [NEXT-SESSION](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/NEXT-SESSION.md) | exec 우선, Python 코어, V04-01 결과와 V04-03 준비, 구성 축소·과금 원칙 | aux-pc 사실은 해당 기록을 남긴 세션의 관측. 이번 세션이 그 PC에서 재실행하지 않음 |
| P03 | [AGENTS](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/AGENTS.md), [COLLABORATION](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/docs/COLLABORATION.md) | 브랜치·PR·인계, 관측 등급, 과거 기록 보존, CI 결과를 먼저 확인 | 모든 과거 PR을 재검토한 것이 아님 |
| P04 | [v0.4 frontier architecture](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/docs/architecture/v0.4/02-frontier-architecture.md) | 네 실행 모드, controller 단일 소유, 프로필·불변 근거 manifest, 독립 초안·주장 대조·교차검토·외부 확인 | 시스템 개요부터 P4까지의 관련 본문 중심. 설계 제안을 실제 runner로 승격하지 않음 |
| P05 | [design README](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/design/README.md) | Ledger의 unknown/검증 분리와 선택적 상세 공개, source/artifact 동기화 원칙 | Claude 발행 아티팩트와 실제 UI는 이번 세션에서 렌더링·편집하지 않음 |
| P06 | [review_boundary.py](https://github.com/inlight37-design/decision-model_lab/blob/0865e3d9493c36921e94c01ad9f6c803a6d78363/tools/review_boundary.py) | `advance`, `budget_projection`, `sealed_projection`, `quota_projection`의 실제 구현 | 순수 함수/합성 경계 실험. 인증, 프로세스 제어, 실제 한도 조회, 진실 판정은 하지 않음 |

## h01

**Hermes README — 제품의 문제 설정과 학습 루프 설명**

원문: [README.md](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/README.md)

등급: 문서 확인 / 일부 제작자 자체 보고. 검토 범위: 도입, 기능 요약, 설치·CLI 안내, documentation 경로, 기여 안내 등 반환된 본문. 긴 응답이 잘린 뒤의 미반환 부분은 검토 범위에 포함하지 않는다.

확인한 내용: 경험을 스킬과 기억으로 남기는 접근, gateway/cron/subagent/RPC 실행/trajectory 등 기능군, 자체 AIAgent 제품이라는 성격. `FTS5 session search with LLM summarization`이라는 설명이 포함된다.

제한: ‘유일한 학습 루프’, 낮은 운영비, 여러 backend의 호환성을 독립 검증하지 않았다. **세션 검색의 현재 동작은 H05 코드를 우선**한다. README의 설치 스크립트·보안 프로그램 예외 설정은 이번 작업에서 실행하거나 추천하지 않는다.

## h02

**전체 아키텍처 지도**

원문: [website/docs/developer-guide/architecture.md, L1–L230](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/developer-guide/architecture.md#L1-L230)

등급: 문서 확인. locator: System Overview, Directory Structure, Data Flow, Major Subsystems.

확인한 내용: `AIAgent` facade, conversation loop, provider resolution, tool registry, memory/context plugins, SessionDB, gateway/ACP/cron/batch 입구.

제한: 구조 지도는 개별 기능 보증이 아니다. 여기서 요약한 API mode 목록만 보고 **현재 Hermes가 native Codex 런타임을 제공하지 않는다고 결론 내릴 수 없다**. H08–H09 구현이 별도로 존재한다. 디렉터리 지도에 나온 모든 모듈을 읽은 것은 아니다.

## h03

**Skills — 단계적 공개와 검색 경계**

원문:

- [skills.md, L1–L210](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/user-guide/features/skills.md#L1-L210)
- [tools/skills_tool.py, L1–L225](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/tools/skills_tool.py#L1-L225)

등급: 문서 확인 + 코드 관측. locator: Progressive Disclosure, `/learn`, `_skills_dir`, `_skill_lookup_path_error`, `_skill_search_dirs`, `_find_all_skills`.

확인한 내용: 작은 목록에서 필요한 본문·참조를 불러오는 구조, 프로필별 저장 위치, 디렉터리/플랫폼/disabled 조건의 검색 cache, 절대 경로·traversal 검사, 프로젝트/로컬/외부 skill 검색과 이름 기준 first-wins 처리. `/learn`은 일반 agent turn으로 skill 문서를 만드는 경로로 설명된다.

제한: skill 쓰기 승인·검역의 모든 sibling 구현, symlink/경쟁 조건, plugin 실행 경계는 전수 검토하지 않았다. 코드에 검사 함수가 있다는 사실은 완전한 sandbox 증명이 아니다. 우리가 제안하는 후보/승인/게시 상태기계와 내용 hash 고정은 **추가 설계**이다.

## h04

**Persistent memory — bounded store와 frozen snapshot**

원문: [memory.md, L1–L240](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/user-guide/features/memory.md#L1-L240)

등급: 문서 확인. locator: How It Works, Frozen snapshot pattern, Memory Needs Session Boundaries, Troubleshooting, Capacity Management, Session Search.

확인한 내용: MEMORY/USER 저장소의 길이 제한, 세션 시작 snapshot, 명시적인 add/replace/remove, 가득 찼을 때 오류 반환, 프로필 분리, 하나의 home을 복수 writer가 공유하지 말라는 경고. 저장했다고 말하는 문장과 실제 memory tool 쓰기를 구분한다.

제한: 글자 수는 모델별 token 수와 동일하지 않다. ‘raw/no truncation’ 설명은 H05의 실제 잘림 분기와 다르다. 실제 파일 잠금·쓰기 승인·악성 입력 탐지율은 검증하지 않았다. 품질·시간 수치와 작은 모델에 관한 일반화는 이번 권고의 근거로 사용하지 않는다.

## h05

**Session search — 추가 LLM 없는 검색, 범위·계보·잘림 정보**

원문: [tools/session_search_tool.py, L1–L250](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/tools/session_search_tool.py#L1-L250)

등급: 코드 관측. locator: 모듈 설명, `_HIDDEN_SESSION_SOURCES`, `_DEMOTED_SESSION_SOURCES`, `_READ_MAX_CONTENT`, `_resolve_to_parent`, `_session_left_live_context`, `_get_message_storage_state`, `_shape_message`.

확인한 내용: discovery/scroll/read/browse 형태, LLM 호출이 없는 DB 메시지 반환 설계, lineage 중복 처리, cron 순위 조정, undo와 compaction archive 상태 구분, ANSI 제거, 긴 메시지의 `content_truncated` 및 원래 길이 정보.

제한: 모든 검색/권한 진입점을 읽거나 실데이터로 실행하지 않았다. source 숨김·순위 조정을 **우리의 사용자/참여자 권한 경계로 간주하지 않는다**. 잘린 응답 이후 필요한 원문을 얻는 전체 경로와 한국어 검색 품질은 별도 수용 시험이 필요하다.

## h06

**Session storage — 소유권·계보·관측 출처가 있는 사용량**

원문: [session-storage.md, L1–L230](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/developer-guide/session-storage.md#L1-L230)

등급: 문서 확인. locator: Hermes home/profile isolation, test isolation guard, compaction generations, Codex input ownership, gateway exception-path ownership, Architecture Overview, schema.

확인한 내용: profile별 DB, SQLite WAL와 FTS, 한국어 등을 위한 trigram/CJK 경로가 포함된 schema, parent lineage, active/archive 구별, token/cost 출처 필드, 별도 모델 사용량, delivery obligation 원장. 입력 echo를 다루는 소유권 표식은 단순 내용 중복 제거와 다르다고 설명한다.

제한: DB 구현·migration·복구·FTS tokenizer·outbox 전체는 실행하거나 전수 검토하지 않았다. 원문 자체가 예외 경로 중재를 universal exactly-once가 아니라고 제한한다. 우리에게 모든 table을 복제하라는 근거가 아니다.

## h07

**Subagent construction and lifecycle**

원문: [tools/delegate_tool.py, L1–L415](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/tools/delegate_tool.py#L1-L415)

등급: 코드 관측. locator: `_open_child_session_db`, `_build_child_agent`, `_run_single_child`, `_build_children`.

확인한 내용: 새 child AIAgent, 별도 task/session 식별, 공유 DB 파일에 대한 별도 handle, `skip_context_files=True`와 `skip_memory=True`, 부모 `prefill_messages` 전달, child별 새 iteration budget, 부모 취소 전파 연결, 출력 schema 검증 진입, completed/interrupted/failed와 max-iteration 사유 구분, 진행 callback·생명주기 hook·worktree 처리 연결점.

제한: `delegate_tool_*` sibling 전체, 실제 OS 권한·worktree 격리, 완료 후 자식 잔존 여부는 검증하지 않았다. fresh conversation은 blind 독립성의 충분조건이 아니다. fallback과 credential rotation의 세부 동작을 이 facade만으로 단정하지 않는다.

## h08

**Native Codex session adapter**

원문: [codex_app_server_session.py, L1–L230](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/agent/transports/codex_app_server_session.py#L1-L230)

등급: 코드 관측. locator: `TurnResult`, `_HERMES_TO_CODEX_PERMISSION_PROFILE`, `_notification_scope_ids`, `_notification_belongs_to_turn`, `_classify_oauth_failure`, `CodexThreadResumeError`, `CodexAppServerSession` 생성부.

확인한 내용: native thread/turn/승인/취소/재개를 다루는 session adapter, 서로 다른 thread/turn 표식을 가진 알림의 배제, 표식 없는 알림의 호환성 수용, 설정에 따른 권한 profile 변환, 본 요청 오류와 주변 stderr 진단 분리.

제한: transport 의미·권한 명칭의 현재 공식 지원을 이 파일만으로 보증하지 않는다. 실제 CLI 버전별 conformance는 미실시. 특히 기본 workspace-write와 unscoped 알림 수용을 우리 read-only/blind controller에 그대로 이식하지 않는다.

## h09

**Native Codex stdio transport and process cleanup**

원문: [codex_app_server.py, L1–L210](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/agent/transports/codex_app_server.py#L1-L210)

등급: 코드 관측. locator: `_snapshot_descendants`, `_reap_snapshotted`, `CodexAppServerClient.__init__`, `initialize`, `close`.

확인한 내용: `codex app-server` argv 실행, JSON-RPC 요청/응답·notification/server-request 분리, stdout/stderr 별도 reader, 초기 handshake, 부모 종료 전 descendant snapshot, 제한된 종료 대기와 후속 정리, 환경변수 필터 helper 사용.

제한: `psutil`을 못 쓰거나 조회가 실패하면 descendant snapshot이 비어 있을 수 있다. 이것을 OS 전체 프로세스 격리·취소 완료 증명으로 취급하지 않는다. 환경 구성은 provider credential 상속을 허용하는 경로이므로 우리의 구독-only 실행에 그대로 쓰지 않는다. 사용자 PC에서는 실행하지 않았다.

## h10

**Provider runtime / credential / auxiliary / fallback**

원문: [provider-runtime.md, L1–L245](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/developer-guide/provider-runtime.md#L1-L245)

등급: 문서 확인. locator: registry and precedence, Native Anthropic path, OpenAI Codex path, Auxiliary model routing, Fallback models.

확인한 내용: 공통 provider resolver, 요청·설정·환경 우선순위, 모델/endpoint/인증 분리, 별도 보조 모델 경로, fallback 설명. Anthropic 경로는 Claude Code 자격증명을 활용한 직접 Messages API 접근을 설명한다.

제한: 그것은 공식 Claude Code CLI를 그대로 실행한다는 설명이 아니다. 구현 존재가 공급자 약관상 허용을 증명하지 않는다. 이 조사에서는 provider 계정·인증 파일·약관 허용 여부를 검증하지 않았으며 인증 이식 방법을 권고하지 않는다. 이 문서의 API mode/fallback 개요만으로 최신 모든 transport·child routing을 단정하지 않는다.

## h11

**Mixture of Agents product behavior and vendor benchmark**

원문: [mixture-of-agents.md, L1–L260](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/user-guide/features/mixture-of-agents.md#L1-L260)

등급: 문서 확인 / Benchmarks 절은 제작자 자체 보고.

확인한 내용: named preset·reference slots·실제 도구 루프를 수행하는 aggregator, 역할별 과금 주의, 조언의 user_turn/per_iteration/every_n 주기, 일부 reference 실패 후 지속, privacy filter의 display/full 차이, 재귀 MoA 제한 설명.

제한: 같은 문서의 개요는 매 iteration처럼 서술하지만 cadence 절은 user_turn 기본값을 명시한다. 기본값은 H12 config와 대조했다. 조언 payload에 관한 문서와 코드 주석의 차이도 아래 drift 표에 남긴다. benchmark의 동일 총예산·반복 변동·우리 작업군 재현은 확인하지 않았으므로 성능 향상률을 전이하지 않는다. 기본 preset의 모델 이름을 현재 최선의 모델 목록으로 사용하지 않는다.

## h12

**MoA configuration, reference call and accounting code**

원문:

- [agent/moa_loop.py, L1–L235](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/agent/moa_loop.py#L1-L235)
- [agent/moa_loop.py, L250–L395](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/agent/moa_loop.py#L250-L395)
- [hermes_cli/moa_config.py, L1–L130](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/hermes_cli/moa_config.py#L1-L130)

등급: 코드 관측. locator: `_RefAccounting`, `_REFERENCE_TOOL_RESULT_BUDGET`, `_slot_runtime`, `_price_reference_response`, `_run_reference` 시작부, `_coerce_fanout`, `coerce_privacy_filter`.

확인한 내용: 조언 모델 고유 route/rate를 사용하는 accounting 구조, role별 호출 설정, resolver 실패 시 bare provider/model로 계속 시도하는 분기, 잘못된 cadence의 user_turn 정규화, privacy filter 기본 off. reference에 실제 실행을 수행했다고 주장하지 말라는 별도 지침이 있다.

제한: MoA loop 전체, payload builder 전체, 취소·실패의 전체 전파는 검토하지 않았다. `_REFERENCE_TOOL_RESULT_BUDGET`과 주석은 조언용 도구 결과 preview 경로의 존재를 시사하므로 ‘tool trace를 전혀 받지 않는다’는 일반화는 피한다. 확인하지 않은 정확한 전송 payload·과금·실제 fanout 실행 횟수는 pilot에서 관측해야 한다.

## h13

**Context compression and caching**

원문: [context-compression-and-caching.md, L1–L230](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/developer-guide/context-compression-and-caching.md#L1-L230)

등급: 문서 확인. locator: ContextEngine, gateway vs agent compression, usage anchors, estimate fallback, failure cooldown/provider-proven overflow.

확인한 내용: 교체 가능한 context engine, 계층별 압축, provider 관측량과 신규 메시지 추정량의 결합, 반복 실패 냉각·한정 복구·일부 원문 보존/요약 fallback 경로 설명.

제한: 압축 code 전체 및 안내에서 언급한 replay eval을 실행하지 않았다. 특정 threshold·cooldown·고정 token 추정값을 우리 최적값으로 사용하지 않는다. ‘lossless’라는 plugin 이름이나 원문 DB 보존이 모델 입력의 의미 보존을 보증하지 않는다.

## h14

**Security model and approval policy**

원문: [security.md](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/user-guide/security.md)

등급: 문서 확인. 검토 범위: 앞부분 Overview, Approval Modes, supervised gateway guard, hardline/user deny rules, threat-model note, Approval Timeout까지. 긴 응답이 잘린 뒤 부분은 포함하지 않는다.

확인한 내용: smart 모드의 보조 LLM 위험 평가, headless deny 설정, 승인 timeout의 거절 처리, shell 패턴 검사와 OS sandbox의 구별. 문서가 deny rule의 해석 한계를 명시한다.

제한: 탐지/권한 구현의 모든 경로와 bypass 저항성을 감사하지 않았다. 이 보고서의 부정 fixture는 우리 시스템의 수용 기준이며, Hermes에서 실증한 취약점 목록이 아니다. 모델 판단을 최종 권한 부여기로 채택하지 않는 것은 우리 설계 제안이다.

## h15

**MCP discovery, catalog and tool selection**

원문: [mcp.md, L1–L235](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/website/docs/user-guide/features/mcp.md#L1-L235)

등급: 문서 확인. locator: catalog flow, tool selection, trust model, manifest version compatibility.

확인한 내용: stdio/HTTP, 목록 발견, tool include/exclude, 인증 성공과 도구 목록 실패의 별도 상태, manifest/설치 출처 표시. 사전 선택/default가 없으면 전체 허용될 수 있고 exclude-only 구성은 새 tool에도 열릴 수 있다는 설명.

제한: MCP client/server 구현, OAuth 저장·취소의 원자성, 공급망 검증, endpoint의 실제 권한은 실행하지 않았다. ‘카탈로그 승인됨’을 우리 capability 검증 통과와 동일시하지 않는다. 도구 schema hash와 default-deny는 추가 설계다.

## h16

**Root license**

원문: [LICENSE](https://github.com/NousResearch/hermes-agent/blob/c0d7294769a38c17ceae51d8f7995e66e1dcae27/LICENSE)

등급: 원문 확인. 전체 root LICENSE를 읽었다. MIT License이며 copyright 문구는 `Copyright (c) 2025 Nous Research`이다. 복사본/상당 부분에 저작권·허가 고지를 포함하는 조건이 명시돼 있다.

제한: 저장소의 모든 asset, skill, 외부 dependency, 하위 파일에 동일 권리가 성립하는지 전수 확인하지 않았다. 우리 코드·문서 라이선스로 타사 고지를 덮어쓰지 않는다. **이번 PR은 분석 문서를 작성하며 Hermes 소스 코드나 asset을 이식하지 않는다.** 실제 복사 시 파일별 검토와 고지 기록을 별도 작업으로 수행한다.

## 문서와 코드가 다를 때의 처리

| 주제 | 문서에서 읽힌 내용 | 검토한 코드 또는 더 구체적인 안내 | 이 조사에서의 처리 |
|---|---|---|---|
| 세션 검색의 요약 호출 | README는 LLM 요약을 소개 | H05 모듈은 no LLM calls를 명시 | 현재 검색 경로는 별도 요약 모델이 없는 설계로 기록. 전체 제품의 보조 호출까지 없다고 확대하지 않음 |
| 세션 검색의 원문 길이 | memory 문서는 truncation이 없다고 설명 | H05 `_shape_message`는 잘림·원래 길이를 기록 | 결과가 항상 전체 원문이라는 주장 금지. 재조회 수용 시험 추가 |
| runtime 종류 | architecture/provider 개요는 제한된 API mode 목록 | H08–H09에 native Codex App Server 코드 | ‘API 전용’이라는 일괄 분류 배제 |
| MoA 주기 | 개요의 매 iteration 서술 | cadence 절·`_coerce_fanout`은 user_turn 기본 | 설정 정규화와 실제 호출 관측을 구별하고 후자를 실험으로 남김 |
| MoA 조언 자료 | 문서는 user/assistant text 중심·tool transcript 제거 설명 | H12에 tool-result preview 예산/주석 존재 | 실제 payload builder 전수 검토 전까지 입력 동등성·blind 보증을 하지 않음 |
| delegate fallback | provider 안내의 일괄 설명 | H07은 child runtime에 route 소유 config를 전달 | 전체 resolver 미검토 상태에서 모든 child의 fallback 동작을 단정하지 않음 |

## 수행하지 않은 검증

Hermes 설치·실제 모델 호출, upstream pytest 실행, Windows 프로세스 트리/ACL 검증, MCP server 설치·호출, 인증 파일 열람, 구독 한도·금액 측정, benchmark 재현, 완전한 코드/의존성/라이선스/보안 감사는 수행하지 않았다. 우리 문서 변경에 대한 CI는 별도이며, 그 통과를 Hermes 운영 검증으로 표현하지 않는다.
