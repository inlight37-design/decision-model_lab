# PR #29·#30 재검토와 C3 무모델 진단 — 2026-09-24

작성: codex 하위 검토, GitHub 플러그인·gh 읽기와 aux-pc-wsl의 합성 HOME 진단. 검토 기준 main `56bf5afcce385b8bec33f118421428af99944534`. 저장소 코드·정책·인증 설정을 바꾸지 않았고 모델은 호출하지 않았다. OpenAI Docs skill의 순서대로 공식 문서를 검색·열어 읽은 뒤 설치 CLI에서 확인했다.

## 결론

- PR #29·#30은 병합됐고, 정확한 head의 push CI에서 Python 3.12·3.13 checkout SHA와 성공을 확인했다. main 자체의 두 CI job도 성공했다.
- main 보호는 검토 시작에는 없었지만, 부모 작업이 적용한 뒤 독립적으로 다시 읽어 필수 검사·PR 경유·관리자 강제를 확인했다. 이 하위 작업은 설정을 변경하지 않았다.
- **C3를 조사할 실제 무모델 도구를 찾았다.** 설치 Codex 0.156.1의 `debug prompt-input`은 합성 HOME에서 모델 통신 없이 지시문·skill metadata가 들어간 JSON을 출력했다.
- **app-server의 무모델 목록도 실제로 확인했다.** `skills/list`, `mcpServerStatus/list`, `app/installed`가 thread/turn 생성 없이 응답했다. 합성 skill metadata와 MCP 도구 schema를 받아 prompt-input의 일부 빈틈을 메웠다.
- **그러나 C3 성공 판정에는 부족하다.** prompt-input에는 최종 요청의 tools schema가 없고, MCP가 초기화돼 도구 목록을 읽어도 해당 도구·서버 지시문 표식이 나오지 않았다. app-server 목록에서도 MCP 지시문은 없으며 thread별 runtimeStatus는 null이었다. 또한 exec의 `--ignore-user-config`를 debug 명령이 받지 않아 현재 참여자 계약과 동등하다는 근거가 없다. `failed`와 허가 보류를 유지해야 한다.

## GitHub의 정확한 근거

GitHub `get_pr_info`는 두 PR에 `merged=true`, `state=closed`를 반환했다. #29는 `NEXT-SESSION.md`만 변경했다. #30의 merge 첫 부모는 #29 merge이고 두 번째 부모는 #30 최종 head다.

| 대상 | 실제 checkout SHA | push CI | 결과 |
|---|---|---|---|
| [PR #29](https://github.com/inlight37-design/decision-model_lab/pull/29) | `bcbf052c3eda78d7d4609c478b062f4059dea14c` | [35967267774](https://github.com/inlight37-design/decision-model_lab/actions/runs/35967267774) | 3.12·3.13 성공, 두 로그 SHA 일치 |
| [PR #30](https://github.com/inlight37-design/decision-model_lab/pull/30) | `c9ead60f0b1ffc55e62c74a14032cf2cbe4ce271` | [35969195657](https://github.com/inlight37-design/decision-model_lab/actions/runs/35969195657) | 3.12·3.13 성공, 두 로그 SHA 일치 |
| main | `56bf5afcce385b8bec33f118421428af99944534` | [35969301924](https://github.com/inlight37-design/decision-model_lab/actions/runs/35969301924) | 3.12·3.13 성공, 두 로그 SHA 일치 |

병합 SHA는 #29 `af474278bb9031a9e5d52c3778b23f27db3f0f8f`, #30 `56bf5afcce385b8bec33f118421428af99944534`다. run의 API `head_sha`뿐 아니라 각 job의 `git log -1 --format=%H` 출력까지 읽었다. 전체 시험은 모두 성공했고 Linux CI의 skip은 Windows 레지스트리 전용이다. 이 검토는 로컬 전체 시험을 별도로 다시 돌리지는 않았다.

## main 보호 재조회

시작 시 `/branches/main`은 `protected=false`, `/rulesets`는 `[]`, `/branches/main/protection`은 404 `Branch not protected`였다. 이후 부모 작업이 적용했다고 알린 뒤 protection API를 다시 읽은 결과:

- `checks (3.12)`와 `checks (3.13)` 필수, 두 검사 모두 GitHub Actions `app_id=15368`에 묶임.
- PR 경유, 승인 수 0; `enforce_admins.enabled=true`.
- 최신 main 재반영 강제는 `strict=false`.
- force push·브랜치 삭제 허용은 모두 false.

이는 읽기로 확인한 설정이며, 실제 실패 PR을 일부러 병합해 거절시키는 변형 실험은 하지 않았다. 새 작업의 최신 CI 상태와 과거 #30 성공은 분리해야 한다.

## C3: 문서와 설치 CLI

공식 [Developer commands](https://learn.chatgpt.com/docs/developer-commands#codex-debug-prompt-input)는 실험적 `codex debug prompt-input`을 모델에 보이는 prompt input JSON을 렌더링하는 진단으로 설명한다. 같은 문서에서 `--ignore-user-config`는 사용자 config 비적재이고 인증은 계속 CODEX_HOME을 쓴다고 설명한다. **최종 요청 전체나 도구 schema까지 출력한다고 확대하지 않았다.**

설치 0.156.1의 `debug --help`와 `debug prompt-input --help`에서도 명령을 확인했다. prompt-input의 옵션은 config·image·enable/disable 등이었고 `--ignore-user-config`는 거절했다. `mcp list --help`에는 `--json`이 있었다.

공식 [Build skills](https://learn.chatgpt.com/docs/build-skills)는 `.agents/skills` 검색과 metadata 중심의 점진적 로딩을 설명한다. 공식 [App Server](https://learn.chatgpt.com/docs/app-server)는 `skills/list`, `mcpServerStatus/list`, `app/installed`, `config/read`, 그리고 thread 시작 결과의 `instructionSources`를 제공한다. 이것들은 발견·설정·표면 상태를 읽는 보조 수단이며 exec의 최종 모델 요청과 같다는 보증으로 쓰지 않는다. 아래 목록 RPC는 실제로 실행했고 config 읽기·thread 생성은 하지 않았다.

## 직접 실행한 합성 HOME 시험

모든 CLI 프로세스는 `isolation.run()` 아래에서 실행했다. 그 안에 `unshare --user --map-root-user --net`을 더해 별도 네트워크 namespace를 만들었다. 실제 로그인 폴더·프로젝트·상태 DB는 연결하지 않았고 읽기 전용 CLI release, 합성 config와 시험 폴더만 연결했다. 실제 exec나 모델 turn 명령은 호출하지 않았다. 각 완료 결과의 `tree_confirmed_empty=true`를 확인했다.

처음 `unshare --net`만 사용한 준비 시도는 권한 거절로 CLI가 시작되지 않았다. 별도 user namespace를 함께 만드는 방법으로 수정했다. 실제 CLI 경로도 symlink 대신 realpath로 넘겼다. 이 준비 오류를 진단 성공에 포함하지 않는다.

| 합성 시험 | 직접 관측한 결과 | 해석 |
|---|---|---|
| 빈 HOME + `debug prompt-input` | exit 0, JSON list, message/input_text 5개, developer 3·user 2, 합성 사용자 표식 포함 | 모델 없이 로컬 prompt 구성을 볼 수 있음 |
| HOME·작업 폴더의 합성 AGENTS 표식 | exit 0, 양쪽 표식이 JSON에 포함 | 지시문 발견을 자기 보고 대신 실제 렌더링으로 관측 가능 |
| 프로젝트 합성 skill | description 표식 포함, 본문 표식 없음 | metadata와 본문 로딩을 구분할 수 있음 |
| 합성 stdio MCP | helper 로그에 initialize→notifications/initialized→tools/list. 그러나 prompt JSON에는 MCP 지시문 표식·도구 이름·tools 필드가 없음 | debug 입력 목록만으로 도구 표면 부재를 증명할 수 없는 반례 |
| `debug prompt-input --ignore-user-config` | exit 2, unexpected argument | 현재 exec 참여자 옵션을 그대로 옮길 수 없음 |
| 빈 HOME `mcp list --json` | exit 0, 빈 JSON 목록 | 합성 설정 목록만 확인. 실제 계정의 문맥 증거는 아님 |

합성 MCP 서버는 도구 하나의 스키마를 반환하는 고정 로컬 helper뿐이며 도구 실행이나 외부 연결을 하지 않았다. 모델은 한 번도 호출하지 않았고, 실제 계정 파일을 읽지도 않았다. CLI는 합성 CODEX_HOME이 임시 디렉터리에 있어 PATH helper alias 생성을 거절하는 경고를 냈지만 진단은 exit 0으로 끝났다.

[재현 스크립트](c3_prompt_probe.py), [선택한 help](c3-help-selected.json), [가린 결과](c3-prompt-results.json)를 함께 남겼다. 실행 방법과 저장 위치는 [PORTABLE.md](PORTABLE.md)를 따른다. raw는 저장소 밖에만 생성하며 공개 기록에 복사하지 않는다. 출력 hash는 임시 경로·환경에 따라 바뀌므로 그것만으로 실행 계약의 동등성을 주장하지 않는다.

## 추가: app-server 읽기 전용 목록의 실제 대조

먼저 설치판의 `app-server generate-json-schema --help`를 읽고, `--experimental --out <합성 폴더>`로 schema를 생성했다. `ClientRequest`에 세 메서드가 실제로 들어 있었고 필수 인자도 확인했다. 현재 설치판의 schema를 기준으로 요청을 만들었으며 문서에만 있는 필드를 추측해 보내지 않았다.

같은 합성 HOME·별도 네트워크 namespace·`isolation.run()` 안에서 `app-server --stdio`를 실행했다. `initialize`/`initialized` handshake 뒤 아래 세 요청만 순서대로 보냈다. 각 응답 대기는 20초 상한이었고 실제로는 모두 상한 안에 응답했다. `turn/start`, `thread/start`, send-message, login, tool call, 설정 쓰기는 없었다.

| 요청 | 설치 schema에 맞춘 인자 | 실제 응답과 대조 |
|---|---|---|
| `skills/list` | 합성 cwd 하나, `forceReload=true` | skill 7개(repo 1·system 6), error 0. 합성 skill description 표식은 있고 본문 표식은 없음 |
| `mcpServerStatus/list` | `detail=toolsAndAuthOnly`, `limit=20`, threadId 없음 | 서버 1·도구 1, 합성 도구 표식과 `inputSchema` 확인. toolsError 없음, 다음 cursor 없음. 서버 지시문 표식 없음, runtimeStatus=null |
| `app/installed` | `forceRefresh=false`, threadId 없음 | `apps=[]`. 합성 계정 없는 환경의 저장된 목록이며 실제 계정의 앱 부재 증거가 아님 |

합성 MCP의 방법 로그는 initialize→notifications/initialized→tools/list뿐이다. 도구 실행은 없었다. app-server의 stdin을 닫은 뒤 3초 안에 종료되지 않아 종료 신호를 보내 정상 exit 0으로 정리했고, 바깥 실행도 exit 0·`tree_confirmed_empty=true`였다. 실제 로그인·기존 daemon·사용자 task에는 연결하지 않았다.

**메운 부분:** prompt-input에 없었던 합성 MCP 도구의 이름·입력 schema를 실제 목록 RPC로 읽을 수 있었다. skill metadata도 두 경로에서 대조할 수 있다. **남은 부분:** MCP 지시문, 최종 요청 전체, 실제 계정 connector 목록, 현재 exec의 ignore/profile/ephemeral 구성과의 동등성, thread별 적용 상태는 확인되지 않았다. 서로 다른 진단 출력의 합집합을 최종 모델 요청이라고 부르면 안 된다.

[재현 스크립트](c3_appserver_probe.py), [가린 결과](c3-appserver-results.json), [설치 schema 발췌](c3-schema-excerpts.json)를 함께 남겼다. raw 합성 응답·stderr·MCP 방법 로그는 필수 `--output-dir`이 지정한 저장소 밖에만 남긴다. 공개 요약에는 개수·scope·표식 boolean·응답 hash만 남겼으며 실제 계정 값·경로·도구 목록 전체를 넣지 않았다.

## 다음 실험을 구체화하면

1. **완료:** 합성 HOME·네트워크 차단에서 app-server의 `skills/list`·`mcpServerStatus/list`·`app/installed`를 읽어 표식 발견과 도구 목록을 대조했다. thread·turn·모델 없이 inventory 보완이 가능하지만 최종 요청 증명은 아님을 확인했다.
2. 같은 설치판에서 **exec와 진단이 공유하는 구성 경로**를 확인한다. 특히 `--ignore-user-config`, `--ignore-rules`, permission profile, ephemeral, model, 작업 폴더·HOME·연결 역할이 같아야 한다. debug는 해당 exec 플래그를 받지 않으므로 문서만으로 같은 계획이라 선언하지 않는다.
3. 최종 request의 `input`뿐 아니라 `instructions`·`tools` 등 전송 필드 전체를 볼 수 있는 공식 진단/trace가 있는지 더 확인한다. 없으면 무모델 fixture 전송 캡처는 합성 HOME에서만 먼저 설계한다. 이 구성은 새 진단 변형이며 실계정 호출과 같다고 자동 대응시키지 않는다.
4. 충분한 수집 경로가 확인된 뒤에만, 승인된 범위에서 실제 계정 연결을 최소화한 비교를 한다. 계정별 도구 cache·플러그인 metadata·원격 도구를 offline 목록만으로 완전히 재현할 수 없다면 C3는 계속 미해결로 둔다. 사용자 정책 완화로 `observed`를 대신하지 않는다.

따라서 지금은 권한이 없어 멈춘 것이 아니다. 무모델 입력 관측은 가능해졌지만 **현재 exec 계약과의 동등성 및 최종 도구 전송 증거**가 아직 없어서 strict blind의 성공 판정을 보류하는 것이다.

