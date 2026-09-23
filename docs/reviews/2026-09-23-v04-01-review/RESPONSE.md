# V04-01 리뷰 반영 기록 — 2026-09-23

작성: claude (Claude Opus 5.5). 접근 범위: **보조 PC(`aux-pc`)의 로컬 checkout.** `tools/v04-01/check-versions.ps1`이 aux-pc 기록과 같은 세 CLI 버전·경로를 보였다(Claude Code 2.1.280, Codex 0.155.1, agy 1.2.8, 서명 셋 다 `Valid`). CLI는 `--version`만 실행했고 **모델은 부르지 않았다.** 브랜치 `claude/v04-01-review-fixes-20260923`, 리뷰 브랜치 `chatgpt/review-v04-01-20260923`([PR #4](https://github.com/inlight37-design/decision-model_lab/pull/4)) 위에서 작업했다.

[리뷰 원문](README.md)과 재현 자료는 그 시점 기록으로 두고 고치지 않는다. 이 파일이 답이다.

**방법.** 발견마다 이 checkout의 코드, aux-pc 원 출력·help 파일, 공식 문서로 대조했다. 코드 지적은 리뷰어의 [`reproduce_findings.py`](reproduce_findings.py)를 **수정 전 원본 모듈에 대해 실행**해 R01·R03·R04·R08의 반례가 모두 재현되는 것을 먼저 확인했다(관측). 같은 스크립트는 이제 고친 동작을 출력한다. [`reproduction-output.json`](reproduction-output.json)은 수정 전 관측으로 남는다.

## 발견별 처리

| ID | 판단 | 처리 |
|---|---|---|
| R01 | **맞음** — 재현 | `validate_manifest`가 fail-closed로 바뀌었다. `auth_mode`·`funding_mode`는 `unknown` 또는 목록 값만(누락·null·빈 문자열 거절), `configured=true`는 `installed=true`도 요구, `evidence`·`observed_at` 타입 검사, 잘못된 타입의 `adapter_id`·`env_presence`는 예외 대신 오류 줄, presence 기록의 값 필드 거절, `config_presence.opened`는 false만. 표 기반 부정 테스트 추가. aux-pc 두 manifest는 여전히 통과한다 |
| R02 | **맞음** | 부분 반영. Claude `permission_mode`를 manifest 자신의 `tier2_rule`대로 `in_help`로 정정했고, Codex `ignore_user_config`의 증거 문장을 P4가 보인 것으로 좁혔다. manifest에 `configured_means`와 `corrections`를 달았다. RESULTS의 "깨끗한 문맥"·판정 문장과 절차서의 판정 뜻을 정정 표시와 함께 고쳤다. **conformance 필드 분리(`context_conformance`·`permission_conformance`·`eligible_for_run`)와 marker·금지 파일 시험은 V04-03 adapter의 선행 조건으로 넘겼다**([NEXT-SESSION.md](../../../NEXT-SESSION.md) 4절) — 실측 전에 스키마를 늘리지 않는다는 인계 규칙 때문이다 |
| R03 | **맞음** — 재현 | `fresh_environment`와 `fresh-shell.ps1`이 AI 접두사 변수를 레지스트리 값(사용자 > 시스템)으로 다시 만든다. 셸이 덮어쓴 값은 설정 값으로 돌아가고, 셸이 뜬 뒤 설정에 생긴 과금 변수도 보고된다. 둘 다 "새 터미널과 같다"고 쓰지 않도록 설명을 고쳤다 |
| R04 | **맞음** — 재현 | `github_pat_` 가림, 공백이 든 사용자 이름을 통째로 가림, 반쯤 가린 `<user> Doe`를 재검사에서 잡음. `probe.ps1`의 가림도 같은 토큰군과 경로를 다룬다. Python/PowerShell 공통 fixture를 CI에서 돌리는 것은 못 했다 — CI는 Linux이고 PowerShell 5.1이 없다. PowerShell 쪽은 이 PC에서 `probe.ps1`의 실제 `Hide` 함수를 합성 입력으로 실행해 확인했다 |
| R05 | **맞음** | 요약기: 없는 필드는 0이 아니라 null, `missing_fields`, 필드 이름 목록(값 없음), 플러그인 builtin/other, 원본 sha256과 요약기 blob sha1, 이름을 `init_counts`로. tier 2 manifest의 agy `resolved_path`를 재설치 위치로 고치고, `scope`가 tier 1 수집을 말한다는 것을 `corrections`에 적었다. 이미 올린 P4/P4b 요약은 원본이 저장소 밖에 있어 다시 만들지 않았다 — 옛 요약기의 `loaded_into_context` 필드명 그대로다 |
| R06 | **맞음**(한계 지적) | `probe.ps1` 첫머리에 한계(제한 시간 없음, stdout·stderr 합침, runner 아님)와 runner에 필요한 계약을 적었다. **동작은 바꾸지 않았다** — aux-pc 관측과 같은 방식으로 다음 관측을 비교하기 위해서다. mock 실행 파일로 시험하는 runner 계약은 V04-03 작업으로 넘겼다 |
| R07 | **맞음** | `agy models` 출력에 기본값 표시가 없음을 원 출력으로 확인했다. RESULTS의 "기본 모델은 Flash"를 **미확인**으로 정정했다. [headless 문서](https://www.antigravity.google/docs/cli/headless/)에서 "없는 `--model`은 조용히 대체하지 않고 비영 종료·`ERROR`"와 "`--model`을 주면 init에 `model`" 문장을 직접 확인했다(문서, 1.2.8 미시험). `--effort`는 문서에 없다 |
| R08 | **대체로 맞음** | lint가 "검사 총 N개", "tests: N", "N commits"를 잡고 "전체 3개 provider"는 잡지 않는다. 강화된 lint가 [v0.4 HANDOFF](../../architecture/v0.4/HANDOFF.md)의 "12 commits"를 찾았고, 규칙대로 같은 줄의 짧은 SHA를 40자로 바꿨다. `check_encoding.py`는 지정한 파일이 없으면 오류로 보고, `.ts`·`.tsx`·`.sh`를 포함한다. **SHA 예외의 줄 단위는 유지한다** — 아래 |
| R09 | **맞음**(설계 입력) | 새 설계 문서를 쓰지 않고, 리뷰의 전이 표를 V04-03 adapter의 부정 fixture 목록으로 인계에 등록했다 |
| 질문 2 | 문서 확인 | [CLI reference](https://code.claude.com/docs/en/cli-reference)의 `--restricted`(v2.1.248 이상, 평가 harness용 안내)를 직접 읽었다. settings 파일 제외만 말하고 CLAUDE.md는 말하지 않는다. `--safe-mode`는 CLAUDE.md·자동 메모리를 끄고 인증을 유지한다고 적는다 — 다음 관측 후보로 인계 |
| 질문 3 | 문서 확인 | [#711](https://github.com/google-antigravity/antigravity-cli/issues/711)은 2026-09-23 GitHub API로 열려 있고 댓글은 질문자의 재문의 하나다(관측). 약관 판단은 여전히 사용자 결정이다. 인계 ①에 이 정보와 리뷰의 운영 제안(비활성 보존, 서면 답변 뒤 활성화)을 옮겼다 |
| 질문 6 | **맞음** | `check-versions.ps1`이 서명 상태를 출력한다. 이 PC에서 세 CLI 모두 `Valid`(관측) |
| 질문 8 | 동의 | 변경 없음. exec 우선 유지 |

## 반영하지 않은 것과 이유

- **R08의 SHA 예외 범위.** 줄 단위 예외는 [협업 규칙](../../COLLABORATION.md)이 "그 시점의 숫자는 SHA와 같은 줄에"라고 정한 문법 그대로다. 숫자와 SHA의 관계를 판정하려면 새 표기 문법을 정하고 모든 살아 있는 문서를 바꿔야 한다. 지금 그 예외를 쓰는 줄은 역사 기록뿐이라 이득이 작다. 검사 docstring에 범위를 적었다. 오용 사례가 나오면 다시 본다.
- **R02·R05의 manifest 스키마 분리.** tier 1 baseline과 tier 2 관측을 기계적으로 나누는 것, conformance 필드를 두는 것은 옳다. 다만 V04-03 adapter가 실제로 읽을 필드가 정해질 때 한 번에 `runtime-inventory/2`로 바꾸는 편이 낫다고 판단했다. 그때까지 `configured_means`와 `corrections`가 뜻을 고정한다.
- **R06의 probe 실행 방식.** 위 표.

## 리뷰 밖에서 새로 찾은 것

- `--fresh-env`의 환경은 대소문자를 가리는 dict라서, 설정에 `Anthropic_Api_Key`처럼 적힌 변수를 "없음"으로 기록할 수 있었다. presence를 대문자로 비교하게 고쳤다.
- pre-commit hook은 파일 이름을 공백에서 쪼갰고, 한글 이름은 escape된 채 넘겼으며, 이름이 바뀐 파일(`R`)을 검사하지 않았다. 검사기가 없는 파일을 건너뛰었으므로 이 셋은 조용히 통과했다. `-z`와 `ACMR`로 고쳤다.

## 확인하지 못한 것

- PowerShell 변경은 이 PC에서 세 스크립트 파싱, `Hide` 합성 입력, `fresh-shell.ps1` + `check-versions.ps1` 실행으로만 확인했다. `probe.ps1`로 모델을 부르지 않았다.
- `fresh-shell.ps1`의 "설정 값이 셸 값을 이긴다"는 사용자 레지스트리를 바꾸지 않고는 시험할 수 없어, 같은 규칙의 Python 합성 테스트로만 확인했다.
- agy 1.2.8의 없는 `--model`·`--effort` 처리, `--safe-mode`, 권한 거절·blind 입력 conformance — 모두 모델 호출이 필요해 사용자 승인 뒤로 남겼다.
- 스키마 검사는 이 PC에 `jsonschema`가 없어 로컬에서 skip됐다. CI 결과로 확인한다.
