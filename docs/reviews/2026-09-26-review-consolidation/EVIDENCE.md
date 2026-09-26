# 통합 검토의 근거와 한계

2026-09-26 · 진행 체크포인트. 기준점은 [README](README.md)의 고정 SHA 표를 따른다. 아래는 원본 소스를 직접 읽은 정적 확인이며, 이전 세션의 실행을 이 세션의 재현으로 바꾸지 않는다.

## 직접 대조한 코드

| ID | 위치 | 이번 확인 | 한계 |
|---|---|---|---|
| V01 | [controller.view / mark_reviewed](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/controller.py#L915-L1045) | reviewed는 human_reviewed 사건의 존재만 보며 결과 seq/attempt를 비교하지 않는다. mark_reviewed도 이미 있으면 새 사건을 남기지 않는다. AH-01의 구조적 근거가 일치한다 | 합성·SQLite 전체 흐름은 이번에 재실행하지 않음 |
| V02 | [task_projection](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/roles.py#L40-L79) | 미확인/합성 실패가 먼저이며 수동 입력이 일반 working 기본값보다 앞선다. 마지막 else는 working이다 | 알 수 없는 모든 입력이 working인 것은 아니다. 앞선 분기에 맞지 않을 때의 기본값 문제 |
| V03 | [view의 반환](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/app/controller.py#L990-L999) | paused는 응답 최상위에만 있으며 task_projection(tasks, runs)에 전달되지 않는다 | N3의 마지막 else만 바꾸는 것으로 일시정지/자동진행을 구분할 수 없음 |
| V04 | [runner._execute](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/core/runner.py#L334-L442) | Popen 성공 뒤 Tree/Reader/Writer 생성·start와 정상 정리 사이에 예외 정리를 보장하는 finally가 없다 | 실제 OS 자식 잔존을 관측하지 않음. #104의 대역 재현과 구분 |
| V05 | [codex_global_instructions](https://github.com/inlight37-design/decision-model_lab/blob/8fc945d410bec31d7f104199a684e9aab4f5b9a3/core/adapters.py#L84-L190) | 현재 목록은 AGENTS.override.md·AGENTS.md. 일반 0바이트 파일은 생략하고 링크·폴더는 거절 대상으로 남긴다 | N1을 목록 추가만으로 구현하면 N1이 요구한 ‘빈 hooks.json도 거절’이 충족되지 않음 |

## N1에 필요한 외부 자료 대조

직접 확인한 OpenAI 공식 문서(확인일 2026-09-26):

- [Hooks](https://developers.openai.com/codex/hooks): hooks.json 외에도 config.toml의 inline hooks, 프로젝트·플러그인·managed 층이 존재한다.
- [Advanced Configuration](https://developers.openai.com/codex/config-file/config-advanced): CODEX_HOME 기본값은 ~/.codex이며 user/project hooks의 활성 층과 프로젝트 신뢰를 구분한다.
- [Non-interactive mode](https://developers.openai.com/codex/non-interactive-mode): --ignore-user-config는 $CODEX_HOME/config.toml을 읽지 않는 용도로 설명된다. 이 문장만으로 모든 훅의 미실행을 보증하지 않는다.

판정: N1은 **좁은 예방 방어로 채택할 후보**다. 사용자 PC에서 훅이 실제로 발화했다는 주장은 하지 않는다. hooks.json 하나가 없다는 사실도 전체 문맥 격리의 증명으로 쓰지 않는다. argv가 바뀌지 않아 현재 계산 revision이 같더라도 새 검사와 적용되는 훅 표면에 대한 확인은 필요하다. argv/설정/허용 표면을 바꾸는 구현이라면 해당 계획의 재관측을 따른다. 사용자 전역 파일을 삭제하거나 고치지 않는다.

## 정적 확인과 전달 증거의 구분

[#104 근거](https://github.com/inlight37-design/decision-model_lab/blob/8281b4fe5b20394c6b15e2792b79dc00d0cc8c6c/docs/reviews/2026-09-26-architecture-health/EVIDENCE.md)의 probe 성공은 반례 재현이며 수정 검증이 아니다. runner의 소스 가드는 수정된 제품에서 실행을 멈추도록 되어 있다. 후속 구현은 필요한 반례를 기존 tests로 옮기고 기대값을 올바른 동작으로 바꿔야 한다. 과거 probe를 그대로 녹색으로 만드는 것이 목표가 아니다.

## 다음 대조

#102·#103 적용안과 #105의 후보 처분, #104 나머지 발견의 우선순위를 합친다. 최종 문서에는 각 항목을 수용/수정 수용/조건부/미채택으로 분리하고, 새 작업 단계와 완료 조건을 남긴다. 이 체크포인트는 최종 완료 보고가 아니다.
