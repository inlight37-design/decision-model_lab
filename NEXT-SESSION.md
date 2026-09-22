# 다음 세션 인계 — decision-model_lab

최종 갱신 **2026-09-23 (Asia/Seoul)**. 이 파일에서 시작한다. 모든 과거 문서를 prompt에 넣지 않는다.

## 1. 현재 상태와 읽을 곳

이번 검토는 `review/mcp-ui-runtime-20260923` 브랜치에서 진행했다. **main 자동 병합은 하지 않았다.** 현재 체크아웃의 branch/head와 PR 상태부터 확인한다. 시작 main은 `c109840890bd72cbe5135f14c4d90c54c9039f0f`였다.

**이 저장소는 여전히 연구·설계 및 오프라인 실험이다. 실제 provider 연결 0건.** 새 경계 코드가 실제 실행 제어기·MCP 서버라는 뜻이 아니다.

| 읽을 곳 | 담긴 것 |
|---|---|
| [이번 종합 검토](docs/reviews/2026-09-23-mcp-ui-runtime/README.md) | MCP 구성, Orca/Paseo/herdr 외 5사례, 신뢰 경계, UI 평가와 후속 순서 |
| [출처 19개와 한계](docs/reviews/2026-09-23-mcp-ui-runtime/SOURCES.md) | 공식 문서/README의 정확한 확인 범위. 기존 E/F 원장과 별개 |
| [검증 기록](docs/reviews/2026-09-23-mcp-ui-runtime/VALIDATION.md) | GitHub CI, 로컬 경계 테스트, 브라우저 smoke, 알려진 대비 실패 |
| [미발행 UI 비교 시안](docs/reviews/2026-09-23-mcp-ui-runtime/preview.html) | 결정/대조표 순서, 두 테마, 4가지 합성 상태. 실행 기능 없음 |
| [기존 전체 인수인계 — 원문 보존](NEXT-SESSION.2026-09-23-before-review.md) | 이전 사용자 결정, 디자인 규칙, 환경 이력과 열린 질문. 일부 과장/숫자는 아래 정정 우선 |
| [v0.4 HANDOFF](docs/architecture/v0.4/HANDOFF.md) | 전체 아키텍처 및 V04-01/V04-03의 원래 맥락 |

코드 commit `85e3cb1f3641c52278dd1d391fe845024b23b7df`에서 Python 3.12/3.13 CI success, 3.13 로그 **112 tests OK / skip 없음**을 확인했다. 추가 37개(경계 31 + 대비 6)다. 기존 원장은 E01–E31/F01–F29로 **60개**이며 이번 검토가 원장을 증설한 것은 아니다. 숫자는 해당 commit 기준이고 최신 결과는 CI로 확인한다.

## 2. 유지할 사용자 결정

앱의 셸·Python 제어 코어·근거 저장소는 우리 것이며 한 외부 앱을 통째로 선택하는 프로젝트가 아니다. 여러 앱에서 패턴을 추출한다. 상급 모델 독립 추론·제한 교차검토·상급 합성을 경제성 경로와 나란히 유지한다. Jev는 선택 부품이다.

공식 native 구독 CLI를 우선하고 API/추가 크레딧 전환은 명시 opt-in만 허용한다. `agy`는 Gemini CLI가 아니다. 논의자는 실제 읽기 전용, 구현자는 한 writer를 기본으로 한다. 프롬프트의 금지 문장·worktree·UI 숨김을 OS 권한 보장으로 취급하지 않는다.

모델 간 합의는 검증이 아니다. blind 초안, 반대 근거, 미합의, 호출/round 예산을 보존한다. 추가 planner/extractor/retry도 예산에 포함한다. 사용량 표시를 위해 모델을 추가 호출하지 않는다. 토큰·추정 비용·계정 한도를 합산하지 않는다.

## 3. 이번에 정정한 것

- **checker는 판정 엔진이 아니다.** `check_frontier_protocol.validate()`는 입력된 합성 완료 기록의 일관성을 검사한다. disposition 계산, 실제 검사 실행, 원문 뒷받침 판정은 수행하지 않는다. design/project 문서의 더 강한 표현보다 코드의 실제 범위를 따른다.
- **원문 회수 ≠ 의미 검증.** URL/locator를 찾았다고 supported가 되지 않는다. 모델이 임의로 passed를 기록하도록 `record_check`를 열지 말고 trusted runner의 내부 기록 권한으로 둔다.
- **herdr의 재부팅 복구 ≠ 원 프로세스 생존.** detach, 배치 복원, native resume를 분리한다. 과거 session resume를 fresh blind 문맥으로 인정하지 않는다.
- **Codex 한도 조회는 공식 문서 경로가 확인됐다.** App Server의 `account/rateLimits/read`, `account/rateLimits/updated`, `rateLimitsByLimitId`가 있다. 사용자 기기 지원은 미검증이다. Antigravity 경로도 이번에는 확인하지 않았다.
- **MCP 지연 로딩/CLI 효율은 모든 클라이언트의 보편적 보장이 아니다.** 필요한 도구만 노출하고 실제 클라이언트에서 문맥·지연을 측정한다.
- **원본 색 대비는 전부 통과가 아니다.** 일반 글자 66쌍 중 5쌍이 4.5:1 미만이다. 원본 design은 발행본 동기화 규칙 때문에 보존하고 별도 검사·수정 후보를 만들었다.

Q1은 기존 ACP 우선+exec fallback을 유지하되 provider 고유 기능의 native 보조 경로를 별도로 둘 것을 제안했다. **공통 계약과 동일 wire protocol 강제는 다르다.** Q4/Q8 첫 화면 우승안은 미확정이며 시안 두 배치는 비교 준비물이다.

## 4. 실제로 추가한 것

`tools/review_boundary.py`는 이벤트 순서·세대, 중복, 취소와 UNKNOWN, 예산 슬롯, 봉인 allowlist, quota stale/unknown/observed 처리를 위한 **순수 함수 실험**이다. 입력은 신뢰된 adapter에서 와야 하며 서버 인가·OS 제어·persistent journal은 없다.

`tools/audit_design_contrast.py`는 대비 수식 감사다. `--strict`는 현재 원본에 exit 1을 반환하는 것이 맞다. `tools/smoke_review_preview.py`는 선택 Playwright 개발 도구이고 주 CI에는 아직 포함하지 않았다. 48조합 smoke는 전체 접근성 인증이나 사용자 실험이 아니다.

기존 `design/`과 Claude 발행 artifact를 바꾸지 않았다. 원본 디자인 수정 시 두 곳을 함께 갱신한다. 새 시안은 검토 폴더의 독립 미발행 파일이다.

## 5. 다음 실제 실행 순서

**V04-01을 실제 운용할 PC에서 먼저 한다.** 이전 인계의 Windows 경로·설치 버전·자격증명·보조 PC 설명은 그 세션의 이력이다. 이번 웹 세션은 사용자 C:\\ai에 접근하지 않았고 CLI 설치·로그인을 확인하지 않았다.

1. 설치 버전/help, native 로그인, 상급 모델/effort, 구조화 출력, ACP/native transport, resume/cancel, 계정 한도 경로를 비밀 값 없이 기록한다.
2. fresh context와 구독 인증을 동시에 만족하는지, 읽기 전용 제한이 실행 전에 유효한지 확인한다. 정책 변화·동시 기기 제한·유료 fallback 차단도 확인한다. 문서만으로 configured=true 금지.
3. V04-03: 서로 다른 두 native 경로의 read-only 독립 응답. 실패/거절/timeout/UNKNOWN을 성공으로 포장하지 않는다.
4. 승인된 test ID의 trusted runner와 실행 영수증을 먼저 연결한 뒤 필요한 만큼 MCP로 노출한다. 그 후 UI 데이터 경계·재연결·복구를 시험한다.
5. 단독/독립 합성 대조군과 Q8 UI 탐색을 거친 뒤 세 모델·제한 교차검토로 확장한다.

## 6. 검사와 인코딩

```bash
git config core.hooksPath .githooks
python -m pip install -r requirements-design.txt
python -m unittest discover -s tests -v
python tools/validate_sources.py
python tools/validate_design_tokens.py
python tools/check_encoding.py
python tools/audit_design_contrast.py
```

`jsonschema` 미설치로 skip한 것은 통과가 아니다. **PowerShell Get-Content/Set-Content로 BOM 없는 UTF-8 문서를 일괄 치환하지 않는다.** 명시적 UTF-8 편집을 사용한다. pre-commit hook/검사기/CI도 그럴듯하게 깨진 한글까지 모두 잡지는 못한다.

작업 단위마다 commit하고 검증 범위와 다음 작업을 갱신한다. 기존 handoff는 Git blob `b4c0bca6a9f3d8d4093c74db0cb27e3e4733815e` 그대로 보존했다.
