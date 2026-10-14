# 바닥부터 만든 부분과 다른 프로젝트에서 가져올 것 (2026-10-14)

사용자 요청(2026-10-14): 이 프로젝트가 너무 바닥부터 만들다 보니 현실성 없는 제약이 많다. 다른 프로젝트를 참고해 사용자가 말한 불편([불편 기록과 해법](../session-pain-points-2026-10-14/README.md)의 P1–P22)도 풀리는지, 참고할 코드가 있는지 봐 달라.

- 작성: claude 세션, 주 PC `DESKTOP-T0UDE01`의 Windows 쪽(Claude 데스크톱 앱). WSL에서는 CLI 판만 읽었다(Claude Code 2.1.280, Codex 0.156.1 — 관측 기록과 같은 판). 모델 호출 없음. 아무것도 설치·실행하지 않았다.
- 방법: 이 저장소의 규칙·코드·문서를 읽어 제약마다 왜 생겼고 지금 무엇이 드는지 적었다(§2). 다른 프로젝트는 세 갈래로 나눠 조사 에이전트가 원문을 읽었고, 작성 세션이 판단에 쓴 주장을 원문에서 다시 확인했다(§3, 확인 범위는 §7).
- 이 문서는 **제안**이다. 코드와 참여자 계획은 바꾸지 않았다.

## 결론 먼저

1. **제약 대부분은 이유가 있다. 실제로 발목을 잡는 것은 "실제 실행의 문"(K1) 하나다.** 기기마다 관측·등록해야 하고, 기록은 30일이 지나면 만료되고, CLI 판이 고정돼 있다. 그래서 CLI를 올리거나 한 달이 지나면 실제 실행이 모두 멈춘다. 샌드박스를 바꿔도 이 문은 없어지지 않는다(§3.3). 안전 원칙(구독만 쓰기, 로그인 파일 안 읽기, 독립 정족수)은 그대로 두고 엄격 모드와 일상 모드로 나누기를 권한다. 사용자가 정할 일이다(결정 D, §6). 코드에는 이미 비슷한 느슨한 경로(`allow_context_unverified`)가 있다.
2. **이 앱의 핵심 흐름(독립 답 → 익명 검토 → 합성)은 이제 흔하다.** cli-council·agent-council·deliberation(모두 MIT)이 같은 일을 한다. 그 코드에 의존하지 말고 참고와 시험 기준으로 쓴다. 원장, 독립성이 확인된 참여자만 세는 정족수, 자손 종료 확인, 호출 상한, 원문 대조를 함께 하는 곳은 없어서 그것이 이 앱의 몫으로 남는다. 2026-09-22 외부 검토와 같은 결론이다.
3. **배선은 공식 도구 쪽으로 옮길 수 있다.**
   - Codex: OpenAI 공식 파이썬 SDK(app-server)와 OpenAI가 낸 Claude Code용 Codex 플러그인.
   - Claude: `claude -p`의 새 공식 기능 — `--json-schema`, 도구 호출을 미뤘다가 잇는 `defer`, `--permission-prompts none`, `claude auth status`.
   - Agent SDK와 ACP는 지금은 쓰지 않는다. 로그인 규정이 걸리고, ACP는 남이 만든 번역 계층이 하나 더 생긴다.
4. **큰 위험 하나.** Claude Code 공식 문서는 `--bare`가 앞으로 `-p`의 기본이 되고, bare 모드는 구독 로그인을 읽지 않는다고 적었다. 그대로 오면 이 앱이 구독으로 Claude를 부르는 방식이 막힌다. WSL에 설치된 판은 2.1.280이고 최신은 2.1.299다. 판을 올리기 전에 확인할 목록에 이것을 넣는다.
5. **다른 프로젝트의 불편 일부는 오늘 바로 쓸 도구가 있다.** 이 앱을 고치지 않고 그 프로젝트에서 먼저 쓸 수 있다.
   - GPU 큐와 완료 판정: pueue
   - GPU와 온도 보기: nvitop·gpustat·LibreHardwareMonitor
   - 작업 공간 충돌: worktree와 worktrunk의 고정 포트
   - Codex 두 번째 의견: codex-plugin-cc
6. **자리 비움(P7)은 공식 기능으로 상당 부분 된다. 남은 것은 멈춤 규칙이다.** continuous-claude의 예산과 Ralph의 회로 차단 기준·허용 도구 목록을 빌린다. continuous-claude는 권한 건너뛰기가 기본값이라 그 부분은 빌리지 않는다.

## 1. 이 앱이 직접 만든 것

2026-09-21에 시작해 3주 남짓 동안 아래를 모두 직접 만들었다(2026-10-14 기준, 날짜 기록이므로 숫자를 적는다).

| 부분 | 하는 일 | 크기 |
|---|---|---|
| [core/](../../../core/README.md) | 셸 없이 CLI 실행, CLI 명령 조립과 결과 해석, bubblewrap 격리, 참여 자격 계산, 정족수 | 파이썬 약 2천 줄 |
| [app/](../../../app/README.md) | controller, SQLite 원장, 웹 서버, 역할판·검토·합성·기억·조회 | 파이썬 약 9천6백 줄 + 화면 약 3천 줄 |
| [tools/w2](../../../tools/w2/README.md)와 [등록](../../../app/registration.py) | 기기마다 참여자를 관측해 기록을 만들고 등록 | 파이썬 약 1천6백 줄 + 관측 기록 |
| 시험 | 오프라인 시험 | 약 1만7천 줄 — 앱·도구 코드보다 많다 |
| 문서 | 설계(v0.2–v0.4), 검토, 실험, 조사, 인계 | 마크다운 287개, 약 3.9 MB |

이 방향은 처음 계획과 다르다. [2026-09-22 외부 검토](../../reviews/2026-09-22-external-review.md)는 여러 CLI를 띄우고 결과를 모으는 배선은 이미 여러 곳에서 해결돼 있으니 기존 구현을 adapter로 흡수할 수 있는지 먼저 평가하라고 권했고(그 검토 7.3, 권고 10), 2026-09-23 인계도 "배선은 재발명하지 않는다"고 적었다([보관 인계](../../handoff/2026-09-23-before-review.md)). 그 뒤 어댑터는 CLI 직접 실행을 우선하기로 했고(인계 2절 12), 흡수 가능성 평가는 기록이 없다. 이 문서가 그 평가를 늦게나마 한다.

## 2. 제약 점검

"막으려는 것"은 그 제약을 만든 기록에서 가져왔다. 다른 프로젝트가 같은 위험을 어떻게 다루는지는 §3에 있다.

| | 제약 | 막으려는 것 | 지금 드는 비용 | 제안 |
|---|---|---|---|---|
| K1 | **실제 실행의 문.** 기기마다 CLI를 관측한 기록(설치·로그인·구조화 출력·문맥·권한 다섯 칸)을 만들고 그 기기에 등록해야 실제 실행이 열린다. 30일이 지나거나 CLI 판·참여자 옵션이 바뀌면 거절한다. 문맥 미확인 허용도 이 문을 지난다([eligibility](../../../core/eligibility.py), [등록](../../../app/registration.py)) | 다른 PC의 기록을 빌려 쓰기. 판이 바뀐 CLI가 사용자 지시문·메모리를 몰래 싣거나 금지한 읽기를 하는 것 | 재관측마다 WSL 명령 열 개 넘게, 모델 호출 다섯 번, 사람이 요약을 읽고 PR([SETUP 4절](../../SETUP.md)). 그동안 실제 실행이 모두 멈춘다. 주 PC 기록은 2026-11-09부터 만료. 추론 강도 연결과 CLI 업데이트가 이 문 때문에 미뤄져 있다 | **엄격 모드와 일상 모드로 나눈다.** 일상 모드는 모델 없는 점검(구독 로그인, 과금 변수 제거, 판)만 하고 결과에 "문맥 미확인"을 붙여 실행한다 — 독립 정족수에 세지 않는 지금 규칙은 그대로. 관측 기록은 "독립성 확인" 표시와 엄격 비교에만 쓴다. 재관측은 명령 하나로 묶는다 |
| K2 | **직접 만든 격리.** bubblewrap 래퍼가 빈 HOME·/tmp, 읽기 전용 연결, PID namespace로 자손 종료 확인을 한다. blind 참여는 WSL에서만 한다([isolation](../../../core/isolation.py), 인계 2절 15·16) | 참여자가 다른 초안·원장·사용자 파일을 읽거나 쓰는 것. 끝났다고 했는데 자손 프로세스가 남는 것 | 격리 코드와 시험을 직접 유지한다. Windows에는 파일·네트워크 격리가 없어 blind 실행을 못 한다(자손 종료 확인은 Windows Job Object로 이미 한다). 참여자 옵션을 바꿀 때마다 K1의 재관측 | 유지한다. 유지보수되는 샌드박스는 그림자 시험으로 비교만 한다(§3.3) |
| K3 | **호출 관문.** 상위 모델 호출은 한 번에 하나, 검토자는 차례로, 자동 재호출 없음. 앞 검토자가 실패하면 남은 검토를 열지 않고, 실패한 팀원 자리는 채우지 않는다. 다듬기·제안은 실행당 2번([app 안내](../../../app/README.md)) | 사용량 폭주, 종료 미확인 호출이 쌓이는 것, 실패를 성공처럼 보이는 것 | 느리다. 한 번 실패하면 라운드가 닫혀 사람이 다시 시작해야 한다 — 다른 프로젝트의 P7(자리를 비우면 멈춤)과 같은 모양 | 서로 독립인 호출은 동시에 부른다. 실패한 것은 빼고 진행하되 빈자리를 보인다. 일시적 실패(시간 초과·한도 응답)는 한 번 다시 시도한다. 쓰는 양은 K4로 막는다 |
| K4 | **원장당 호출 상한**(Codex 5·Claude 5), 상한을 늘리지 않음 | 한 실험이 사용량을 다 쓰는 것 | 다 쓰면 앱이 새 원장을 열어 큰 불편은 아니다. 다만 상한이 실제 남은 한도와 무관해서 사용자가 주간 %를 따로 본다(P10) | 원장 상한은 안전망으로 두고, 실제 정책은 5시간·주간 한도 %로 정한다("몇 %에서 멈춤") |
| K5 | **사람이 모든 시작과 판단.** 자동 예약·보낸 편지함 없음 | 모델이 스스로 일을 키우거나 사람 모르게 사용량을 쓰는 것 | 밤에 멈추고 끝난 결과가 묻힌다(P2·P7) | [불편 기록의 결정 A·B](../session-pain-points-2026-10-14/README.md) 그대로 |
| K6 | **문서 규칙.** 개수 재기술 금지, 인계 크기 상한, 날짜 기록 수정 금지, 인계 3절 모양 CI, 도구마다 현재 사용처 검사 | 문서가 부풀고 서로 어긋나는 것 — 사용자의 P12·P19와 같은 걱정 | 문서가 코드보다 훨씬 크다(§1). PR마다 인계를 상한 안으로 깎는 손질이 든다 | 규칙은 둔다. 지금 상태는 상황판이 보여 주게 해서 인계에 손으로 적는 양을 줄인다 |
| K7 | **지킬 것.** 구독 CLI만, 로그인 파일 안 읽기, 독립 정족수를 세는 법, 공개 뒤 합성과 원문 대조 | 사용자가 정한 비용 원칙과 이 앱의 존재 이유 | — | 유지. §3의 어느 프로젝트도 이것을 대신해 주지 않는다 |

## 3. 다른 프로젝트

### 3.1 여러 모델 묶기와 CLI 연결

이 앱의 핵심 흐름(독립 초안 → 공개 → 교차검토 → 합성)을 하는 공개 구현이 2026년에 여럿 생겼다. 이 흐름 자체는 이제 흔하다. 정족수(agent-council의 N−1, deliberation의 하한)나 공개 관문(deliberation)을 둔 곳은 있지만, 원장, 독립성이 확인된 참여자만 세는 정족수, 자손 종료 확인, 호출 상한, 원문 대조를 함께 하는 곳은 없었다.

| 프로젝트 | 라이선스·활동 | 하는 일 | 가져올 것 | 판단 |
|---|---|---|---|---|
| [codex-plugin-cc](https://github.com/openai/codex-plugin-cc)(OpenAI 공식) | Apache-2.0, 2026-07-08 | Claude Code 안에서 Codex에게 검토·위임을 맡긴다. `codex app-server`로 스레드를 열고 승인 정책은 기본 `never`, 검토는 읽기 전용 | 검토 결과 스키마(판정·지적·파일·줄·확신도), 운영체제별 프로세스 트리 종료, 상태·결과·취소 명령 | **참고하고 다른 프로젝트에서는 바로 써 볼 만하다.** 웹 AI를 손으로 오가던 검토(P16)를 Claude Code 안에서 공식 도구로 한다. 다만 위임(`rescue`)은 기본이 쓰기 가능이다 |
| [openai-codex](https://github.com/openai/codex/tree/5670b1c18e861e5f89bafaff768b86ed579edd81/sdk/python)(OpenAI 공식 파이썬 SDK, PyPI 0.162.1) | Apache-2.0 | `codex app-server`를 감싼 라이브러리. 스레드 시작(샌드박스·승인 모드), 실행, 스트림, 출력 스키마, 이어 부르기 | 이 앱의 Codex 쪽 명령 조립·JSONL 해석·이어 부르기 | **시험 후보.** 기본 승인 모드가 `auto_review`라 명시적으로 막아야 하고, 닫을 때 직계 자식만 끝내므로 이 앱의 자손 종료 확인은 남긴다. 설치된 Codex 0.156.1과 프로토콜이 맞는지는 확인하지 않았다 |
| Claude Code 공식 옵션 | — | `claude -p`의 `--json-schema`(검증된 JSON 출력), `--no-session-persistence`, `--restricted`, `--permission-prompts none`, 그리고 `claude auth status`(로그인 방식 JSON, 모델 호출 없음) | 형식 모듈의 자유 글 해석 대신 스키마 출력, 로그인 방식 확인 | **바로 쓸 수 있다.** Agent SDK는 Anthropic이 제3자 제품이 claude.ai 로그인을 제공하는 것을 허락하지 않는다고 적어 쓰지 않는다([Agent SDK 개요](https://code.claude.com/docs/en/agent-sdk/overview)). Codex 0.156.1의 `exec`도 `--output-schema`·`--ephemeral`이 있다([관측한 help](../../experiments/v04-01-inventory/hosts/aux-pc-wsl/help/codex-2.txt)) |
| [cli-council](https://github.com/LARIkoz/cli-council) | MIT, 2026-07 시작, 별 0 | 파이썬 표준 라이브러리만으로 이 앱과 같은 흐름: 첫 의견을 동시에 → "Response A/B" 익명 순위 → Borda 합산 → 의장 합성 → 감사·레드팀 | [익명화·순위·의장](https://github.com/LARIkoz/cli-council/blob/b47b43b573e06c344544e0dacbab8d124fff2c3a/council/stages.py#L99-L211), [판정·순위 해석기](https://github.com/LARIkoz/cli-council/blob/b47b43b573e06c344544e0dacbab8d124fff2c3a/council/aggregate.py#L48-L95), 빈 출력은 실패로 보는 규칙 | 참고와 시험 기준으로. 한 사람이 만든 새 프로젝트이고 샌드박스가 없다 |
| [agent-council](https://github.com/yogirk/agent-council) | MIT, 2026-04, 별 91 | 세 CLI를 동시에 부르고, 2/3이 오면 30초 기다린 뒤 진행(정족수 N−1). 익명 검토 선택. 부른 CLI가 의장 | [오류 분류·사전 점검](https://github.com/yogirk/agent-council/blob/f6d1e1ad9c6597c03e7922f2bae41c73b7b760b2/src/adapters.ts#L86-L162), 세 CLI의 실제 출력 견본(시험 자료) | 실패한 참여자를 빼고 진행하는 방식(K3)의 참고 |
| [deliberation](https://github.com/antonbabenko/deliberation) | MIT, 2026-10-11, 별 172 | MCP 서버. Codex는 `--sandbox read-only`, 자식 환경에서 `OPENAI_API_KEY`를 뺀다(키가 있어 조용히 과금된 일이 있었다고 적음), 600초 상한. blind 선제출이 끝나야 서로 공개, 정족수 하한, 회로 차단 | [Codex 실행·환경 정리](https://github.com/antonbabenko/deliberation/blob/dc4e3e1856e681ad02433566e0cfe4adbb6051ad/core/providers/codex.js#L97-L124), [공개 관문](https://github.com/antonbabenko/deliberation/blob/dc4e3e1856e681ad02433566e0cfe4adbb6051ad/core/consensus-loop.js#L252-L263) | 이 앱의 공개 규칙·환경 정책과 대조할 참고 |

**쓰지 않을 것.**
- [Claude Code Bridge](https://github.com/SeemSeam/claude_codex_bridge): AGPL-3.0이다. README에 따르면 로그인 파일을 세션별 폴더로 복사한다.
- [Every Code](https://github.com/just-every/code): Codex를 고쳐 만든 별도 실행 파일이라 자기 로그인을 쓰고, 쓰기 모드에는 운영체제 샌드박스가 없다.
- PAL `clink`: 권한 건너뛰기가 기본값이고, 2025-12 이후 커밋이 없다.
- claude-codex-gemini: GPL-3.0이다.
- karpathy/llm-council: 라이선스 파일이 없어 생각만 참고한다.

모델이 순서를 짜는 방식(Every Code의 매크로 등)은 다른 프로젝트의 "코디네이터 과부하"(P18)와 같은 구조다. 코드가 순서를 짜는 방식(cli-council·agent-council·deliberation, 그리고 이 앱)이 맞다.

### 3.2 CLI를 부르고 승인·상태·자리 비움을 다루기

| 무엇 | 하는 일 | 불편 | 판단 |
|---|---|---|---|
| `claude -p`의 새 공식 기능 | `defer`: PreToolUse 훅이 도구 호출을 미루면 `-p` 실행이 `tool_deferred`로 끝나고, 부른 쪽이 답을 받아 `--resume`으로 이어 간다(`-p`에서만, 한 차례에 도구 호출이 하나일 때). `--permission-prompts none`: 답할 사람이 없으면 거절한다. `claude auth status`: 로그인 방식을 JSON으로 준다 | P6, P11 | **이 앱의 승인 수신함을 여기에 얹는다.** 승인을 창마다 묻지 않고 앱의 한 목록에서 받는다([훅 문서](https://code.claude.com/docs/en/hooks) "Defer a tool call for later") |
| [Claude Agent SDK](https://github.com/anthropics/claude-agent-sdk-python)(파이썬 MIT, TS 비공개) | `claude`를 stream-json으로 띄우고 승인 콜백·훅·이어 부르기를 준다. 실험 기능 `get_usage`가 5시간·주간 한도 이용률을 준다 | P6, P10 | **의존하지 않고 코드만 참고한다.** 공식 문서가 제3자 제품이 claude.ai 로그인을 제공하는 것을 허락하지 않는다([법적 고지](https://code.claude.com/docs/en/legal-and-compliance)). SDK 패키지는 기본으로 자기 안에 든 `claude` 실행 파일을 써서, 이 앱이 판을 고정해 관측한 실행 파일과 달라진다(`cli_path`로 바꿀 수는 있다). `get_usage`는 이름부터 "바뀔 수 있으니 기대지 말라"는 실험 기능이다 |
| Codex app-server와 공식 파이썬 SDK | 승인 요청에 accept·acceptForSession·decline·cancel로 답한다. `account/rateLimits/read`로 한도를 읽고, `thread/resume`+`turn/start`로 끝난 작업을 이어 깨운다 | P6, P10, P11 | **시험 후보**(§3.1). 이 앱은 이미 app-server로 Codex 한도를 읽는다 |
| ACP 어댑터([claude-agent-acp](https://github.com/agentclientprotocol/claude-agent-acp)·[codex-acp](https://github.com/agentclientprotocol/codex-acp), Apache-2.0)와 파이썬 SDK | 세션·승인 요청 중계·취소·스트림을 한 규약으로 묶는다 | P6 | **지금은 아니다.** 공식 경로 둘 위에 남이 만든 번역 계층을 하나 더 얹는다. 2026-09-23 이후 codex-acp는 호환이 깨지는 2.0.0을 포함해 새 판을 일곱 번 냈고, 한도 칸이 표준에 없다. 세 번째 에이전트를 붙일 때 다시 본다 |
| [coder/agentapi](https://github.com/coder/agentapi) | 터미널 화면을 읽어 HTTP로 조종한다 | P9 | 저장소가 보관(archived)됐다. 쓰지 않는다 |

**자리 비움(P7).** 공식 기능만으로 상당 부분 된다(2026-10-14 공식 문서).
- **데스크톱 앱 예약 작업:** 앱이 열려 있고 PC가 깨어 있을 때만 돈다. 잠든 동안 놓친 실행은 깨어난 뒤 가장 최근 것 하나만 따라잡는다.
- **`/loop`:** 세션이 열려 있고 쉬고 있을 때만 돌고, 7일 뒤 스스로 끝난다.
- **백그라운드 세션(`claude --bg`):** 잠자기는 견디고, 끄면 멈추고, 권한 질문에서 기다린다.
- **한도가 풀리면 이어 하기:** 대화형 세션, 2.1.234부터.
- **클라우드 루틴:** PC를 꺼도 돈다. 다만 GitHub 저장소를 복제해 Anthropic 클라우드에서 권한 질문 없이 돌고(연구 미리보기), 이 PC의 GPU·파일 일에는 맞지 않는다.

**남는 것은 멈춤 규칙이다.**
- 빌려 올 것:
  - [continuous-claude](https://github.com/AnandChowdhary/continuous-claude)(MIT)의 횟수·비용·시간 예산.
  - [ralph-claude-code](https://github.com/frankbria/ralph-claude-code)(MIT)의 [회로 차단 기준](https://github.com/frankbria/ralph-claude-code/blob/4fd2fe9/lib/circuit_breaker.sh): 진행 없음 3번, 같은 오류 5번, 출력 70% 감소, 권한 거절 2번이면 멈추고 30분 쉰다. 권한은 건너뛰지 않고 허용 도구 목록(`--allowedTools`)으로 준다.
- 빌리지 않을 것: continuous-claude는 권한 건너뛰기(`--dangerously-skip-permissions`)를 기본으로 쓴다.
- 멈추는 기준은 출력 글자를 맞춰 보는 방식이 아니라 한도 사건(`rate_limit_event`)과 이 앱의 원장 상태로 한다.

**상황판(P9).**
- Claude Code와 Codex의 훅은 사건 이름(`PreToolUse`, `PermissionRequest`, `Stop`)이 같다([Codex 훅 이름](https://github.com/openai/codex/blob/78dc2503840d05f4411ae184bb5560ef327fce3c/codex-rs/hooks/src/lib.rs#L23-L37)). 그래서 CLI마다 작은 전송 스크립트 하나로 원장에 모을 수 있다. 설치된 Codex 0.156.1에 이 훅이 다 있는지는 확인하지 않았다.
- 참고할 것: [agents-observe](https://github.com/simple10/agents-observe)(MIT)는 Claude·Codex 훅을 화면으로 모은다. [abtop](https://github.com/graykode/abtop)(MIT)은 상태 줄 값을 파일로 남겨 한도를 보인다.
- 제외: disler의 관측 도구는 라이선스가 없고 API 키를 요구한다.

**휴대폰 알림·승인과 여러 세션 앱.**
- [Happy](https://github.com/slopus/happy)(MIT): 중계 서버를 거친다(내용은 암호화). 앱이 사용 통계(PostHog)를 보낸다.
- Nimbalyst(옛 Crystal, MIT): 사용 통계를 보낸다.
- 이 둘은 밑바탕으로 쓰지 않고 "기다리는 승인 목록"이라는 생각만 참고한다.
- opcode와 claudecodeui: AGPL이라 읽기만 한다.

### 3.3 격리·프로세스·GPU·작업 공간

**전제 정정.**
- Windows에서도 자손 종료는 이미 확인한다. [runner](../../../core/runner.py)가 Windows Job Object의 `ActiveProcesses`로 센다. blind 참여가 WSL에서만인 이유는 Windows에 파일·네트워크 격리가 없어서다.
- 다만 지금은 프로세스를 띄운 **뒤에** Job에 넣는다. 그 사이에 생긴 자식은 Job 밖에 남을 수 있다.
- 정석은 일시 정지 상태로 띄워 Job에 넣고 재개하는 것이다. sandbox-runtime의 Windows 코드가 그렇게 한다.

| 도구 | 라이선스·상태 | 하는 일 | 판단 |
|---|---|---|---|
| [sandbox-runtime](https://github.com/anthropics/sandbox-runtime)(`srt`, Claude Code가 쓰는 샌드박스) | Apache-2.0, "beta research preview" | 명령 하나를 bubblewrap(Linux)으로 가둔다. 네트워크는 프록시를 거쳐 허용한 도메인만 쓴다. 읽기는 기본 허용, 쓰기와 네트워크는 기본 거부. TypeScript·Node가 필요하고 파이썬 API는 없다. Windows는 알파 | **바꾸지 말고 그림자 시험만 한다.** 이 앱의 래퍼와 재료(bwrap·PID namespace)가 같다. 얻는 것은 네트워크 허용 목록과 seccomp다. 네트워크 허용 목록은 지금 격리가 "보장하지 않는 것"으로 적은 localhost 노출을 줄인다. 잃는 것: 빈 HOME 대신 읽기 금지 목록을 일일이 적어야 하고, 셸을 거치고, 1.0 전이라 설정 형식이 바뀔 수 있다 |
| Codex 자체 샌드박스 | Apache-2.0 | `codex exec`가 모델이 낸 명령을 가둔다 | **혼자로는 부족하다.** 이 저장소의 K46 진단에서 read-only 샌드박스 안의 명령이 Codex 로그인 파일을 읽었다([adapters](../../../core/adapters.py)). 지금처럼 이름 있는 권한 profile로 막는다 |
| Claude Code 자체 샌드박스 | 공식 | 셸 명령만 가둔다. Read·Edit·Write 같은 파일 도구, MCP, 훅은 밖에서 돈다([샌드박스 문서](https://code.claude.com/docs/en/sandboxing)) | 참여자 격리를 대신하지 못한다 |
| Docker Sandboxes(`sbx`), container-use | 닫힌 바이너리("All rights reserved") / Apache-2.0 실험 기능 | 에이전트마다 microVM이나 컨테이너를 준다 | 계정·로그인 조건과 WSL2 궁합을 확인하지 않았다. 지금은 아니다 |

**관측 제도는 샌드박스로 없어지지 않는다.** 관측은 CLI가 자기 설정 폴더에서 사용자 지시문·플러그인·연결 앱·훅을 모델 문맥에 싣는지를 본다. 어느 샌드박스도 그것을 대신 보장하지 않는다. 그래서 K1을 푸는 길은 샌드박스 교체가 아니라 정책(일상 모드)이다.

**GPU·작업 큐·온도·작업 공간(P3·P14·P15·P21) — 다른 프로젝트에서 바로 쓸 것.**

| 도구 | 라이선스 | 하는 일 | 쓰는 곳 |
|---|---|---|---|
| [pueue](https://github.com/Nukesor/pueue) | MIT 또는 Apache-2.0 | 작업 큐 데몬이다. 그룹, 그룹별 동시 실행 수, 선행 작업, 지연·우선순위, 그룹 단위 멈춤·종료, `status --json`. 결과를 성공·실패(코드)·시작 실패·종료됨·선행 실패로 나눈다. Windows도 지원한다 | P3: GPU 그룹은 동시 1개로 두고, 빈 시간을 채우는 그룹을 따로 둔다. 예약 시각이 오면 채우기 그룹을 끝낸다(멈추기만 하면 VRAM을 잡고 있다). P15: 완료 표시 파일 대신 큐의 결과 상태를 본다. 주의: 작업을 넣은 셸의 환경을 디스크의 큐에 저장하므로 환경을 비우고 넣는다. WSL에서 돌리면 PowerShell 따옴표 문제(P17)도 피한다 |
| [nvitop](https://github.com/XuehaiPan/nvitop) / [gpustat](https://github.com/wookayin/gpustat) | Apache-2.0 / MIT | GPU 사용률·VRAM·온도·점유 프로세스를 파이썬(nvitop `take_snapshots`)이나 JSON(gpustat `--json`)으로 준다 | P3·P21, 상황판의 GPU 칸 |
| [LibreHardwareMonitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) | MPL-2.0 | Windows의 CPU·GPU 온도와 팬. 내장 웹 서버가 `data.json`을 준다 | P21의 CPU 온도. 관리자 권한이 필요하다. 이 PC 밖으로 열리지 않게 loopback과 인증을 건다 |
| [worktrunk](https://github.com/max-sixty/worktrunk) | MIT 또는 Apache-2.0 | git worktree를 관리한다. 브랜치 이름으로 고정 포트(10000–19999)를 만든다(`hash_port`) | P14: 작업마다 worktree를 쓰고, 포트는 브랜치에서 계산한다 |
| [portless](https://github.com/vercel-labs/portless) | Apache-2.0 | 포트 번호 대신 `.localhost` 이름을 쓰고, worktree마다 하위 도메인을 준다 | P14의 다른 방법 |

빈 GPU 시간을 스스로 채워 주는 성숙한 단일 PC 도구는 찾지 못했다. pueue 그룹, 예약표, nvitop을 조합한다. 채우는 작업은 중간에 끊었다가 다시 시작할 수 있어야 한다.

포트 소유를 지켜 주는 성숙한 도구도 없었다. 그래서 규칙이 아니라 구조로 만든다: 프로세스는 하네스로만 띄우고, 끌 때는 포트가 아니라 이름표(pueue 이름표나 작업별 Job)로 끈다.

## 4. 불편별로 다시 본 해법

[불편 기록과 해법](../session-pain-points-2026-10-14/README.md) §2를 이번 조사로 고친 부분만 적는다. 여기 없는 불편(P4·P5·P8·P12·P13·P19·P20)은 그 문서 그대로다.

| 불편 | 지금 쓸 것(이 앱 밖) | 이 앱에 넣을 것 |
|---|---|---|
| P2 끝난 결과가 묻힘 | `notify_when_idle`, codex-plugin-cc의 상태·결과 명령 | 훅 → 원장 상황판 |
| P3 GPU가 놂 | pueue + nvitop | 상황판의 GPU 칸 |
| P6 다시 묻는 허락 | — | `defer` 훅 + 앱의 승인 수신함, Codex 승인 응답(`acceptForSession`) |
| P7 자리를 비우면 멈춤 | 데스크톱 예약 작업, `/loop`, 백그라운드 세션, 한도 뒤 이어 하기 | 멈춤 규칙(예산·회로 차단), 결정 B |
| P9 무엇이 돌고 기다리나 | `claude agents --json` | 훅 → 원장(agents-observe 방식) |
| P10 한도를 손으로 맞춤 | 상태 줄 `rate_limits`를 파일로(abtop 방식) | Codex app-server 한도 + Claude 상태 줄 값 → K4의 한도 % 정책 |
| P11 세션을 손으로 깨움 | `claude --bg`, Codex `thread/resume` | 결정 B |
| P14 작업 공간 충돌 | worktree + worktrunk·portless, 프로세스는 하네스로만 | — |
| P15 시작·끝 보고가 틀림 | pueue의 결과 상태 | 이미 있는 종료 확인을 바깥 작업에도 |
| P16 웹 AI 손 왕복 | codex-plugin-cc의 검토 명령(Claude Code 안에서 Codex 두 번째 의견) | 교차검토 결과를 스키마로(codex-plugin-cc의 검토 스키마 참고) |
| P17 셸 실패 반복 | pueue를 WSL에서, 명령은 인자 목록으로 | — |
| P18 코디네이터 과부하 | — | 코드가 순서를 짜는 구조 유지(cli-council·deliberation 참고) |
| P21 온도·VRAM 감시 | nvitop·gpustat + LibreHardwareMonitor | 상황판의 PC 칸 |
| P22 넘긴 지시가 순화됨 | 지시문을 모델이 요약하지 않고 그대로 stdin·파일로 넘긴다(cli-council 방식) | — |

## 5. 바꾸는 순서(제안)

1. **지금, 이 앱 밖(다른 프로젝트).** 그 프로젝트의 세션에서 정하고 설치한다.
   - pueue와 nvitop(그리고 LibreHardwareMonitor)으로 GPU 큐와 상태 보기
   - codex-plugin-cc로 Codex 두 번째 의견
   - 작업마다 worktree와 고정 포트
2. **이 앱, 작은 것부터.** 기술 판단이라 세션이 정하고 알린다(인계 2절 25).
   - (가) CLI를 올리기 전 확인 목록에 "`-p`가 bare 기본으로 바뀌었는가"와 `claude auth status`를 넣는다.
   - (나) Windows Job 경쟁을 고친다: 일시 정지로 띄워 Job에 넣고 재개한다.
   - (다) 호출 관문을 줄인다(K3): 서로 독립인 호출은 동시에 부르고, 실패는 빈자리로 보이며 건너뛰고, 일시적 실패는 한 번 다시 시도한다.
   - (라) 형식 모듈을 `--json-schema`·`--output-schema` 출력으로 바꾼다(인계 4절 3의 "CLI 스키마 출력 전환"). 참여자 명령이 바뀌므로 일상 모드가 열리기 전에는 재관측이 필요하다.
3. **결정 D 다음.** 일상 모드(K1)를 연다. 그 위에서 아래를 차례로 한다.
   - Codex 공식 SDK를 그림자 시험으로 비교
   - `defer` 승인 수신함(P6)
   - 훅으로 모으는 상황판(P9)
   - 한도 % 정책(K4·P10)
   - 결정 A–C는 [불편 기록](../session-pain-points-2026-10-14/README.md) §7 그대로다.
4. **나중에.** sandbox-runtime 그림자 시험(네트워크 허용 목록), 그리고 멈춤 규칙을 갖춘 자리 비움 모드(결정 B).

## 6. 정할 것

### 결정 D — 일상 모드를 열까

| | |
|---|---|
| 무엇을 정하나 | 관측 기록·기기 등록·30일 만료·판 고정을 통과하지 못해도 실제 실행을 허락할지. 모델 없는 점검(구독 로그인, 과금 변수 제거, 판)은 통과해야 한다. 그 결과는 "문맥 미확인"으로 표시하고 독립 정족수에 세지 않는다 |
| 왜 지금 | 주 PC 기록이 2026-11-09에 만료된다. CLI는 이미 뒤처져 있다(Claude Code 2.1.280 → 2.1.299, Codex 0.156.1 → 0.162.1). 올리면 그날부터 실제 실행이 막힌다 |
| 보고 정할 것 | §2의 K1. 인계 2절 18: 확인되지 않은 참여까지 세는 정책도 고를 수 있지만, 그 결과를 독립 정족수 충족으로 표시하지 않는다 |
| 선택지 | (1) **연다 — 엄격 비교는 지금처럼 관측 기록이 있어야 하고, 일상 실행만 연다 (추천)** (2) 그대로 둔다 — 재관측을 정기 작업으로 한다 |
| 안 정하면 | 11월 9일 전에 재관측해야 실제 실행이 계속된다 |

**세션이 정하고 알리는 것**(인계 2절 25): §5의 2번, Codex SDK 시험, sandbox-runtime 그림자 시험. 참여자 명령을 바꾸는 일은 일상 모드가 열리기 전에는 재관측을 거친다.

## 7. 확인 범위와 확인하지 않은 것

- **조사:** 조사 에이전트 셋이 GitHub API, 원본 코드(고정 커밋), 공식 문서를 읽었다. 설치·실행·clone은 하지 않았다.
- **작성 세션이 다시 확인한 것:**
  - 라이선스와 마지막 커밋(GitHub API), CLI 최신 판(npm).
  - 공식 문서의 문장: bare 기본 예고, `defer`, Agent SDK와 법적 고지, 예약 작업·루틴·`/loop`, 샌드박스 범위.
  - 표에 쓴 저장소 주장: codex-plugin-cc의 승인 정책, openai-codex의 기본 승인 모드, CCB의 로그인 파일 복사, PAL `clink`의 기본 옵션, Every Code의 샌드박스 없음, deliberation의 환경 정리, cli-council·agent-council의 흐름, continuous-claude의 기본 옵션, Ralph의 기준과 권한 방식, Codex 훅 이름, Happy의 사용 통계, sandbox-runtime의 기본 권한, runner의 Job 넣는 순서.
- **확인하지 않은 것:**
  - 어떤 도구도 실제로 돌려 보지 않았다.
  - openai-codex SDK와 Codex 0.156.1의 프로토콜 궁합.
  - sandbox-runtime을 WSL2의 AppArmor 아래에서 Codex와 함께 돌리는 것.
  - sbx와 GPU 도구의 WSL2 동작.
  - `get_usage`가 `claude -p`에서 답하는지.
  - Happy가 구독 로그인을 어떻게 쓰는지.
  - bare 기본 전환의 시기와 끄는 방법.
  - 라이선스 판단은 법률 검토가 아니다.
