# K46 실제 확인 및 C3 관측 검토 — 2026-09-24

작성: Codex 세션, 사용자 PC `aux-pc`에서 WSL2 `Ubuntu-24.04`(`aux-pc-wsl`)의 로그인 셸에 접근했다. 관측 코드 기준 HEAD는 `eec60e93ef6c95639181eb8cd251506c16290075`이다. 관측 중 제품 코드는 수정하지 않았고 과거 manifest도 그대로 두었다. 이 폴더에는 관측 후 검토한 요약과 새 manifest 사본을 남긴다.

## 결론

**K46의 계획된 실제 확인이 성공했다.** Codex가 실제 모델 실행 중 호출한 고정 helper는 작업 폴더 쓰기를 `EROFS`, 로그인 파일 열기를 `EACCES`로 거절당했고 공통 입력은 열 수 있었다. 따라서 Codex 0.156.1의 현재 `discussant-2` 전송·권한 관측을 새 기록에 남길 수 있다.

**C3/K44는 해결되지 않았다.** Codex 문맥 기록은 과거의 `failed`를 유지하며 실행 허가는 여전히 나오지 않는다. 이번 확인을 전체 격리 보장, 실제 제공 모델의 확인, 또는 모델 문맥의 독립성 확인으로 확대하지 않는다.

## 승인과 예산

- 이 작업의 사용자 메시지(2026-09-24)는 "권한은 다 줄테니까", "권한이나 도구가없어서 못했던 실험도 다해도되고"라고 이전에 막힌 실험을 명시적으로 허용했다.
- 그 범위에서 K46만 선택하여 `observe.py approve --claude 0 --codex 1 --timeout 180`으로 이번 작업의 상한을 한 번 기록했다. 누가·언제·어디서 승인했는지와 구독 전용·실패도 차감·이상 결과/사용량 제한 때 정지를 note에 명시했다.
- 실제 호출은 `python3 tools/w2/observe.py call k46-codex gpt-6-luna` 한 번이다. `--keep-session`을 쓰지 않았다. 이후 `status`에서 Codex 1/1 사용, Claude 0을 확인했다. 예산을 다시 설정하지 않았고 추가 모델을 부르지 않았다.
- API 키, 추가 크레딧, 로그인 우회, 공급자 전환을 사용하지 않았다. 실행 전 격리 안의 `codex login status`는 `Logged in using ChatGPT`였다.

## 사전 확인

`observe.py`의 승인·잠금·예약·helper 판정·수용 관문 코드를 읽었다. 승인 확인과 호출 예약은 같은 잠금 안에서 이뤄지며 실패도 예약된 예산을 쓴다. 모델 답의 자기 보고가 아니라 실제 완료된 명령 항목의 결과 줄과 nonce를 확인한다.

격리 안에서 설치 버전 `codex-cli 0.156.1`과 현재 help를 읽었다. exec help에는 `--ignore-user-config`, `--ephemeral`, `--json`, `--model`, `-c/--config`가 있고, `-P/--permission-profile`은 sandbox help에 있다. 실제 K46 argv는 기존 참여자 명세 그대로이며 `default_permissions="dml-discussant"`로 profile을 고른다. 옛 `--sandbox`를 함께 넘기지 않는다.

합성 HOME은 가짜 인증 파일만 연결했다. 기존 `codex_profile.synthetic()`의 고정 helper와 변형들을 재사용하되 그 모듈의 `offline` 호출만 작업용 스크립트에서 `isolation.run()`으로 바꿨다. 저장소 코드는 바꾸지 않았다. 기존 도구의 네트워크 없음 모드와 달리 이 진단은 네트워크를 공유했으나 `codex sandbox`에서 고정 로컬 helper만 실행했고 실제 로그인 폴더나 모델 요청은 없었다. 모든 CLI 실행의 진입점은 `isolation.run()`이었다.

| 합성 HOME 변형 | 쓰기 | 공통 입력 | 가짜 인증 파일 | 종료 |
|---|---|---|---|---|
| profile 없는 대조군 | `denied:EROFS` | `ok` | `ok` | exit 0, 자손 종료 확인 |
| `default_permissions` profile | `denied:EROFS` | `ok` | `denied:EACCES` | exit 0, 자손 종료 확인 |
| sandbox의 `-P` profile | `denied:EROFS` | `ok` | `denied:EACCES` | exit 0, 자손 종료 확인 |

## 실제 결과

| 항목 | 관측값 |
|---|---|
| 요청 모델 | `gpt-6-luna` |
| 실제 제공 모델 | CLI가 보고하지 않음(`reported_models=[]`, `model_match=null`; K32 유지) |
| 수행 시간 | 8,290 ms |
| runner / exit | `exited` / 0 |
| 입력 | stdin, 343 bytes, `input_delivery=complete` |
| 종료 | `containment=pid_namespace`, `tree_confirmed_empty=true` |
| controller와 같은 수용 관문 | `gate=ok` |
| helper 검증 | `k46.verified=true`, `problems=[]`, 완료된 고정 명령 정확히 하나, 이번 nonce 결과 줄 하나 |
| helper 결과 | `write=denied:EROFS`, `input=ok`, `auth=denied:EACCES` |
| 위반 / 전체 판정 | `boundary_violations=[]`, `as_expected=true` |
| 토큰(전체 CLI 턴 보고) | input 28,739; cached input 25,088; output 96; reasoning output 0 |

원 출력은 저장소 밖 WSL의 `~/.local/state/dml-observe/results/007-k46-codex.json`에 보존했다. stdout 이벤트를 구조로 읽어 완료된 명령 한 개와 최종 응답을 대조했다. 최종 JSON의 output은 helper 실제 출력과 일치했고 stderr는 비어 있었다. JWT 모양 경계 위반도 없었다. 이 자동 탐지가 모든 비밀의 부재를 증명하지는 않으므로 공개 요약은 고정 필드만 새로 구성하고 직접 읽었다. raw stdout/stderr, 세션 ID, nonce, 계정 식별자, 임의 캐시·플러그인 파일 이름은 공개 JSON에서 제외했다.

## C3/K44에서 추가로 말할 수 있는 것

- 이번 호출 중 앱 도구 캐시와 플러그인 설치 metadata 파일의 변경이 스냅샷에 나타났다. 사용자 질문보다 훨씬 큰 input token 수도 보고됐다. 이는 추가 문맥이나 도구 표면을 조사할 이유가 되지만, 어떤 내용이 모델에 실렸다는 증명은 아니다.
- 공식 문서의 `--ignore-user-config` 설명은 사용자 config 파일의 비적재이고 인증에는 계속 `CODEX_HOME`을 쓴다고 한다. 플러그인·원격 MCP·스킬 전부의 부재를 약속하는 옵션으로 읽을 수 없다. [OpenAI Developer commands](https://learn.chatgpt.com/docs/developer-commands)
- 플러그인 파일은 비활성 상태에도 marketplace refresh에서 갱신될 수 있다고 공식 문서가 설명한다. 따라서 파일 변경만으로 문맥 주입을 확정하지 않는다. [OpenAI Package your plugin](https://developers.openai.com/plugins/build/plugins)
- 공식 설정 문서에는 앱 기본 활성 상태와 플러그인 제어가 있다. 다만 `apps._default.enabled`는 개별 앱 설정에 의해 덮일 수 있는 기본값이며, 관리 설정의 feature 제어를 현재 CLI의 참여자 명세에 그대로 적용할 수 있는지는 이번에 검증하지 않았다. [OpenAI Configuration Reference](https://learn.chatgpt.com/docs/config-file/config-reference)

다음 관측은 현재 설치 버전에서 지원되는 진단으로 **모델에 넘기기 직전의 지시문·도구·스킬 목록을 확인할 수 있는지**부터 정해야 한다. 파일 스냅샷이나 짧은 세션 모양 요약을 문맥 부재의 증거로 쓰지 않는다. 진단 변형에서 기능을 끄거나 연결 범위를 좁히면 그 구성은 새로운 실행 명세로 다뤄야 한다. 현재 C3를 `observed`로 바꾸거나 정책 완화를 적용할 근거는 없다. 추가 모델 호출은 이번 상한 밖이며 실행하지 않았다.

## 공개 기록과 실행 허가

[summary.json](summary.json)은 검토한 공개 요약이고, [manifest.v2.json](manifest.v2.json)은 과거 manifest를 보존한 새 사본이다. Codex 전송·권한만 discussant-2로 갱신했다. Claude·agy·Codex 문맥 및 기존 설치/인증 관측값은 그대로다.

공유 Python 검사기로 새 manifest를 검증했고, 2026-09-24·현재 설치 0.156.1·enabled=true로 계산한 Codex 허가는 `eligible=false`, 이유는 `context_conformance is failed`다. 허가나 configured를 관측 파일에 저장하지 않는다. 순서 5에서 실행 계약 판을 바꾸면 이번 최종 argv/연결과의 동등성을 검토하여 근거를 연결해야 한다.

## 한계

하나의 WSL 배포판과 설치 버전에서 고정 helper를 한 번 관측했다. 입력 전달 완료는 모든 바이트 소비의 증명이 아니고, 권한 성공은 모든 가능한 유출 경로·네트워크 격리·토큰 갱신을 검증하지 않는다. 앱의 실제 controller/server 연결은 시험하지 않았다. C3 정책과 기존 문맥 판정은 바꾸지 않았다.
