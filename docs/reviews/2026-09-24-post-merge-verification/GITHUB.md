# GitHub 병합·CI 재검토

관측 시각: 2026-09-24 06:31 UTC. 저장소: `inlight37-design/decision-model_lab`. 읽기 전용 감사이며 설정·브랜치·PR을 변경하지 않았다. GitHub 플러그인으로 PR·Actions job과 로그를 확인했고, 플러그인이 제공하지 않는 push 실행·보호 설정·삭제 사건은 로그인된 `gh api`로 읽었다. 사용자 PC의 로컬 저장소 Git 객체와 대조했다.

## 결론

병합·순서·CI·브랜치 정리 주장은 확인됐다. 코드 누락이나 병합 순서 오류는 발견하지 못했다. 두 표현은 더 정확히 쓸 수 있다.

- **전체 트리 동일성:** PR #25 head와 동일한 것은 문서 정리 전 순차 통합 커밋 `fbb7225eaeec72360731d58db214da7375411375`다. #26 최종 결과 및 현재 main은 문서가 달라 전체 Git 트리는 다르지만, 코드와 시험은 동일하다.
- **정확한 head CI 근거:** 기존 기록이 링크한 실행은 `pull_request` 이벤트여서 실제 checkout은 GitHub의 합성 merge SHA였다. 같은 head의 `push` 실행도 모두 성공했고, 이번에는 양쪽 Python job의 실제 checkout SHA까지 확인했다. 기존 성공 결론은 유효하며 아래 push 링크가 더 직접적인 근거다.

운영상 남은 사항은 **main 보호 없음**이다. 보호가 강제되지 않으므로 CI 녹색 뒤 병합 규칙은 현재 사람과 세션의 준수에 의존한다. 이번 감사에서 설정은 변경하지 않았다.

## 정확한 SHA와 CI

모든 PR은 GitHub API에서 `merged=true`, `state=closed`다. 아래 push 실행은 Python 3.12·3.13 두 job 모두 `success`; 두 로그의 `git log -1 --format=%H`가 표의 head와 일치했다. #22–#27 각 전체 suite는 Windows 레지스트리 전용 시험 하나를 제외하고 성공했다. workflow는 `DML_REQUIRE_BWRAP=1`을 설정하며 bubblewrap 준비와 전체 suite 단계가 모두 성공했다.

| PR | 최종 head | 병합 커밋 | 정확한 head의 push CI |
|---|---|---|---|
| [#22](https://github.com/inlight37-design/decision-model_lab/pull/22) | `5f3a856ab2d089511786ddeb0203809885a2aacf` | `0eeb5b6c42c7bb1c0b2d435bef945502d44aacf9` | [35960129953](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960129953) |
| [#23](https://github.com/inlight37-design/decision-model_lab/pull/23) | `6617ce5ede44d96b7f42e76e0417c145435612a9` | `7c0b015f7640b812949b7fd454c46ebaf599ed37` | [35960249780](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960249780) |
| [#24](https://github.com/inlight37-design/decision-model_lab/pull/24) | `c0b5e18620185e62f4c2307eaef705df31b00393` | `4e4037fa5f1547701ae5e27531b91a223f46d19e` | [35960294351](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960294351) |
| [#25](https://github.com/inlight37-design/decision-model_lab/pull/25) | `e053d0de35f71396d701020e43a032e2c43dc806` | `fbb7225eaeec72360731d58db214da7375411375` | [35960706854](https://github.com/inlight37-design/decision-model_lab/actions/runs/35960706854) |
| [#26](https://github.com/inlight37-design/decision-model_lab/pull/26) | `8156dcb7e48b0c2a6fc9ac7fea895c46d623e0a0` | `ff8e356375d4d302b4b228661e868f0575873bfc` | [35963912824](https://github.com/inlight37-design/decision-model_lab/actions/runs/35963912824) |
| [#27](https://github.com/inlight37-design/decision-model_lab/pull/27) | `a41672b128ee13fc0e0bb94f072226a3d06246ac` | `eec60e93ef6c95639181eb8cd251506c16290075` | [35964210761](https://github.com/inlight37-design/decision-model_lab/actions/runs/35964210761) |

현재 main `eec60e93ef6c95639181eb8cd251506c16290075`도 [push CI 35964323617](https://github.com/inlight37-design/decision-model_lab/actions/runs/35964323617)의 Python 3.12·3.13 job이 모두 성공했다. 3.12 로그 checkout SHA도 main과 일치했고 전체 suite의 유일한 skip은 Windows 레지스트리 시험이다.

기존 문서의 PR 이벤트 실행(35960132984, 35960254902, 35960299252, 35960752930, 35963942047, 35964214797)도 두 Python job 모두 성공했고 API `head_sha`가 각각 정확한 PR head였다. 다만 #22의 실제 checkout은 `631c51cd42793b7d1dfee755c90a28486dd1f279`처럼 head와 별개인 합성 merge였다. 앞으로 기록은 `head_sha` 연관 확인과 실제 checkout SHA 확인을 구분하면 된다.

## 이력·트리 대조

`git log --first-parent`의 부모 연결은 `34975794… → 0eeb5b6… (#22) → 7c0b015… (#23) → 4e4037f… (#24) → fbb7225… (#25)`다. 각 merge의 두 번째 부모도 해당 PR의 정확한 head다. #26이 이 통합 이력을 main에 넣었고 #27이 문서 정정을 더했다. GitHub에서 #22–#25가 #26보다 늦게 merged로 표시된 시각은 자동 인식 시각이며 Git 그래프의 순서를 뒤집지 않는다.

| 커밋 | 전체 Git tree SHA |
|---|---|
| #25 head `e053d0de35f71396d701020e43a032e2c43dc806` | `0e46510ed3e64e21d06bd652623caf8e2cf7ccc4` |
| 문서 정리 전 통합 `fbb7225eaeec72360731d58db214da7375411375` | `0e46510ed3e64e21d06bd652623caf8e2cf7ccc4` |
| #26 merge `ff8e356375d4d302b4b228661e868f0575873bfc` | `6f785caba006815aac26295e0a1996657f358d65` |
| 현재 main `eec60e93ef6c95639181eb8cd251506c16290075` | `e26a7ebaf272c7d9168c491f8964b8d0cba93711` |

`git diff --name-status e053d0d eec60e9`의 차이는 다음 문서뿐이다: `NEXT-SESSION.md`, `docs/COLLABORATION.md`, `docs/reviews/2026-09-24-merge-22-25/README.md`, `docs/reviews/README.md`. #27 단독 차이는 `NEXT-SESSION.md`와 `docs/reviews/README.md`뿐이다.

## 현재 원격 상태·자동 삭제

- REST `/branches?per_page=100`: main 하나, SHA `eec60e93ef6c95639181eb8cd251506c16290075`.
- REST `/pulls?state=open&per_page=100`: 빈 목록. GitHub 플러그인 검색도 같음.
- 저장소 `delete_branch_on_merge=true`.
- #22–#25 및 #26, #27의 issue events에서 `merged` 뒤 `head_ref_deleted`를 각각 확인했다. #22 1초, #23 2초, #24 1초, #25 1초, #26 3초, #27 2초 뒤다. #27의 자동 삭제 정정은 맞다.
- 현재 main `protected=false`, protection API는 404 `Branch not protected`, repository rulesets는 `[]`. 계정의 저장소 admin 권한이 조회되므로 권한 부족과 구분 가능하다.
- Actions 로그에 checkout@v4/setup-python@v5의 Node 20 폐기 및 Node 24 강제 실행 경고가 있다. 모든 검사는 성공했으며 낮은 우선순위 의존성 정리 후보다.

## 범위

이 감사는 원격 CI·Git 이력·설정을 재검토했다. Windows/WSL 로컬 시험을 새로 돌리지 않았고 실제 모델 호출·브라우저·CLI 인증·실행 허가도 검증하지 않았다. 과거 로컬 시험 성공을 이 감사의 새 관측으로 바꾸지 않았다. 감사 도중 이 작업의 새 브랜치/worktree를 만들었으므로 로컬 브랜치가 main뿐이라는 과거 정리 문장은 이번 작업 시작 전 상태로 읽어야 한다.


