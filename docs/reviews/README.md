# reviews — 외부 검토 기록

저장소 밖에서 수행된 검토의 원문을 보존한다. 요약으로 대체하지 않는다.

현재 실행 경로의 후속은 [2026-09-25 감사·PR #47](2026-09-25-runtime-audit-finish/README.md)이다. [이전 #46 기록](2026-09-25-runtime-review/README.md)의 저장된 수명주기 수정 위에 자료 복원 검사를 추가했고, 사용량 파서의 로컬 수정과 원격 미반영을 구분했다. 과거 기록의 완료 상태를 현재 head의 CI로 읽지 않는다.


| 파일 | 무엇 |
|---|---|
| [`2026-09-22-external-review.md`](2026-09-22-external-review.md) | 첫 외부 정밀 검토. 코드·문서·근거 원장 전체를 읽고 검사를 재실행한 기록 |
| [`2026-09-23-mcp-ui-runtime/`](2026-09-23-mcp-ui-runtime/README.md) | MCP 구성·기존 앱 8사례·Ledger UI 검토, 오프라인 경계 실험(`tools/review_boundary.py`), 대비 감사. [PR #3](https://github.com/inlight37-design/decision-model_lab/pull/3) |
| [`2026-09-23-review-request/`](2026-09-23-review-request/README.md) | V04-01 검토 요청서. 질문·읽는 순서·결과 형식은 원문을 보존하고 결과는 아래 리뷰로 연결한다 |
| [`2026-09-23-v04-01-review/`](2026-09-23-v04-01-review/README.md) | GitHub 기록·코드·공식 문서 대조. 실행 준비와 blind/권한 통과의 구분, manifest·환경·가림 가드의 합성 반례와 재현 자료. [PR #4](https://github.com/inlight37-design/decision-model_lab/pull/4). 반영 결과는 같은 폴더의 [`RESPONSE.md`](2026-09-23-v04-01-review/RESPONSE.md) |
| [`2026-09-23-wsl2-boundary/`](2026-09-23-wsl2-boundary/README.md) | WSL2 채택과 실행 경계. runner 종료 확인·정리 상한, 정족수, 출력 파서의 재현과 WSL2가 해결하는 것·하지 않는 것. 원문은 [`REVIEW.md`](2026-09-23-wsl2-boundary/REVIEW.md), 반영 결과는 [`RESPONSE.md`](2026-09-23-wsl2-boundary/RESPONSE.md) |
| [`2026-09-23-wsl2-migration-request/`](2026-09-23-wsl2-migration-request/README.md) | 경계 리뷰 반영, WSL2 이전, bubblewrap 격리에 대한 검토 요청서. 한 일, 잘 안 된 것, 아직 모르는 것, 다음 계획과 검토 질문. 결과는 `2026-09-23-wsl2-migration-review/`로 받는다 |
| [`2026-09-23-wsl2-migration-review/`](2026-09-23-wsl2-migration-review/README.md) | 위 요청에 대한 ChatGPT 리뷰([PR #6](https://github.com/inlight37-design/decision-model_lab/pull/6)). 입력 전달 실패, 토큰의 argv 경로, namespace 보장 부여, 마운트 충돌, 빈 PATH, 파서 경계, 잔류 입출력(WM-01–WM-07)과 고정된 재현 자료. 반영 결과는 같은 폴더의 [`RESPONSE.md`](2026-09-23-wsl2-migration-review/RESPONSE.md) |
| [`2026-09-23-a1-handoff-request/`](2026-09-23-a1-handoff-request/README.md) | WSL2 리뷰 반영, A1 모의 앱, 새 인계의 한계 표(K 번호)와 다음 계획에 대한 검토 요청서. 결과는 아래 리뷰와 재개 검증·정정으로 연결한다 |
| [`2026-09-23-a1-handoff-review/`](2026-09-23-a1-handoff-review/README.md) | [PR #7](https://github.com/inlight37-design/decision-model_lab/pull/7). A1 봉인·수용·복구·마운트, K 표·계획·수동 원본 앱 참여와 인계 비교. 중단 전 리뷰·재현 코드·관측을 보존했으며, [재개 검증·WM-07 정정](2026-09-23-a1-handoff-review/VERIFICATION-20260923.md)을 함께 읽는다. 제품 실행 코드는 이 리뷰에서 수정하지 않음. 반영 결과는 같은 폴더의 [`RESPONSE.md`](2026-09-23-a1-handoff-review/RESPONSE.md) |
| [`2026-09-23-stage2-request/`](2026-09-23-stage2-request/README.md) | 2단계(승인된 모델 호출 다섯 번)의 판정, 관측 도구 수정, 그 과정의 실패·실수·시행착오(S01–S21)에 대한 검토 요청서. 결과는 `2026-09-23-stage2-review/`(또는 리뷰한 날짜)로 받는다 |
| [`2026-09-24-review-request/`](2026-09-24-review-request/README.md) | 위 요청서를 이어받는 검토 요청서. 지금까지의 흐름(연표), 2단계 뒤의 PR #8–#12, K46 방어, 새 실패·시행착오(S22–S33)와 S01–S21의 현재 상태. PC에만 있던 관측 요약을 가려서 함께 옮겼다. 결과는 `<YYYY-MM-DD>-review/`로 받는다 |
| [`2026-09-24-review/`](2026-09-24-review/README.md) | 위 요청과 17번 질문에 대한 ChatGPT 검토([PR #14](https://github.com/inlight37-design/decision-model_lab/pull/14)). K46·P3 판정식, 실행 허가의 합성 반례, 구성별 관측 판정, S01–S33·PR 충돌·다음 순서. 원본 판정과 제품 코드는 유지했고 재현 코드·결과·소스 해시를 함께 남겼다. 반영 결과는 같은 폴더의 [`RESPONSE.md`](2026-09-24-review/RESPONSE.md) |
| [`2026-09-24-a1-integrity/`](2026-09-24-a1-integrity/README.md) | 전체 검토와 직접 수정([PR #18](https://github.com/inlight37-design/decision-model_lab/pull/18)). 원장 거래 실패/HTTP 음성 회귀, 공개 뒤 합성 없는 보고, 화면 배치, 실제 소켓과 오프라인 DOM 검증 범위, 다음 작업 인계 |
| [`2026-09-24-lean-lifecycle/`](2026-09-24-lean-lifecycle/README.md) | PR #18 위의 간결성 검토와 직접 수정([PR #20](https://github.com/inlight37-design/decision-model_lab/pull/20), 자동 닫힌 PR #19 대체). 지속 취소·스레드/연결 수명·필요한 사건만 읽는 조회, 합성 성능 측정과 남은 경계 |
| [`2026-09-24-structure-audit/`](2026-09-24-structure-audit/README.md) | claude의 구조 전수검사(main `99d9bb4`): 덧대기인가 구조적 해결인가. core·app·tools·이력의 판정, 직접 재현한 틈 G1–G9, 적은 코드 순서의 해법. 위 간결성 검토와 독립으로 썼고(blind), 둘의 비교는 [`COMPARISON.md`](2026-09-24-structure-audit/COMPARISON.md)([PR #21](https://github.com/inlight37-design/decision-model_lab/pull/21)) |
| [`2026-09-24-offline-progression/`](2026-09-24-offline-progression/README.md) | codex의 새 main 검토와 순서 1–4 구현([PR #22](https://github.com/inlight37-design/decision-model_lab/pull/22)–[#25](https://github.com/inlight37-design/decision-model_lab/pull/25)). 주인 모듈별 반영, 검토 중 고친 결함, 검증 범위와 브라우저 미검증 |
| [`2026-09-24-merge-22-25/`](2026-09-24-merge-22-25/README.md) | claude의 PR #22–#25 병합 검증([PR #26](https://github.com/inlight37-design/decision-model_lab/pull/26)). 정확한 head의 CI, 쌓인 브랜치의 인계 충돌과 통합 병합, 병합 트리 동일성, 코드 검토와 낮은 우선순위 발견 |
| [`2026-09-24-post-merge-verification/`](2026-09-24-post-merge-verification/README.md) | codex의 병합 후 재검토([PR #28](https://github.com/inlight37-design/decision-model_lab/pull/28)). 실제 브라우저·K46 관측, 진단 출력 수정과 실행 계약 제안. GitHub 원문 대조는 같은 폴더의 [`GITHUB.md`](2026-09-24-post-merge-verification/GITHUB.md) |
| [`2026-09-24-execution-contract/`](2026-09-24-execution-contract/README.md) | claude의 순서 5 실행 계약(G4·G6) 구현([PR #30](https://github.com/inlight37-design/decision-model_lab/pull/30)). 계획 한 번, 계획에서 계산한 판, 옛 판의 정확한 대응, 시도에 저장한 실행 종류 |
| [`2026-09-24-cli-readiness/`](2026-09-24-cli-readiness/README.md) | codex의 순서 5 재검토·회귀 수정, main 보호 적용, 서버 연결 전 조회, Claude 재관측 준비 및 Codex C3 무모델 진단([PR #31](https://github.com/inlight37-design/decision-model_lab/pull/31)). 실행 허가를 임의로 승격하지 않았다. 앞 기록의 “main 보호 없음”은 이 작업으로 해소됐다. 작성 중 검증 상태는 보존하고 [완료 검증](2026-09-24-cli-readiness/FINAL-VALIDATION.md)으로 대체한다 |
| [`2026-09-24-pr31-safety-review/`](2026-09-24-pr31-safety-review/README.md) | 위 PR #31에 대한 ChatGPT의 독립 재검토([PR #32](https://github.com/inlight37-design/decision-model_lab/pull/32)). 계획 뒤 허가 변경·전송 증거 누락의 회귀 시험과 양성 대조, 문맥 독립성의 다음 확인. 제품 코드는 바꾸지 않았다 |
| [`2026-09-24-merge-31-32/`](2026-09-24-merge-31-32/README.md) | claude의 PR #31·#32 병합 검증. 정확한 head의 CI와 job 로그, 판 직접 계산, 로컬 전체 검사, 변이 시험, 병합을 막지 않는 발견 |
| [`2026-09-24-live-cli-pilot/`](2026-09-24-live-cli-pilot/README.md) | codex가 사용자 PC의 PR #34 head에서 첫 실제 Codex 서버 응답을 수용·공개한 기록. 문맥 미확인·제공 모델 미보고·상한 소진, 원문 API 저장, 공개 답의 독립성 표시 정정 |
| [`2026-09-24-live-pilot-replication/`](2026-09-24-live-pilot-replication/README.md) | claude가 같은 PC에서 PR #35 head로 두 번째 실제 Codex 응답을 받은 기록. 예산 소진 뒤 시작 전 거절, 실제 답의 모의 합성, PR #34·#35 검토(CI·변이 시험)와 병합, 상한 고정·회계·회귀 시험의 발견 |
| [`2026-09-24-cli-unblock/`](2026-09-24-cli-unblock/README.md) | ChatGPT 웹 세션의 PR #38. 상한 원장 고정, 시작 전 거절 회계, provider별 입력·설정과 병렬 연결, Codex 계정 메타데이터 조회 도구, Windows CI 추가와 그 실패를 고치는 평문 패치. 모델 호출 없음 |
| [`2026-09-24-windows-live-completion/`](2026-09-24-windows-live-completion/README.md) | codex의 PR #39. #38의 Windows 패치 적용, 계정 한도 화면, Claude stream-json 권한 관측, 실제 Codex·Claude 병렬 응답의 수용·공개 |
| [`2026-09-24-merge-39/`](2026-09-24-merge-39/README.md) | claude의 #38·#39 검토·병합. 정확한 head의 CI, Windows·WSL 전체 시험, 변이 시험의 두 빈틈과 검증 도구의 CP1252 오류 수정, 다음 작업(A–F)을 정한 근거 |
| [`2026-09-24-account-limits/`](2026-09-24-account-limits/README.md) | claude의 다음 작업 A·F. Claude stream의 `rate_limit_event`로 계정 한도 표시(봉인·실제 실행만), Codex `model/list`로 가용 모델 확인(실제 조회, 추론 없음), 계획에서 바꾼 두 곳 |
| [`2026-09-24-source-snapshot/`](2026-09-24-source-snapshot/README.md) | claude의 다음 작업 B. 실행별 공통 자료를 원장에 고정·질문 digest에 묶고 시도마다 해시 확인, 실제 Codex·Claude 실행에서 두 답의 자료 인용과 A·F의 실제 화면 확인 |
| [`2026-09-24-model-synthesis/`](2026-09-24-model-synthesis/README.md) | claude의 다음 작업 C. 공개 뒤 실행마다 켜는 실제 합성 1회, 원문 글자 그대로의 인용 대조와 원문에 없는 추가 주장 표시, 같은 상한 안의 예약, 실제 Claude 합성 확인 |
| [`2026-09-24-codex-apps-off/`](2026-09-24-codex-apps-off/README.md) | claude의 다음 작업 E 첫 단계. Codex 참여자에게 열려 있던 계정 연결 앱(도구 198개, 쓰기 포함)을 끄고, 바뀐 판으로 K46을 다시 관측했다. 새 manifest와 아직 열린 문맥 통로 |

최신 추가: [`2026-09-25-runtime-audit-finish/`](2026-09-25-runtime-audit-finish/README.md) — #46의 합성 수명주기를 재검토하고 자료 복원 오류를 수정했다. 사용량 파서는 로컬 수정만 검증되어 원격 반영이 남았다. 앞선 [`Codex 연결 앱 끄기`](2026-09-24-codex-apps-off/README.md)의 관측은 보존하며 문맥 독립성(C3)은 아직 미확인이다.

## Windows·실제 병렬 실행 후속

[2026-09-24-windows-live-completion](2026-09-24-windows-live-completion/README.md)([PR #39](https://github.com/inlight37-design/decision-model_lab/pull/39))에서 [PR #38 기록](2026-09-24-cli-unblock/README.md)의 Windows 평문 패치를 적용하고, 실제 계정 한도·Claude의 현재 stream-json/Read 권한 거절·Codex/Claude 병렬 수용과 브라우저를 관측했다. 이전 기록의 패치 미적용·계정/병렬 응답 미관측은 당시 상태다. 현재 문맥 독립성은 여전히 미확인이다.

## 읽는 순서

현재 후속은 [실행 경로 감사·미반영 사항](2026-09-25-runtime-audit-finish/README.md)과 [이전 실행 경로 리뷰](2026-09-25-runtime-review/README.md)다. 그 앞은 [다음 작업 E의 첫 단계](2026-09-24-codex-apps-off/README.md), [D 결과](../experiments/2026-09-24-comparison-pilot/RESULTS.md), [C](2026-09-24-model-synthesis/README.md), [B](2026-09-24-source-snapshot/README.md), [A·F](2026-09-24-account-limits/README.md)이고, 그 앞은 그 작업들을 정한 [#38·#39 검토·병합](2026-09-24-merge-39/README.md)이다. 그 앞이 위 Windows·실제 병렬 실행 기록과 [#38 기록](2026-09-24-cli-unblock/README.md)이며, 그 이전은 [두 번째 실제 CLI 응답과 #34·#35 병합](2026-09-24-live-pilot-replication/README.md)이다. 같은 경로가 다른 세션·다른 질문에서 재현됐고, 호출 상한이 원장에 고정되지 않는 점과 시작 전 거절이 실행별 회계에 섞이는 점을 찾았다. 그 앞 [첫 실제 CLI 서버 응답](2026-09-24-live-cli-pilot/README.md)은 PR #34의 문맥 미확인 opt-in에서 단일 Codex 응답을 수용·공개했으며 strict 허가는 여전히 없다. 그 앞 [PR #31의 순서 5 재검토·회귀 수정](2026-09-24-cli-readiness/README.md)은 실행 직전 허가 재검사, 자료 연결 개수와 stdin 옵션을 지우지 않는 판, 무모델 조회·진단을 더했고, [독립 재검토](2026-09-24-pr31-safety-review/README.md)와 [병합 검증](2026-09-24-merge-31-32/README.md)을 거쳐 main에 들어왔다. 그 앞 구현은 [순서 5 실행 계약](2026-09-24-execution-contract/README.md)이다. 아래 재검토의 제안대로 G4·G6을 닫았고, 옛 판은 실제로 돈 계획에만 대응시켜 기록된 Claude 관측으로는 허가가 나오지 않는다. 그 앞 검토는 [병합 후 재검토·실제 관측](2026-09-24-post-merge-verification/README.md)이다. GitHub head checkout·CI·병합 이력, 실제 브라우저의 모의 흐름/Q4/교차 출처 차단, 승인된 K46 확인, Windows 진단 인코딩 수정과 실행 계약 제안을 담았다. C3는 남는다. Q4는 화면 확인을 마쳤고 사용자 선택은 미정이다. 취소 확인창·실제 파일 다운로드 끝단은 순서 5 구현 때 claude 세션이 설치된 Edge로 확인했다. 이전 검토 당시의 도구 제약과 현재 상태를 구분한다.

그 앞 구현은 [새 main 후속](2026-09-24-offline-progression/README.md)의 PR #22–#25이며 [병합 검증](2026-09-24-merge-22-25/README.md)을 거쳐 main에 들어왔다. 아래 날짜 기록의 당시 표현은 유지한다.

이 저장소의 검토 기록은 아래 시간순으로 읽는다. **뒤로 갈수록 최신이며, 앞의 것은 그 시점의 기록으로 남긴다.**

1. [`v0.4/FINAL_REVIEW.md`](../architecture/v0.4/FINAL_REVIEW.md) — PR #1 최종 검토
2. [`v0.4/EVIDENCE_FOLLOWUP.md`](../architecture/v0.4/EVIDENCE_FOLLOWUP.md) — 남은 출처 재확인, F22–F24
3. `2026-09-22-external-review.md` (이 폴더) — 외부 검토 원문
4. [`v0.4/REVIEW_FIXES.md`](../architecture/v0.4/REVIEW_FIXES.md) — 3의 반영 결과와 그 뒤 cross_check, F25–F27
5. [`2026-09-23-mcp-ui-runtime/`](2026-09-23-mcp-ui-runtime/README.md) — MCP·앱·UI 검토. `validate()`는 판정을 *검사*할 뿐 *계산*하지 않는다는 정정 포함
6. [`2026-09-23-v04-01-review/`](2026-09-23-v04-01-review/README.md) — aux-pc 원 출력과 후속 도구·판정·진입 조건 검토. 재현 범위와 원 출력 선검토의 한계도 명시
7. [`2026-09-23-v04-01-review/RESPONSE.md`](2026-09-23-v04-01-review/RESPONSE.md) — 6의 발견별 반영·보류와 이유, 리뷰 밖에서 새로 찾은 것
8. [`2026-09-23-wsl2-boundary/REVIEW.md`](2026-09-23-wsl2-boundary/REVIEW.md) — V04-03 실행 코어의 경계와 WSL2가 해결하는 것·하지 않는 것
9. [`2026-09-23-wsl2-boundary/RESPONSE.md`](2026-09-23-wsl2-boundary/RESPONSE.md) — 8의 발견별 반영, WSL2 확정과 격리 백엔드(bubblewrap) 선택, 작업 순서
10. [`2026-09-23-wsl2-migration-request/`](2026-09-23-wsl2-migration-request/README.md) — 9 이후 작업(WSL2 설치, 실행 명세, bubblewrap 격리)의 검토 요청
11. [`2026-09-23-wsl2-migration-review/`](2026-09-23-wsl2-migration-review/README.md) — 10에 대한 리뷰(WM-01–WM-07, 질문별 답, 구조 평가)
12. [`2026-09-23-wsl2-migration-review/RESPONSE.md`](2026-09-23-wsl2-migration-review/RESPONSE.md) — 11의 발견별 반영, 리뷰 밖에서 새로 찾은 것, 바뀐 작업 순서
13. [`2026-09-23-a1-handoff-request/`](2026-09-23-a1-handoff-request/README.md) — 12 이후 작업(WM 반영, A1 모의 앱)과 새 인계의 한계 표·계획에 대한 검토 요청
14. [`2026-09-23-a1-handoff-review/`](2026-09-23-a1-handoff-review/README.md) — 13에 대한 리뷰. 기준 commit `4bbd034b33649f0ae570b37eecc17d3176669420`, 코드 우선 판단·고정 재현 스크립트·관측 포함
15. [`2026-09-23-a1-handoff-review/VERIFICATION-20260923.md`](2026-09-23-a1-handoff-review/VERIFICATION-20260923.md) — 중단 후 CI 원문 재확인, WM-07 답변의 정정, 실제 호출 전 보강 순서와 남은 검증
16. [`2026-09-23-a1-handoff-review/RESPONSE.md`](2026-09-23-a1-handoff-review/RESPONSE.md) — 14·15의 발견별 반영, 심각도를 다르게 본 곳, 리뷰 밖에서 새로 찾은 것(같은 참여자 이중 실행, Windows의 같은 포트 이중 bind), 바뀐 계획
17. [`2026-09-23-stage2-request/`](2026-09-23-stage2-request/README.md) — 16 이후 1단계(N1–N6)와 2단계 호출, 관측 도구 수정, 실패·시행착오에 대한 검토 요청
18. [`2026-09-24-review-request/`](2026-09-24-review-request/README.md) — 17을 이어받아 main `a26e504`까지의 작업(PR #8–#12)과 전체 흐름, 실패·시행착오에 대한 검토 요청
19. [`2026-09-24-review/`](2026-09-24-review/README.md) — 17·18에 대한 검토와 질문별 답. K46·실행 허가·관측 도구 반례, 근거 수준 비교, 인계 점검과 승인 전 보강 순서
20. [`2026-09-24-review/RESPONSE.md`](2026-09-24-review/RESPONSE.md) — 19의 발견별 반영(R01–R03·R05–R08 수용, R04·R09 부분 수용), 합성 HOME 진단, 리뷰 밖에서 새로 찾은 것, 사용자에게 묻는 것
21. [`2026-09-24-a1-integrity/`](2026-09-24-a1-integrity/README.md) — 현재 코드 직접 검토·수정과 A1 모의 후속. 기존 관측/결정은 유지했고 K18·K27·K42의 부분 진행과 실제 브라우저/CLI 미검증을 구분
22. [`2026-09-24-lean-lifecycle/`](2026-09-24-lean-lifecycle/README.md) — 최소 코드/효율 검토. 기존 runner 경로를 재사용한 K19 구현과 자원 상한·조회 개선. 이전 기록의 “취소 없음”과 연결 상한 부재는 이 후속에서 변경했으며 실제 CLI/문맥 검증 완료로 올리지 않음
23. [`2026-09-24-structure-audit/`](2026-09-24-structure-audit/README.md) — 21 뒤의 main(`99d9bb4`) 전체에 대한 구조 검사. 22와 독립으로 썼다(blind). 사본이 흩어진 규칙, 문서와 코드가 다른 곳, 다음 기능 전에 할 통합. 22와의 비교는 같은 폴더의 `COMPARISON.md`
24. [`2026-09-24-offline-progression/`](2026-09-24-offline-progression/README.md) — 23의 순서 1–4를 codex가 구현한 기록(PR #22–#25). 판단·주인 모듈·검토 중 고친 결함·검증 범위
25. [`2026-09-24-merge-22-25/`](2026-09-24-merge-22-25/README.md) — 24의 PR들을 claude가 확인하고 병합한 기록. 쌓인 브랜치의 인계 충돌과 통합 병합, 병합 트리 동일성, 로컬 전체 시험과 코드 검토
26. [`2026-09-24-post-merge-verification/`](2026-09-24-post-merge-verification/README.md) — codex의 병합 후 재검토(PR #28). GitHub 원문 대조, 실제 브라우저, 승인된 K46 확인, 진단 인코딩 수정, 실행 계약 제안
27. [`2026-09-24-execution-contract/`](2026-09-24-execution-contract/README.md) — 26의 제안을 claude가 구현한 순서 5(PR #30). 계획 한 번, 계획에서 계산한 판, 옛 판의 정확한 대응, 시도에 저장한 실행 종류
28. [`2026-09-24-cli-readiness/`](2026-09-24-cli-readiness/README.md) — 27을 codex가 재검토하고 고친 기록(PR #31). 실행 직전 허가 재검사, 자료 연결 개수, stdin 옵션 가림, 서버 연결 전 조회와 무모델 진단, main 보호 적용
29. [`2026-09-24-pr31-safety-review/`](2026-09-24-pr31-safety-review/README.md) — 28에 대한 ChatGPT의 독립 재검토(PR #32). 계획 뒤 허가 변경의 회귀 시험 보강과 문맥 독립성의 다음 확인
30. [`2026-09-24-merge-31-32/`](2026-09-24-merge-31-32/README.md) — 28·29를 claude가 확인하고 병합한 기록. 판 직접 계산, 변이 시험, 병합을 막지 않는 발견
31. [`2026-09-24-live-cli-pilot/`](2026-09-24-live-cli-pilot/README.md) — PR #34 head의 단일 실제 서버 응답과 공개 답 독립성 표시 정정. 원문 API 저장과 다운로드 미관측을 구분하고 추가 호출 예산이 없음을 기록
32. [`2026-09-24-live-pilot-replication/`](2026-09-24-live-pilot-replication/README.md) — 31을 claude가 별도 원장·다른 질문으로 재현하고 #34·#35를 검토·병합한 기록. 변이 시험, 예산 소진 거절, 발견 N1–N5, 다음 작업 권고
33. [`2026-09-24-cli-unblock/`](2026-09-24-cli-unblock/README.md) — ChatGPT 웹 세션의 PR #38. 32에서 찾은 상한 고정·회계 문제를 고치고 provider별 병렬 연결과 계정 메타데이터 도구를 더했다. Windows 패치는 평문으로 남겼다
34. [`2026-09-24-windows-live-completion/`](2026-09-24-windows-live-completion/README.md) — 33을 이어 codex가 Windows 패치를 적용하고 실제 Codex·Claude 병렬 응답과 계정 한도 화면을 관측한 기록(PR #39)
35. [`2026-09-24-merge-39/`](2026-09-24-merge-39/README.md) — 33·34를 claude가 검토·병합한 기록. 변이 시험, 검증 도구의 Windows 출력 오류, 다음 작업의 근거가 된 문서·코드 확인
36. [`2026-09-24-account-limits/`](2026-09-24-account-limits/README.md) — 35가 정한 다음 작업 중 A·F. 봉인·실제 실행 규칙을 지키는 Claude 한도 표시, Codex 가용 모델의 실제 조회
37. [`2026-09-24-source-snapshot/`](2026-09-24-source-snapshot/README.md) — 다음 작업 B와 A·F의 실제 확인. 공통 자료를 입력 digest에 묶고 시도마다 확인, 두 답이 같은 자료를 인용한 실제 실행
38. [`2026-09-24-model-synthesis/`](2026-09-24-model-synthesis/README.md) — 다음 작업 C. 37의 공개된 실행에 실제 합성 1회, 인용 대조와 추가 주장 표시

## 28번 기록에 대한 단서

- `README.md` 검증 절의 "최종 전체 검사 및 정확한 head CI 결과는 같은 폴더의 `VALIDATION.md`에 기록한다"는 실제와 다르다. 최종 결과는 [`FINAL-VALIDATION.md`](2026-09-24-cli-readiness/FINAL-VALIDATION.md)에 있고, `VALIDATION.md`는 작성 중 상태를 보존한 것이다(30번 기록 N2). 원문은 당시 기록으로 둔다.
- 28·29번이 인용한 `learn.chatgpt.com` 문서는 30번 세션이 열지 못했다(그 컨테이너의 외부 접속 정책). 웹 검색 색인으로 페이지가 있다는 것만 확인했다. 그 문서의 내용은 28·29번 세션이 읽은 것이다.

## 25번 기록에 대한 단서

- **전체 트리와 코드 동일성을 구분한다.** #25 head와 전체 트리가 같은 것은 문서 정리 전 통합 `fbb7225eaeec72360731d58db214da7375411375`다. #26/main에는 문서 변경이 있어 전체 tree SHA가 다르며 코드·시험은 같다. 기존 CI 링크는 PR 합성 merge checkout이었다. 같은 head의 push run과 실제 checkout SHA도 성공했으므로 결론은 유효하다. 더 직접적인 근거는 [GitHub 재검토](2026-09-24-post-merge-verification/GITHUB.md)에 있다.
- "병합 뒤" 절의 "통합 PR로 들어간 codex 브랜치 넷은 GitHub의 자동 삭제 대상이 아니므로 병합한 이 세션이 원격에서 지운다"는 틀렸다. PR #26 병합(`ff8e356`) 직후 GitHub가 #22–#25를 병합됨으로 표시했다. 그리고 저장소 설정(병합 시 자동 삭제)이 네 head 브랜치를 1–3초 안에 지웠다(각 PR의 `head_ref_deleted` 사건). claude 세션이 지울 브랜치는 남지 않았다. 원문은 당시 기록으로 두고, [NEXT-SESSION.md](../../NEXT-SESSION.md) 3절은 원본에서 고쳤다.

## 23번 기록에 대한 단서

- 기준은 main `99d9bb4`다. 그 뒤 22번(PR #20)이 K19 취소를 플래그 방식으로 넣었다. 그래서 5절 4의 "K19 취소 전에"는 "다음 기능 전에, 취소 판단을 파생 gate 하나로 모은다"로 읽는다. 지금의 작업 순서는 [NEXT-SESSION.md](../../NEXT-SESSION.md) 4절이다.
- 4절의 틈 G1–G9는 PR #20 병합 뒤의 main(`962b61c`)에서도 그대로다. 2026-09-24에 claude 세션이 다시 확인했다. 줄 번호는 `99d9bb4` 기준이다.

## 22번 기록의 통합 상태 정정

- 기술 검토·측정·코드는 그대로다. 작업 중 PR #18이 2026-09-24 13:01:34 KST에 다른 세션에서 main으로 병합됐고, 13:01:37 KST에 그 브랜치가 삭제되어 기준으로 쓰던 PR #19가 자동으로 닫혔다. 변경 거절이나 코드 유실이 아니다.
- 삭제된 base로는 PR #19를 다시 열거나 main으로 바꿀 수 없어, 같은 `chatgpt/lean-cancellation-20260924` 브랜치의 [PR #20](https://github.com/inlight37-design/decision-model_lab/pull/20)을 main 대상으로 열었다. 원문의 “PR #18을 먼저 병합하고 #19를 retarget” 및 “PR #19의 Checks”는 **PR #18 병합 완료, PR #20의 최신 head Checks 확인**으로 정정한다. 원문은 당시 기록으로 보존한다.
- 현재 인계는 [NEXT-SESSION.md](../../NEXT-SESSION.md) 3절이고, PR #20 본문/Checks가 최종 검증 commit의 기준이다. ChatGPT는 main이나 이전 세션 브랜치를 수정·병합하지 않았다.

## 20번 기록에 대한 단서

- R08 행의 `pad_markers_seen`은 기록만 했고 판정에 들어가지 않았다. 표식을 놓친 큰 입력도 `as_expected`가 참이었다([PR #15](https://github.com/inlight37-design/decision-model_lab/pull/15)에 대한 Codex 리뷰, P2). 병합 뒤 claude 세션이 두 표식을 모두 되말해야 기대대로가 되게 고쳤다(`CallTests.test_a_padded_question_is_judged_by_its_end_marker`). 기록 원문은 고치지 않았다.

## 19번 기록에 대한 단서

- 코드 기준은 `a26e504`, 공개 관측 기준은 `7329a31`이다. 사용자 PC·WSL·실제 provider CLI·모델을 실행하지 않았다.
- 재현은 해시가 일치하는 `eligibility` 원본과 관측 판정식 발췌를 합성 데이터로 실행한 것이다. 저장소 전체 시험이나 실제 샌드박스 검증과 구분한다. `results.json`의 `repository_ast_verification`은 `false`다.
- 문맥 상태와 완료 표현에 대한 이견은 검토 원문에만 남겼다. 반영 세션은 발견별로 재현·반박·보류를 별도 기록하고, 검토 원문을 수정하지 않는다. 최종 CI는 PR의 정확한 head를 기준으로 본다.
- 반영 세션(20번)이 `reproduce.py --repo`를 기준 코드에 돌려 AST 일치와 반례를 모두 확인했다. 고친 코드에서는 이 스크립트가 해시 불일치로 멈춘다 — 의도된 동작이다. 고친 동작은 `tests/`의 회귀 시험에 있다.
- R08이 지적한 [K01 기록](../experiments/w2-isolation/k01-large-input-aux-pc-wsl.md)의 "끝까지 읽었다"는 "약 95 KB 전송, 정상 응답, 입력만큼의 토큰 증가 관측"으로 좁혀 읽는다. 기록 원문은 고치지 않았다.

## 17번 기록에 대한 단서

- 17번은 리뷰받기 전에 18번이 이어받았다. 17번의 S01–S21과 질문은 유효하고, 지금 상태는 18번의 "17번의 S01–S21 — 지금 상태" 표에 있다.

- 요청서가 병합된 뒤(2026-09-24) 모델 없는 후속 진단에서 새 한계를 찾았다: **Codex 참여자의 명령이 Codex의 로그인 파일을 읽을 수 있다(K46).** 요청서의 S 목록과 질문에는 없다. 리뷰어는 [후속 기록](../experiments/w2-isolation/stage2-followup-aux-pc-wsl.md)을 함께 읽고, 방어 후보(인증 파일만 읽기 금지하는 권한 profile)와 K09를 그 뒤로 미룬 판단도 검토한다.
  - 정정(2026-09-24): 후속 기록의 "exec에 `-P`를 넘긴다"는 틀렸다 — `codex exec`에는 `-P`가 없고 profile은 `default_permissions`로 고른다. 그 방식으로 adapter에 넣었다([K46 profile 기록](../experiments/w2-isolation/k46-profile-aux-pc-wsl.md)). exec에서 모델의 명령에 금지가 적용되는지는 아직 관측하지 않았다.
- 요청서가 적은 "main 병합이 막혔다"(S16)는 그 뒤 사용자 지시로 병합했다. PR을 만들지 못한 것(S17)은 GitHub CLI를 설치하고 사용자가 로그인해 풀렸다 — claude 세션이 [PR #9](https://github.com/inlight37-design/decision-model_lab/pull/9)부터 직접 연다. CI 원문 로그도 읽는다(K37).

## 14번 기록에 대한 단서

- 원문의 질문 2 표 중 **WM-07 행은 주제를 잘못 연결한 편집 오류**다. 잔류 스레드·fd, `lingering()`, controller의 새 시도 억제에 관한 답은 15번 정정이 대체한다. 원문과 이전 관측은 보존한다.
- `reproduce.py`는 검토 대상의 소스 blob을 고정한다. 수정된 코드에서는 해시 검사로 멈춘다. 종료 코드 0은 관측 절차 완료일 뿐 결함 수정 완료가 아니다. 고칠 때 해당 반례를 제품 회귀 시험으로 옮겨 기대 결과를 반대로 고정한다.
- 기록의 실제 bubblewrap 실행과 합성 executor의 containment 필드를 구분한다. 재개 세션은 기존 CI 원문을 재확인했으며 사용자 PC·실제 모델을 실행하지 않았다. 이전 재현 실행의 녹색과 최종 PR의 CI는 별개다.
- 본문에서 예고했던 AGENTS 현재 상태 정정, NEXT 3절과 이 목록의 연결은 재개 작업에서 마무리했다. 발견의 수용·반박과 실행 코드의 수정은 후속 반영 기록으로 남겨야 한다 — 16번이 그 기록이다.
- A1-02의 실제 bubblewrap 사례(질문 없이 성공 JSON만 출력해도 수용·공개)는 일부러 stdin을 주지 않는 시험용 실행기의 결과다. 당시 제품 경로는 늘 질문을 보냈다. 요약해 옮길 때 본문의 "한정" 문단을 함께 옮긴다(16번).

## 11번 기록에 대한 단서

- 리뷰는 수정 **전** 코드(`a662e59`)를 본다. `reproduce.py`는 코어 파일의 해시가 다르면 멈추므로 지금 `main`에서는 돌지 않는다. 수정 전 관측은 `results.json`에, 고친 동작은 `tests/`의 회귀 시험에 있다.

## 8번 기록에 대한 단서

- 리뷰는 수정 **전** 코드를 본다. 번들의 재현 스크립트는 스냅숏을 검사하므로 지금 실행해도 수정 전 동작이 나온다.
- R01·R02는 POSIX 경로의 결함이다. 보조 PC의 Windows 경로(job object)는 같은 시나리오를 정상 처리했다 — 지금 실행이 아니라 WSL2 이전을 막는 결함이다.

## 6번 기록에 대한 단서

- 리뷰는 수정 **전** 코드를 본다. `reproduce_findings.py`를 지금 실행하면 고친 동작이 나오고, `reproduction-output.json`은 수정 전 관측이다.
- 리뷰가 지적한 aux-pc 기록의 과한 문장(Claude `permission_mode`의 `observed`, "깨끗한 문맥", "agy 기본 모델은 Flash")은 원본에서 정정 표시와 함께 고쳤다. 무엇을 고쳤는지는 RESPONSE.md에 있다.

## 5번 기록에 대한 단서

- 본문의 "루트의 날짜 붙은 파일"은 이후 [`docs/handoff/`](../handoff/README.md)로 옮겼다. 내용은 바이트 그대로다.
- 이 검토는 웹 컨테이너에서 수행됐고 사용자 PC·CLI에 접근하지 않았다. 환경 사실은 그 한계 안에서 읽는다.

## 3번 문서에 대한 단서

이 판본은 **두 건의 지적이 정정되기 전** 상태다. 확인 결과 저장소 쪽이 옳았다.

- `published` 결측 8건은 결함이 아니었다 — 살아있는 문서는 `revised`, 고정 commit은 `revision`을 쓴다. 실제 결함은 F17/F18/F19만 날짜 필드가 없던 것
- 날짜의 축소 정밀도(`2025`, `2024-07`)도 정상이다 — 아는 것보다 정밀하게 적지 않은 처리다

정정 내역은 `REVIEW_FIXES.md` §2에 있다. 원문을 고치지 않고 남기는 이유는 **검토자가 무엇을 틀렸는지도 기록이기 때문**이다.
