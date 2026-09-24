# Claude 재관측 준비 — 2026-09-24, aux-pc-wsl

Codex 세션이 사용자 PC의 WSL2 `Ubuntu-24.04` 로그인 셸에서 확인했다. 기준 main은 `56bf5afcce385b8bec33f118421428af99944534`이며 이 기록과 함께 추가한 [`claude_preflight.py`](../../../../tools/w2/claude_preflight.py)를 썼다. **모델 호출과 승인 초기화는 없었다.** 이전 사용자가 허용한 인증 연결 진단 범위에서 로그인 상태만 확인했다. 실제 실행 허가와 기존 manifest 판정은 바꾸지 않았다.

## 확인한 것

[`preflight.json`](preflight.json)에 가린 계획·현재 help의 관련 줄·무모델 결과를 남겼다. 공개 전에 내용을 읽었으며 인증 값·계정 식별자는 넣지 않았다.

- 실제 설치된 Claude Code는 **2.1.280**이고 설치 경로에서 읽은 버전과 `--version` 출력이 맞았다.
- version/help는 실제 로그인 폴더가 없는 합성 HOME에서 실행했다. CLI 실행은 모두 `isolation.run()`을 통했다.
- 이어서 controller 계획과 같은 격리 경계에서 `claude auth status`만 실행했다. `loggedIn=true`, `authMethod=claude.ai`, `apiProvider=firstParty` 조합을 확인했고, 공개 요약에는 구독 로그인 확인 여부만 남겼다. 모든 진단이 exit 0 및 전체 자손 종료 확인으로 끝났다.
- controller/`plain-claude` 계획은 `--output-format json`, `--tools ""`, 공통 자료 없음이며 판은 **`claude-code@97d0508b4567`**이다.
- 출력만 `stream-json --verbose`로 바꾸는 진단 계획은 **`claude-code@af2906b422af`**로 다르다. 실제로 실행하지 않았고 controller 명세도 바꾸지 않았다.

## 현재 출력으로 증명할 수 있는 범위

| 항목 | 방법과 판정 경계 |
|---|---|
| 전송 | 승인 뒤 `plain-claude`를 정확한 판으로 실행하면 stdin 전달, JSON 결과 판정, 모델 일치, 전체 자손 종료, controller 수용 관문을 확인할 수 있다. 모든 입력 바이트 소비의 증명은 아니다 |
| 권한 | help는 `--tools ""`가 built-in 도구를 끈다고 설명한다. 그러나 현재 단일 result JSON은 실행 도구 목록/집행 흔적을 제공하지 않는다. 거절 0개나 파일이 생기지 않았다는 결과만으로 권한 관측 성공을 기록하지 않는다 |
| 문맥 | 현재 결과는 모델에 들어간 전체 지시문·메모리 목록을 입증하지 않는다. `--restricted`의 help는 사용자/프로젝트/local 설정을 무시한다고 설명하며 managed 설정은 적용된다. 이를 CLAUDE.md·메모리·플러그인의 완전한 부재로 확대하지 않는다 |
| stream-json init | 도구·MCP·스킬 목록을 진단하는 보조 자료다. 출력 변형의 판은 controller와 다르고, init 자체도 전체 지시문/메모리 부재를 보증하지 않는다. controller의 문맥 관측을 승격하지 않는다 |

도구의 `assess`는 실제 `plain-claude` 판, 성공한 수용 관문, 입력·종료·위반 상태를 확인한 경우에도 **전송만** 근거가 있다고 표시한다. 모델이 "지시문이 없다"고 답하거나 임의 init 목록이 비어 있어도 권한·문맥은 `insufficient`이며 실행 허가를 만들지 않는다. 이 단어는 진단 보고의 판단이고 manifest 상태값을 새로 추가한 것이 아니다.

## 실행 방법 — 여기까지는 모델 없음

WSL 로그인 셸, 저장소 루트에서:

```bash
python3 tools/w2/claude_preflight.py plan --model claude-sonnet-5
python3 tools/w2/claude_preflight.py preflight --model claude-sonnet-5
```

실제 로그인 상태 진단까지 사용자가 허용한 경우에만 두 번째 명령에 `--real-auth`를 붙인다. 결과 저장은 저장소 밖에서 시작해 직접 읽고 옮긴다. `claude-sonnet-5`는 다음 실험의 요청값이며 이번에 모델 가용성을 확인한 것은 아니다.

이미 승인된 실제 호출 결과가 있다면:

```bash
python3 tools/w2/claude_preflight.py assess <저장소-밖-결과.json> --revision claude-code@97d0508b4567
```

판은 이번 기기의 현재 연결 기준이다. 코드·연결·버전이 바뀌면 `plan`과 preflight부터 다시 확인한다.

## 사용자가 고를 실제 관측 범위

아래는 제안이며 **이번 턴에서 승인 장부에 기록하거나 호출하지 않았다.** 기존에 소진한 K46/2단계 예산을 재사용하지 않는다.

1. **전송부터 확인:** Claude `claude-sonnet-5` 1회, 300초 이내. 기존 `observe.py call plain-claude claude-sonnet-5`를 그대로 쓴다. 합격해도 권한·문맥/실행 허가는 미해결이다.
2. **진단까지 비교:** 위 1회와 별도 stream-json 진단 1회, 각각 300초 이내, 총 최대 2회. 추가 진단은 같은 빈 작업 폴더/빈 도구/자료 없음이고 출력 옵션만 다르다. 별도 승인 예산과 관측 실행 경로를 구현·검토한 뒤 수행해야 한다. 기존 b1은 Read 도구와 자료가 있어 대신 쓸 수 없다. 이 선택도 지시문 부재를 확정하지 못한다.

두 선택 모두 Codex 0회, 구독 전용, API/추가 크레딧/자동 대체 없음이다. 사용량 제한, 다른 과금 경로, 예상 밖 결과, 모델 불일치, 입력 미완료, 자손 종료 미확인, 경계 위반, 검토한 판과 불일치 때 provider를 멈춘다. 실패도 호출 상한에 포함하고 재시도하거나 `approve`를 다시 써서 예산을 늘리지 않는다.

문맥을 엄격히 확인하려면 같은 실행 명세에서 모델 전송 직전의 전체 지시문·도구 표면을 볼 수 있는 별도 근거가 필요하다. 현재 help/단일 JSON/init에서는 그 근거를 확보하지 못했다. 진단을 늘리는 것과 독립성 정책을 완화하는 것은 다른 결정이며, 정책 완화를 관측 성공으로 쓰지 않는다.

## 검증

Windows와 WSL에서 `python -m unittest discover -s tests -p test_w2_claude_preflight.py -v`가 성공했다. 시험은 정확한 참여자 판 보존, 진단 판의 구분, 무모델 명령 허용 범위, 진단 실패 때 실제 auth 미연결, 인증 식별자 미노출, 불완전/다른 판의 결과 및 모델 자기 보고를 관측 성공으로 올리지 않는 조건을 검사한다. 실제 모델·CLI 권한 집행·문맥 독립성 시험은 아니다.
