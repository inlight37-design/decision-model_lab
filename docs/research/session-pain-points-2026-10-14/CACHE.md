# 캐시 유지(keepalive) 도구 조사 (2026-10-14)

사용자 요청(2026-10-14): 캐시를 계속 살려 두는 도구들이 있던데 찾아봐도 된다. [불편 기록과 해법](README.md)의 한 부분이다.

**결론: 이 PC에는 설치하지 않기를 권한다.** 구독 사용량 안에서 Claude Code의 메인 대화는 이미 1시간 캐시를 쓰고, 이런 도구를 만든 사람들도 구독에서는 쓰지 말라고 적었다. 공식 문서도 쉬는 세션에 새 차례가 열릴 때마다 대화 전체를 보낸다고 적었다. 사용량을 아끼려면 세션을 작게 쓰는 쪽이 낫다(§5).

- 작성: claude 세션, 주 PC `DESKTOP-T0UDE01`의 Windows 쪽. 도구를 설치·실행하지 않았고 모델 호출도 하지 않았다. 아래는 공식 문서와 각 도구의 설명을 읽은 것이다(출처 등급 "문서", 2026-10-14). 실제 동작은 확인하지 않았다.

## 1. 캐시가 무엇인가

모델 회사는 요청의 앞부분(시스템 안내·도구 목록·지난 대화)을 잠시 저장해 둔다. 다음 요청이 같은 앞부분으로 시작하면 그 부분을 싸게 읽는다. 정해진 시간 동안 쓰지 않으면 저장이 사라지고, 다음 요청은 앞부분 전체를 다시 저장한다. 다시 저장하는 쪽이 비싸고, 대화가 길수록 다시 저장할 양이 크다.

캐시 유지 도구는 쉬는 동안 아주 작은 요청을 주기적으로 보내 저장이 사라지지 않게 한다.

## 2. 사실

| 무엇 | 내용 | 출처 |
|---|---|---|
| Anthropic 캐시 수명 | 기본 5분이고, 캐시를 읽을 때마다 추가 비용 없이 다시 늘어난다. 1시간을 고를 수 있다(추가 비용) | [Anthropic prompt caching](https://platform.claude.com/docs/en/build-with-claude/prompt-caching) 첫 절·"1-hour cache duration" |
| 가격 배수 | 5분 저장은 입력 가격의 1.25배, 1시간 저장은 2배, 읽기는 0.1배다. Opus 5.5·Sonnet 5.5의 읽기는 0.05배, Fable 5.1은 0.025배다 | 같은 문서 "Pricing" |
| 캐시가 깨지는 경우 | 도구 정의가 바뀌면 전부, 시스템 안내·추론 설정이 바뀌면 그 뒤 전부가 무효가 된다 | 같은 문서 "What invalidates the cache" |
| Claude Code의 캐시 시간 | 구독 사용량 안에서는 메인 대화(대화형 차례, `-p` 실행, Agent SDK 차례)가 1시간이고, 그 밖(서브에이전트·워크플로·팀원·압축·세션 제목 등)은 5분이다. 한도를 넘어 추가 사용량으로 넘어가면 메인 대화도 5분으로 내려간다. API 키·클라우드 사업자는 기본 5분이다. `promptCacheTtl`·`CLAUDE_CODE_PROMPT_CACHE_TTL`(메인)과 `subagentPromptCacheTtl`(그 밖)로 직접 정할 수 있다(2.1.242). 어느 쪽이 쓰였는지는 `claude -p "hello" --output-format json` 결과의 `usage.cache_creation`에서 `ephemeral_1h_input_tokens`로 본다 — 이것도 작은 모델 호출이다 | [Claude Code 프롬프트 캐시](https://code.claude.com/docs/en/prompt-caching) "Which TTL each request gets"·"Choose the TTL yourself" |
| 쉬는 세션이 사용량을 쓰는 경우 | 하루 종일 열어 둔 세션에서는 한 줄 질문도 대화 전체만큼 사용량을 쓴다(캐시 읽기 가격으로). 쉬는 세션에 예약 작업이 돌거나 다른 세션의 글이 오면 그때마다 대화 전체를 보낸다. Pro/Max에서 오래 쉰 큰 세션을 다시 열면 요약으로 시작하자고 제안한다 | [Claude Code 비용](https://code.claude.com/docs/en/costs) "Long context"·"Cache misses"·"Scheduled tasks"·"Cross-session messages" |
| 쉬기 전 압축 | 터미널 세션에서 1시간 캐시로 쉬는 긴 대화는 캐시가 끝나기 직전에 압축될 수 있다. 끄는 설정 `idleCompaction`은 2.1.290부터다. `/usage`가 캐시 적중·놓침과 지금 따뜻한지를 보여 준다(2.1.251) | [Claude Code 프롬프트 캐시](https://code.claude.com/docs/en/prompt-caching) |
| 이 PC에서 본 것 | 이 데스크톱 앱 세션이 받은 예약 도구 설명에 "이 세션의 요청은 1시간 캐시를 쓰고, 사용량 초과로 넘어가면 5분으로 떨어지며, 캐시를 데우려고 깨우기를 더 잡는 것은 낭비"라는 취지의 안내가 있다. 위 공식 문서와 맞는다 | 2026-10-14 관측. 공식 문서가 아니라 앱이 세션에 주는 도구 설명이다 |
| OpenAI(Codex 쪽) | GPT-5.6 이후 모델은 마지막으로 쓰거나 저장한 뒤 30분 동안 다시 쓸 수 있다(설정값은 `30m` 하나이고 기본값). 저장은 1.25배, 읽기는 대부분 0.1배다 | [OpenAI prompt caching](https://developers.openai.com/api/docs/guides/prompt-caching) "Cache lifetime"·"How caching works" |
| 손익 연구 | Anthropic 5분 캐시에서는 약 4분 간격이 가장 싸다. 핑을 이어 가는 비용이 한 번 다시 저장하는 비용보다 싼 쉬는 시간의 한계는 Anthropic 약 46분, OpenAI·DeepSeek 약 36분이다 | Khailo, [arXiv:2607.19214](https://arxiv.org/abs/2607.19214v2)(2026-07) 초록. 본문은 읽지 않았다 |

## 3. 찾은 도구

| 도구 | 방식 | 간격과 멈춤 | 구독에 대해 스스로 한 말 | 읽은 곳 |
|---|---|---|---|---|
| [claude-code-cache-keepalive](https://github.com/yujiachen-y/claude-code-cache-keepalive)(MIT) | Stop 훅이 기다렸다가 `decision: "block"`을 내 새 차례를 만든다. Claude가 짧게 답하면서 캐시를 읽는다 | 기본 240초, 한 차례당 최대 7번. Esc·사용자 입력·세션 끝에서 멈춘다 | "API 키·토큰 과금에서만 유용", Pro/Max에서는 5시간 한도를 써서 "오히려 나쁘니 끄라". 5분 캐시를 전제로 한다 | README |
| [cachebeat](https://github.com/ARahim3/cachebeat) | 백그라운드 Stop 훅. 정말로 쉰 지 N분 뒤에 한 번만 핑 | 기본 50분(5–55분), 8시간(1–24시간) 뒤 스스로 멈춤 | 1시간 캐시를 전제로 한다. 5분 캐시라면 "어떤 핑도 도움이 안 된다"고 적었다 | 스킬 목록 페이지만. 저장소는 읽지 않음 |
| cache-money([florianbuetow/claude-code](https://github.com/florianbuetow/claude-code)) | 캐시 시간에 맞춘 가벼운 핑을 예약한다 | 확인 못 함 | "1시간은 Max 요금제의 Claude Code" | 스킬 목록 페이지만. SKILL.md는 읽지 않음 |
| Prompt Cache Control([davila7/claude-code-templates](https://github.com/davila7/claude-code-templates)의 mod) | **핑이 아니라 계량기다.** 요청마다 캐시 읽기·저장·미저장 양과 만료까지 남은 시간을 보이고, 큰 문맥의 캐시가 만료되면 `/compact`나 `/clear`를 권한다 | 핑 없음 | 구독 사용량 안에서는 1시간, 크레딧·API 키는 5분으로 본다. 응답에 실린 한도 창의 종류로 구독 여부를 추정한다 | [mod 소개 페이지](https://www.aitmpl.com/component/mods/observability/prompt-cache-control) |

aider의 `--cache-keepalive-pings`(API용, 300초)와, 같은 방식을 제안했다가 "계획 없음"으로 닫힌 openclaw 이슈는 [정리 글](https://agentpatterns.ai/context-engineering/prompt-cache-keepalive-agent-pauses/)에서 이름만 봤다.

## 4. 이 사용자에게 맞지 않는 이유

1. **구독이라 돈이 아니라 사용량 한도를 쓴다.** 핑마다 캐시 읽기와 짧은 답이 한도에서 빠진다. 구독 한도에서 캐시 읽기·저장이 각각 얼마로 계산되는지는 공개돼 있지 않다 — [역할판 검토](../../reviews/2026-09-26-role-board-review/README.md)의 RB-08과 [mixdog 검토](../agent-tools-2026-10-12/README.md)가 이미 같은 한계를 적었다. 그래서 "핑이 이득"이라는 API 가격 계산을 구독에 그대로 댈 수 없다.
2. **이미 1시간이다.** 메인 대화는 1시간 안에 돌아오면 핑 없이도 캐시가 산다. 핑이 쓸모 있는 경우는 1시간보다 오래 쉬었다가 같은 큰 세션으로 돌아올 때뿐이다. 서브에이전트·팀원은 5분이지만 짧게 끝나는 일이라 핑할 대상이 아니다.
3. **아껴 쓰는 한도를 밤사이에도 깎는다.** 사용자는 주간 한도를 99%까지 맞춰 쓰는데(다른 프로젝트의 P10), 핑은 그 계산을 흐린다.
4. **헛수고가 될 수 있다.** 핑 차례가 대화에 쌓이고, 쉬는 동안 훅·MCP·설정이 바뀌면 데워 둔 앞부분을 다음 요청이 쓰지 못한다.

## 5. 대신 할 것

- **오래 쉴 세션은 상태를 적고 닫는다.** 돌아오면 작은 새 세션으로 시작한다. 다시 저장할 양이 작아진다. 이 앱의 방식(참여자는 매번 새 세션, 이어지는 내용은 고정 입력)과 같고, 다른 프로젝트의 세션 상태 파일 방식과도 맞는다.
- 큰 세션을 오래 둘 수밖에 없으면 쉬기 전에 압축한다. 터미널 세션은 쉬기 전 압축이 이미 있고, 오래 쉰 큰 세션은 요약으로 다시 열 수 있다(§2).
- 쉬는 동안 훅·MCP·설정을 바꾸지 않는다.
- 캐시가 실제로 얼마나 다시 저장되는지 궁금하면 핑이 아니라 계량기를 쓴다. 위의 mod 방식이나, 대화 기록의 사용량 칸(캐시 읽기·저장 토큰)을 세는 방식은 모델 호출이 들지 않는다. [상황판](README.md) §3의 "세션과 문맥" 칸에 함께 넣을 수 있다.
- 이 앱의 참여자 호출은 매번 새 세션이라 핑이 소용없다. 대신 요청의 앞부분 순서를 고정한다(역할판 검토 RB-07).

## 6. 다시 볼 조건

- API 키(토큰 과금)로 Claude Code를 쓰게 될 때. 그때는 5분 캐시이고, 쉬는 시간이 46분 안쪽이면 핑이 돈을 아낄 수 있다.
- Anthropic이 구독 한도에서 캐시 읽기·저장의 무게를 공개할 때.
- 구독 세션의 캐시 시간이 5분으로 바뀔 때(사용량 초과로 넘어간 때 포함).
