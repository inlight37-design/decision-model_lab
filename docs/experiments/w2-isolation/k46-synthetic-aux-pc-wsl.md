# K46 — 합성 HOME에서 본 권한 profile과 k46 helper, `aux-pc-wsl`

2026-09-24 · claude 세션(Claude Opus 5.5, aux-pc의 로컬 checkout, `wsl.exe`로 배포판의 로그인 셸에서 실행). **모델 호출 없음. 사용자의 실제 `~/.codex`(로그인 파일)는 연결하지 않았다.** 도구: [`tools/w2/codex_profile.py`](../../../tools/w2/codex_profile.py)의 기본 모드. Codex 0.156.1.

## 왜 했나

- [2026-09-24 리뷰](../../reviews/2026-09-24-review/README.md)가 `k46-codex`의 합격 조건이 실제 차단을 보증하지 않는다고 지적했다(R01). 판정을 셸 종료 코드에서 **고정 helper의 errno 이름**으로 바꿨다. helper는 인증 파일을 열었다 닫기만 한다.
- 새 합격 조건은 인증 파일이 `EACCES`·`EPERM`으로 거절돼야 한다는 것이다. `ENOENT`는 대상이 안 보인 것이라 거절로 치지 않는다. **실제 Codex 샌드박스가 profile로 막을 때 어느 errno를 주는지** 승인된 호출 전에 알아야 했다.
- 리뷰는 실제 로그인 상태를 연결하는 진단도 허락을 받고 하라고 권했다(질문 3). 그래서 가짜 인증 파일만 둔 합성 HOME에서 봤다(질문 9).

## 어떻게 봤나

- 임시 폴더에 합성 HOME을 만들고 `~/.codex/auth.json`에 비밀이 아닌 가짜 내용을 넣었다. 격리 안에는 그 합성 `~/.codex`와 Codex 실행 파일의 버전 폴더(읽기 전용)만 연결했다.
- 참여자와 같은 bubblewrap 경계에서 `--share-net`만 빼고(네트워크 없음) `codex sandbox [profile] -- /usr/bin/python3 <helper>`를 변형마다 한 번 돌렸다. helper는 `observe.py`의 `K46_HELPER` 그대로다.
- 변형: profile 없음(대조군), exec 방식(`-c permissions.dml-discussant=…`와 `-c default_permissions="dml-discussant"`), `-P` 방식. profile의 금지 경로는 합성 HOME의 `auth.json`이다.

## 결과

| 변형 | exit | 작업 폴더 쓰기 | 공통 자료 열기 | 인증 파일 열기 | 남은 파일 | 자손 종료 |
|---|---|---|---|---|---|---|
| profile 없음(대조군) | 0 | `denied:EROFS` | `ok` | **`ok`** | 없음 | 확인 |
| exec 방식(`default_permissions`) | 0 | `denied:EROFS` | `ok` | **`denied:EACCES`** | 없음 | 확인 |
| `-P` 방식 | 0 | `denied:EROFS` | `ok` | **`denied:EACCES`** | 없음 | 확인 |

- 세 변형 모두 stderr에 경고 한 줄이 있었다: `Refusing to create helper binaries under temporary dir "/tmp"`. 합성 HOME이 `/tmp` 아래라서 Codex가 보조 실행 파일 별칭을 만들지 않았다는 뜻이다. 명령 실행에는 영향이 없었다.
- 가짜 인증 파일의 크기·수정 시각은 바뀌지 않았다.

## 판정

- 대조군에서 helper가 인증 파일을 **열었다**. 그러니 profile 변형에서 열지 못한 것은 파일이 없어서가 아니다. 파일이 있고, profile이 `EACCES`로 막았다.
- 새 판정(`observe.k46_passed`)이 기대하는 모양이 실제와 같다: 쓰기 `denied:EROFS`, 공통 자료 `ok`, 인증 파일 `denied:EACCES`.
- 2026-09-24 실제 HOME 진단([K46 profile 기록](k46-profile-aux-pc-wsl.md))의 결론 — `default_permissions`로 고른 profile이 `-P`와 같게 인증 파일만 막는다 — 과 맞는다. 이번에는 사용자 로그인 파일 없이 확인했다.

## 아직 아닌 것

- `codex sandbox`로 본 것이다. **exec에서 모델이 돌린 명령**에 같은 금지가 적용되는지는 여전히 `observe.py call k46-codex` 1회가 필요하다(승인 필요).
- 합성 HOME은 `/tmp` 아래였고 실제 HOME은 아니다. 경로 모양이 다르면 Codex의 동작이 다를 수 있다 — 실제 호출이 실제 HOME에서 본다.
- 배포판 하나, Codex 0.156.1 하나다. 권한 profile은 문서상 베타다.
