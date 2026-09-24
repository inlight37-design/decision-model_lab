# 첫 실제 CLI 서버 응답 — 2026-09-24

Codex 세션이 사용자 PC `aux-pc`의 WSL2 `Ubuntu-24.04`와 Codex 내장 브라우저에서 직접 실행했다. 사용자는 단일 호출 제안 뒤 “너가 직접 해볼수는 없는건가”라고 요청했다. 실행 대상은 [PR #34](https://github.com/inlight37-design/decision-model_lab/pull/34) head `437010678941afa768b8f36fa738dc4419626295`이며, 모델 응답은 이번 소스 수정 전에 받았다. 후속 기록·표시 수정 브랜치는 `codex/live-pilot-observation-20260924`이고 main을 대상으로 제안한다. PR #34는 관측 시 열린 상태였다.

## 실행과 결과

- 설치 확인: Linux-native Codex `0.156.1`, Python `3.12.3`, bubblewrap `0.9.0`. `codex login status`는 ChatGPT 로그인을 보고했다. 인증 파일 내용·계정 식별자는 기록하지 않았다.
- 기존 K46 manifest와 빈 입력 폴더 하나를 사용했다. `--check-cli`는 `eligible=true`, 판 `codex@8a0128d4c791`을 반환했다. C3 `failed`와 strict 정책은 변경하지 않았다.
- `--live-cli codex --model gpt-6-luna --allow-context-unverified --call-budget 1 --timeout 180`으로 별도 앱 원장을 사용했다. 브라우저에서 Codex만 선택해 `2+3`을 묻고 답 `5`를 받았다. 실제 모델 호출은 한 번이며 반복·추가 호출은 없었다.
- 원문 보고 `a1-draft-report/3`: `execution=real`, `state=accepted`, `status=ok`, `independence=unverified`. 실행이 공개됐고, `include_unverified` 정족수는 확인 0·미확인 1·산입 1로 충족했다. 독립 정족수 충족이 아니다.
- 입력 전달은 `complete`, CLI 종료 코드는 0, `interpret` 결과는 `ok=true`, 종료 경계는 `pid_namespace`, `tree_confirmed_empty=true`, 실행 시간은 5332 ms였다. 답이 나왔다는 사실만으로 수용 성공을 판정하지 않았다.
- 요청 모델은 `gpt-6-luna`지만 `reported_models=[]`, `model_match=null`이다. 요청 수락과 실제 제공 모델 확인을 구분한다. 보고의 합성은 `not_included`, 사실 검증은 `not_performed`다.

초기 준비에서 별도 WSL 호출 사이에 `/tmp`의 빈 입력 폴더가 사라져 서버 시작 전 경로 검사에 실패했다. 서버를 시작하는 같은 셸 안에서 **빈 입력 폴더만** 다시 만들어 해결했다. 이 준비 실패에는 모델 호출이나 원장 예약이 없었다. 사용 원장·예산을 초기화하지 않았다.

## 보고와 화면 정정

원문 보고 버튼을 눌렀지만 내장 브라우저의 다운로드 완료는 관측하지 못했다. 같은 실행의 인증된 읽기 전용 보고 API에서 JSON을 받아 로컬 `outputs/codex-live-pilot-report.json`에 저장하고 위 수용·독립성·정족수 필드를 읽었다. 원문에는 질문·초안과 실행 정보가 있으므로 저장소에는 올리지 않는다. 이 문서는 직접 읽은 결과에서 필요한 필드만 옮긴 요약이다.

공개된 답의 상세 행에 실제 독립성 값과 무관하게 “독립성 확인”이 표시되는 결함을 발견했다. `app/static/index.html`을 참여자의 저장된 `independence`에 따라 표시하도록 고쳤다. 같은 실행을 다시 조회했을 때 “문맥 미확인 · 독립 정족수에 세지 않음”으로 표시됐고 답·종료·입력·모델 정보가 보존됐다. 예약은 1/1, 사용 중 실행 자리는 0이었다. 이 화면 확인은 추가 모델 호출을 만들지 않았다.

표시 수정의 검증은 모델 없는 관련 회귀 시험과 inline JavaScript 구문 검사, 실제 `participantRow`의 최소 DOM 대조(미확인·확인·값 없음·수동)로 수행했다. WSL의 별도 venv에서 고정 `jsonschema==4.26.0`을 사용해 `DML_REQUIRE_BWRAP=1 python -m unittest discover -s tests -v`를 실행했고 완료 결과는 `OK`, Windows registry 전용 시험만 skip이었다. 인코딩·문서 무결성을 포함한 필수 로컬 검사도 성공했다. 정확한 head의 CI 결과는 후속 PR/Actions에서 확인하며 로컬 결과와 구분한다.

API로 다시 읽은 `live_call_budget`은 `used=1`, `cap=1`, 사용 중 자리와 미정리 시도는 모두 0이었다. 원문 보고의 프롬프트는 247바이트이고 SHA-256 `927fa6ed48b3f93b815800e2cd3118be9d0e8308450294416a429342ab9eb2a2`, 초안 `5`는 SHA-256 `ef2d127de37b942baad06145e54b0c619a1f22327b2ebbcfbec78f5564afe39d`로 재계산 일치했다. 로컬 보고 파일 자체의 SHA-256은 `fdfd38dc53880fbd2cf40e2d1553ee660f60300499cd3c2c4154bfe7012626ff`다. 해시 일치는 진실성이나 독립성을 입증하지 않는다.

## 남은 범위와 다음 단계

첫 단일 Codex 서버 경로의 입력·종료·수용·공개는 관측했다. C3 문맥 독립성, 인증·계정 문맥 전체의 안전 보장, 실제 제공 모델, 다른 provider, 복수 실제 CLI 동시 참여, 실제 합성·사실 검증은 확인하지 않았다. 빈 입력 폴더이므로 공통 자료 전달 검증도 아니다. 기존 네트워크·자원 상한의 한계는 그대로다.

승인된 단일 호출 상한은 소진됐다. 동일 원장을 보존하며 새 데이터 폴더·상한 증가·`observe.py approve` 재작성으로 추가 호출을 만들지 않는다. 다음 작업은 복수 참여 연결과 provider별 실행 조건·상한을 준비하는 것이다. 추가 실측과 사용량 비교에는 새 사용자 승인이 필요하다.
