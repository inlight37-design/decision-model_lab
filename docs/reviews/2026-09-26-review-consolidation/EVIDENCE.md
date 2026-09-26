# 통합 검토의 근거와 한계

2026-09-26 · 기준점은 [README](README.md) 2절의 고정 SHA 표를 따른다. 직접 읽은 소스의 정적 확인, 공식 문서의 설명, 다른 세션의 실행 기록을 구분한다. 여러 리뷰가 동의하거나 하위 에이전트가 투표했다는 사실을 독립 실험의 재현으로 세지 않는다.

## 읽은 자료와 역할

| 자료 | 사용한 범위 | 취급 |
|---|---|---|
| [#104 README](../2026-09-26-architecture-health/README.md), [FINDINGS](../2026-09-26-architecture-health/FINDINGS.md), [EVIDENCE](../2026-09-26-architecture-health/EVIDENCE.md) | 전체 판단·AH 지적·낮은 우선순위 계약·재현 방법과 한계 | 문서 직접 열람. 그 안의 실행·측정은 이전 세션의 전달 근거 |
| [#105 README](https://github.com/inlight37-design/decision-model_lab/blob/6d6fdb9debc07ef835dd3d3f0b224f372a918c01/docs/reviews/2026-09-26-codex-peek-claude/README.md), [EVIDENCE](https://github.com/inlight37-design/decision-model_lab/blob/6d6fdb9debc07ef835dd3d3f0b224f372a918c01/docs/reviews/2026-09-26-codex-peek-claude/EVIDENCE.md) | N1–N4·단계별 제안·미채택·후보 처분·검증 한계·사용자 미확정 판단 | 문서 직접 열람. 외부 저자의 수치·이력은 직접 실험으로 승격하지 않음 |
| [#102 ADOPTION](../2026-09-26-codex-peek/ADOPTION.md), [#103 비교](../2026-09-26-codex-peek-comparison/README.md) | 현재 모듈에 흡수하는 순서, 이미 있는 계약, 수동 자료와 자동 기억의 구분 | 기존 방향의 일관성 확인. 외부 전체 소스를 새로 해체했다는 뜻은 아님 |
| AGENTS.md, docs/COLLABORATION.md, PR 양식, #104 NEXT-SESSION | 문서·브랜치·인계·사용자 위임과 미확정 선택 | 기존 규칙을 적용. 사용자 PC의 사실은 앞선 관측 기록으로 보존 |

## 직접 대조한 코드

| ID | 위치 | 이번 확인 | 한계 |
|---|---|---|---|
| V01 | [controller.view / mark_reviewed](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/controller.py#L915-L1045) | reviewed는 human_reviewed 사건의 존재만 보며 결과 seq/attempt를 비교하지 않는다. mark_reviewed도 이미 있으면 새 사건을 남기지 않는다. AH-01의 구조적 근거가 일치한다 | 합성·SQLite 전체 흐름은 이번에 재실행하지 않음 |
| V02 | [task_projection](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/roles.py#L40-L79) | 미확인/합성 실패가 먼저이며 수동 입력이 일반 working 기본값보다 앞선다. 마지막 else는 working이다 | 알 수 없는 모든 입력이 working인 것은 아니다. 앞선 분기에 맞지 않을 때의 기본값 문제 |
| V03 | [view의 반환](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/controller.py#L990-L999) | paused는 응답 최상위에만 있으며 task_projection(tasks, runs)에 전달되지 않는다 | N3의 마지막 else만 바꾸는 것으로 일시정지/자동진행을 구분할 수 없음 |
| V04 | [runner._execute](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/core/runner.py#L334-L442) | Popen 성공 뒤 Tree/Reader/Writer 생성·start와 정상 정리 사이에 예외 정리를 보장하는 finally가 없다 | 실제 OS 자식 잔존을 관측하지 않음. #104의 대역 재현과 구분 |
| V05 | [codex_global_instructions](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/core/adapters.py#L84-L190) | 현재 목록은 AGENTS.override.md·AGENTS.md. 일반 0바이트 파일은 생략하고 링크·폴더는 거절 대상으로 남긴다 | N1을 목록 추가만으로 구현하면 N1이 요구한 ‘빈 hooks.json도 거절’이 충족되지 않음 |
| V06 | [view의 공개 투영과 이력](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/controller.py#L915-L999) | 일반 사건 tail은 LIMIT 12다. 합성 상태와 이력을 각각 계산하고, 공개 후 원문을 포함한 runs를 돌려준다 | 반복 조회를 줄일 근거이나 사용자 원장의 실제 지연 측정은 아님 |

## 공식 문서로 보완한 N1

OpenAI 공식 문서 확인일은 2026-09-26이다. 다음 developers.openai.com 주소는 읽을 때 learn.chatgpt.com의 해당 문서로 연결됐다.

| 문서·locator | 확인한 설명 | 이번 적용 |
|---|---|---|
| [Hooks](https://developers.openai.com/codex/hooks), Where Codex looks for hooks / Review and trust hooks | hooks.json·inline config·프로젝트·플러그인·managed 층을 구분한다. 비관리 훅에는 신뢰 검토 조건도 있다 | 파일 하나의 존재 여부와 모든 훅의 실행 여부는 다름. ‘설정된 모든 훅이 항상 발화한다’고도 쓰지 않음 |
| [Advanced Configuration](https://developers.openai.com/codex/config-file/config-advanced), Config and state locations | CODEX_HOME의 기본값은 ~/.codex다 | 검사 경로는 참여자에게 실제 적용되는 HOME/구성과 맞아야 함 |
| [Non-interactive mode](https://developers.openai.com/codex/non-interactive-mode), Permissions and safety | --ignore-user-config는 $CODEX_HOME/config.toml을 읽지 않는 용도로 설명된다 | 이 문장만으로 모든 훅의 미실행을 보증하지 않음 |

N1은 **좁은 예방 방어로 채택할 후보**다. 사용자 PC에서 훅이 실제로 발화했다는 주장은 하지 않는다. 현재 웹 문서가 관측된 설치판 0.156.1의 모든 동작을 입증하지도 않는다. 파일 검사만으로 원래 strict 관측을 훅 전수 검증으로 소급 승격하지 않는다.

argv가 바뀌지 않아 기존 계산 revision이 같더라도 새 검사와 적용되는 훅 표면에 대한 확인은 필요하다. argv/설정/허용 표면을 바꾸는 구현이라면 해당 계획의 재관측을 따른다. 사용자의 전역 파일을 삭제하거나 고치지 않는다. 파일 내용·인증 값을 로그로 남기는 진단도 하지 않는다.

## 전달받은 반례를 사용하는 방법

[#104 근거](../2026-09-26-architecture-health/EVIDENCE.md)의 probe 성공은 **반례 재현이며 수정 검증이 아니다.** 통합 runner의 소스 가드는 수정된 제품에서 실행을 멈추도록 되어 있다. 후속 구현은 필요한 반례를 기존 tests로 옮기고 기대값을 올바른 동작으로 바꿔야 한다. 과거 probe를 그대로 녹색으로 만드는 것이 목표가 아니다.

- AH-02·04의 폴더 충돌/메타데이터 반례는 synthetic 입력이다. 실제 provider가 비정상 메타데이터를 보냈다는 근거가 아니다.
- AH-03의 Popen/Tree 대역은 cleanup 호출 누락을 보이며 실제 OS orphan을 직접 관측한 것은 아니다.
- AH-05는 제품 JS 함수·지연 Promise 대역의 반례다. 실제 이중 과금이나 봉인 우회를 입증한 것이 아니다.
- AH-06의 큰 임시 원장 측정은 증가 구조를 보인다. 상한과 원장 교체가 있는 현재 사용자 앱이 이미 느리다고 단정하지 않는다.
- AH-07은 함수·파일·thread로 특정 경쟁 순서를 고정한 것이다. 실제 바탕화면 두 프로세스의 발생 빈도는 미확인이다.
- AH-08은 같은 OS 사용자가 관측 파일을 교체하는 좁은 경쟁이다. 실행 직전 재검사까지 통과한 실제 모델 실행을 입증하지 않는다.

## 기존 표현을 보완한 이유

| 원래 지적/읽힐 수 있는 표현 | 보완 |
|---|---|
| N1: 거절 목록에 hooks.json 추가 | 현재 함수의 빈 파일 예외를 그대로 물려받으면 요구가 충족되지 않음. 존재 정책을 별도로 명시 |
| N3: 남은 기본값을 사람 몫으로 변경 | paused 입력과 알려진 자동 진행 조건도 필요. 모든 paused 실행이 이미 멈춘 것은 아니며 실제 running과 구분 |
| #105: 폴링 가드는 TM 계획 후보 | AH-05의 생성 영수증·역순 응답 반례는 최적화가 아니라 정확성 보완이므로 우선순위를 앞당김 |
| N2: none/미보고 검토는 완료 근거가 아님 | 약한 ‘지적 없음’을 신뢰하지 말자는 취지는 수용. 모델을 가리지 않는 고정 강도 규칙 대신 요청/보고값·범위·실제 근거를 기록. 강도가 높아도 무결성 증명은 아님 |
| Warm·구간 겹침·시나리오 재계산 | 자동 기억·우리 효과를 미확립으로 두는 데 사용. 효과 없음의 증명이나 원자료 없이 정확히 보정된 구간으로 사용하지 않음 |
| 새 세션이므로 resume의 캐시 이득을 못 씀 | 영속 검증 세션 재사용을 도입하지 않는 근거로만 사용. 새 세션에는 어떤 캐시도 없다는 주장으로 넓히지 않음 |
| 리뷰들의 검사 개수·검토 관점 수 | 코드 기준과 OS·skip 조건이 다르므로 품질 순위로 비교하지 않음. 합의는 검증이 아님 |

## 이 세션의 검증 경계

GitHub 연결 도구로 읽고 문서를 커밋했으며 사용자 PC에는 접근하지 않았다. 컨테이너 GitHub clone은 DNS 실패, 공개 archive 다운로드도 성공하지 못했다. 따라서 로컬 전체 suite나 원본 probe를 재실행했다고 쓰지 않는다. 코드·시험·workflow를 고치거나 검사를 약화하지 않았다.

이 PR의 고유 diff는 시작 commit `8281b4fe5b20394c6b15e2792b79dc00d0cc8c6c` 이후다. main 대비 diff에는 선행 역할판 및 리뷰가 포함된다. 최종 head와 CI 결과는 [PR #106](https://github.com/inlight37-design/decision-model_lab/pull/106)의 검증 절에 기록한다. CI 성공이 제안된 제품 결함의 수정 완료나 실제 모델 품질의 검증을 뜻하지 않는다.
