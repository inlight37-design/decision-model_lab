# 검증 완료 — 2026-09-24

앞 [진행 중 기록](VALIDATION.md)은 작성 중 문서 링크가 없었던 첫 실행을 보존한다. 아래는 파일 작성과 커밋 뒤 다시 수행한 결과이며 그 미완료 상태를 대신한다.

## 직접 실행

코드 커밋 **`3b9b61c771b3a757922331030e8be91ba1b09a32`**에서 전체 검사를 실행했다. 검사 중 app/core/tools/tests의 Python·HTML·JS 파일 sha256이 바뀌지 않았음을 확인했다.

| 환경 | 결과 | 건너뛴 범위 |
|---|---|---|
| Windows, Python 3.12.6, jsonschema 4.26.0 | 409 tests, OK | 33개는 Linux·WSL 전용 |
| WSL2 Ubuntu-24.04, Python 3.12.3, jsonschema 4.26.0, `DML_REQUIRE_BWRAP=1` | 409 tests, OK | Windows 레지스트리 전용 하나 |

두 환경 모두 encoding, design tokens, frontier protocol, 최신 K46 inventory 구조, v0.1/v0.2 contracts, source registry, compile 검사를 통과했다. 의존성 부재나 bubblewrap 부재로 건너뛴 시험은 없다. 실제 모델은 호출하지 않았다.

새 readiness의 독립 코드 검토에서 bwrap 신뢰 검사 누락과 임시 폴더 오류가 JSON 대신 예외로 끝나는 문제를 발견해 위 커밋 전에 수정했다. 조회 결과가 실행 승인/namespace 가용성 확인은 아니라는 경계를 출력·문서에 명시했다.

## GitHub CI

위 정확한 코드 커밋의 [push run 35972399622](https://github.com/inlight37-design/decision-model_lab/actions/runs/35972399622)는 성공했다. 각 checkout 로그의 `git log -1 --format=%H` 결과가 **`3b9b61c771b3a757922331030e8be91ba1b09a32`**인 것을 직접 읽었다.

- [Python 3.12](https://github.com/inlight37-design/decision-model_lab/actions/runs/35972399622/job/107544899588): 성공, 409 tests / Windows 전용 skip 1.
- [Python 3.13](https://github.com/inlight37-design/decision-model_lab/actions/runs/35972399622/job/107544899265): 성공, 409 tests / Windows 전용 skip 1.

pull_request run의 `head_sha`로 checkout을 추정하지 않았다. 이 검증 기록을 추가하는 문서 후속 커밋은 실행 코드·시험·관측 결과를 바꾸지 않는다. 병합 시에는 [PR #31](https://github.com/inlight37-design/decision-model_lab/pull/31)의 **최종 head** 필수 CI를 다시 확인한다. 이 문서의 코드 커밋 성공을 뒤 커밋의 CI 성공으로 대신하지 않는다.

## 보존·정리

- 인계 2절(사용자 결정), 5절(금지 사항)이 시작 main과 같은 것을 비교했다.
- manifest와 K46 단일 자료 판을 유지했고 새 호출 승인/예산 초기화는 없다.
- 임시 화면 서버와 브라우저 탭을 종료했다. 사용자 원장은 열지 않았다.
- 기존 codex 작업 폴더는 새 브랜치에 재사용했다. main에 포함된 옛 codex 로컬 브랜치만 ancestry 확인 뒤 삭제했다. 현재 작업 폴더는 PR 작업에 필요하므로 유지한다.
- main 보호 설정은 적용 뒤 두 경로에서 재조회했다. 다른 세션의 자동 승인 분류기 문제를 이 세션의 권한 부족으로 재사용하지 않았다.
