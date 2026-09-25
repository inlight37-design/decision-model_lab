# 검토 도중 병합된 새 설치판 대조 — 2026-09-25

**최초 검토의 기준은 `2f76a1a6fdd6b4ca8edf5111460f7ae806c8977b`이다.** 결과를 작성하는 동안 다른 세션이 PR #74를 수정하고 2026-09-25 09:23:49 UTC(18:23:49 KST)에 병합했다. 새 main은 `2450caff5b3bf58eabee5d2486ba7a294c63dd89`, PR #74의 최종 head는 `5f89c646e566a5d736b8dc7a2134c47a33cd28f1`이다. 이 문서는 최초 검토를 새 판의 전수 검토로 포장하지 않기 위한 차이 기록이다. ChatGPT는 #74를 병합하지 않았다.

## 직접 확인한 차이

GitHub compare로 변경 파일을 확인하고 새 `tools/setup/setup.ps1` 전체, 새 `setup-wsl.sh` 전체, 최신 인계의 바뀐 구간과 PR #74 본문을 읽었다. Windows에서 실행한 것은 아니다.

| 최초 발견 | 새 판에 대한 판단 |
|---|---|
| R01 Windows 실패 가림 | **일부 해결.** 옛 `setup-windows.ps1`은 삭제되고 `setup.ps1`로 바뀌었다. 새 5단계는 apt와 CLI 설치 직후 종료 코드를 확인하여 중단하고, 마지막 검사는 Windows·Linux 실패를 누적한다. 따라서 옛 R01의 WSL 실패가 Windows 성공으로 덮이는 설명을 새 코드에도 그대로 적용하면 안 된다. 그러나 winget 단계는 종료 코드보다 PATH 재확인/경고에 기대고, pip 실패는 경고 뒤 `ok test dependency and encoding hook`를 출력하며 hook 설정 결과도 확인하지 않는다. 각각의 필수/선택 의미를 명시해야 한다 |
| R02 관측 실패 뒤 latest | **새 셸에 같은 경로가 남음.** `want`의 기본값 `latest`와 process substitution으로 읽는 구조가 같다. 기존 재현은 최초 판으로 실행했고 새 판에 다시 실행한 결과는 아니다 |
| R03 승인과 실행 파일 불일치 | **새 셸에 같은 경로가 남음.** 승인 재실행에서 파일을 새로 받고 `accept=1`이면 해시 불일치를 모두 통과시키는 구조다. 최초 판 A/B 재현과 새 판 코드 관측을 구분한다 |
| R04 설치 확인의 의미 | 이번 compare에서 Python 확인 도구의 변경은 새 Windows 설치 명령 안내다. 새 setup의 Claude 로그인 확인도 `loggedIn: true` 정규식만 검사하므로 구독 방식 확인으로 확대할 수 없다. 최초 Python 경계 재현의 기준 SHA는 유지한다 |
| R05 #70 / R06 #71 | 이 병합은 `core`·`app`을 바꾸지 않았다. 최신 PR 본문도 #70·#71 미수정을 명시한다. 최초 검토의 실행 경계/설계 권고는 유지한다 |
| R07 #74 상태 문구 | 최초 검토 시점에는 open이었으므로 당시 지적은 유효하다. 현재는 실제로 병합됐으므로 최신 NEXT의 병합 이력을 보존한다. 초기 D의 T2 `모든 인용` 대 `9/10` 불일치는 별도 정정으로 유지한다 |

원문은 움직이는 상대 경로 대신 정확한 판에서 읽는다: [최초 Windows 코드](https://github.com/inlight37-design/decision-model_lab/blob/2f76a1a6fdd6b4ca8edf5111460f7ae806c8977b/tools/setup/setup-windows.ps1), [새 Windows 코드](https://github.com/inlight37-design/decision-model_lab/blob/2450caff5b3bf58eabee5d2486ba7a294c63dd89/tools/setup/setup.ps1), [새 WSL 코드](https://github.com/inlight37-design/decision-model_lab/blob/2450caff5b3bf58eabee5d2486ba7a294c63dd89/tools/setup/setup-wsl.sh).

## 새 경계 — 코드 관측이며 Windows 재현 아님

### U01 · 중간 · CheckOnly의 무변경 약속과 transcript

새 스크립트는 `-CheckOnly`를 분기하기 전에 `Start-Transcript -Path "$env:USERPROFILE\dml-setup.log" -Append`를 시도한다. 따라서 파일 쓰기에 성공하면 확인 전용도 파일을 만들거나 늘린다. `changes nothing` 설명과 맞지 않는다. 확인 모드는 기본 로그 쓰기를 끄거나 명시적으로 그 예외를 설명해야 한다.

또한 transcript는 로그인 단계까지 계속된다. 실제 토큰/비밀번호가 기록됐다고 주장하지 않는다. 다만 로그인 명령이 출력하는 승인 코드·URL·계정 정보 중 무엇이 저장될지는 실행판별 확인이 필요하다. 로그인 전 transcript를 중단하고 비식별 성공/실패 요약만 남기는 편이 안전하다. 로그를 저장소에 자동 업로드하지 않는다.

### U02 · 중간 · 재부팅 필요 판정과 사용자 생성의 실패 상태

`Start-Process wsl.exe ... -Wait`는 실행된 설치 프로세스의 ExitCode를 얻어 검사하지 않는다. 이후 배포판 목록에 없으면 재부팅 필요로 추정하고 RunOnce를 등록한다. 다운로드 실패·잘못된 배포판 등도 구분해야 하며, 재부팅만 반복하는 경로가 없어야 한다. 예약 등록 자체가 실패했는지도 확인한다.

Linux 사용자 생성의 `useradd`, `passwd`, 설정 쓰기, 재시작 뒤 `id -u`는 각각 성공을 검사하지 않는다. 마지막 검사는 문자열이 `'0'`인지에 집중하므로 실패한 조회의 빈 출력과 정상 non-root 사용자를 구분해야 한다. 뒤 CLI 단계가 결국 실패할 수 있다는 점은 중간 `Linux user ready` 문구를 정당화하지 않는다. 정상 숫자 UID와 해당 명령의 종료 상태를 함께 확인하고, 실패 단계에서 중단하는 시험이 필요하다.

## 권고와 보존

새 원터치 기능의 편의는 인정하지만 실행 범위가 커졌으므로 빈 PC 설치·재부팅 재개·로그인과 로그 보호를 별도 완료 조건으로 둔다. 최초 리뷰가 긍정한 `winget 약관 자동 수락 안 함`은 **최초 판에만 해당**한다. 새 판은 실행을 약관 동의로 간주하고 두 자동 수락 옵션을 쓴다. 이는 사용자가 읽을 시작 안내에서 분명하게 드러나야 한다.

새 관측 없이 `원터치 설치 완전 검증`으로 승인하지 않는다. 기존 질문 1–7의 분류·#70/#71·L1/카드 시범 판단은 유지하되, Windows 수정자는 R01만이 아니라 이 새 판 차이와 U01/U02를 함께 읽는다.

`probe.py`는 기준 소스가 바뀌면 의도적으로 중단한다. 최신 main에서 재현하려고 해시 검사만 제거하지 않는다. 최초 파일의 별도 디렉터리를 정확한 commit에서 마련하고 `--root`로 지정한 뒤 재현 스크립트를 실행한다. 새 판의 재현은 새 SHA와 새로운 결과로 남긴다.

이 검토는 새 판의 전체 설치 경로·로그인·재부팅을 직접 실행하지 않았다. API 상태, 변경 목록과 위 원문 코드만 추가로 확인했다.
