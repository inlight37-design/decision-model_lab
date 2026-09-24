# CLI 막힌 부분 수정·한계 재검토 — 2026-09-24

작성: ChatGPT 웹 세션. [PR #38](https://github.com/inlight37-design/decision-model_lab/pull/38), 브랜치 `chatgpt/cli-unblock-20260924`. 시작 main은 PR #37이 병합된 `16646b34a508f4fbe4fbbd1e00758eb8223a2d65`다. 사용자 요청은 남은 문제를 직접 수정하고 중간 커밋을 남기는 것이었다. main 병합은 하지 않았다.

## 결론과 현재 경계

호출 상한 저장, 시작 전 거절 회계, 독립성 화면 회귀 시험, provider별 입력·관측 기록, 동시 실행 연결은 구현했다. 계정 한도도 원천적으로 조회 불가능한 것이 아니므로, 공식 Codex 메타데이터 통로를 쓰는 별도 진단 도구를 구현했다. 실제 계정·모델을 부르지 않는 시험으로 검증했다.

**실제 모델 호출은 0회다. 사용자 PC/WSL 연결, Claude의 새 실행 권한 관측, 실제 Codex·Claude 동시 답변, 실제 계정 한도 조회는 수행하지 않았다.** 현재 웹 세션의 접근 한계를 과거 PC 세션의 성공 관측에 덮어쓰지 않는다. 사용자 PC 서버를 새로 띄우거나 기존 원장을 수정하지 않았다. 서버 종료는 이전 Claude의 관측이며 이번 세션이 포트를 재확인한 것은 아니다.

**PR은 아직 병합 준비 완료가 아니다.** 추가한 Windows CI에서 기존 인코딩 검사 도구가 한글 결과를 CP1252 출력에 쓰다 실패했다. 이를 고친 평문 [WINDOWS-CONSOLE.patch](WINDOWS-CONSOLE.patch)는 로컬에서 시험했지만 제품 파일에는 아직 적용되지 않았다. 직접 반영 요청이 도구의 보안 상태 판정 단계에서 두 번 차단돼 우회하지 않았다. 권한 있는 PC 세션이 패치를 검토·적용하고 정확한 head의 Windows·Linux CI를 확인한 뒤 PR을 준비 완료로 바꾼다. 파일 검사 자체를 끄거나 실패한 Windows job을 삭제하지 않는다.

## 1. 코드로 해결한 것

| 문제 | 변경과 검증 |
|---|---|
| 서버 재시작으로 호출 상한 증액 | `app/store.py` 스키마 6의 `live_budget`에 첫 전체·provider별 상한을 저장한다. 다른 값은 거절하고, 옵션을 생략해도 저장된 상한을 복원한다. 첫 호출 전에도 고정된다 |
| 구형 원장과 모순된 상한 | 기존 예약 사건의 같은 cap에서 복원한다. 서로 다른 cap이나 상한 초과 이력이면 추정하거나 원장을 덮어쓰지 않고 거절한다. 기존 사건·초안은 보존한다 |
| 예산 경쟁·provider 간 빌려 쓰기 | `controller.py`가 같은 거래에서 전체·provider 한도를 확인하고 예약한다. 한 provider의 여유를 다른 provider가 가져가지 않는다 |
| 부르지 않은 실행의 사용량 표시 | 카드의 실행/진행, 시작 전 종료, 실제 CLI 예약을 분리했다. 시작 전 거절은 실행 0으로 보이고, 시작 직전 예약 뒤 철회된 경우 예약만 남는다. 이미 시작된 실패·취소·UNKNOWN의 예약은 환불하지 않는다 |
| 독립성 오표시 재발 | `test_cli_unblock.py`가 실제 HTML의 JavaScript 함수를 Node로 실행한다. confirmed/unverified/누락/null/수동과 공개 전 초안 비노출을 시험한다 |
| Codex 입력 설정이 Claude 판을 변경 | `CliExecutor`가 provider별 입력 폴더와 inventory를 받는다. Codex의 빈 폴더 하나를 Claude에 전파하지 않아 Claude의 기존 자료 없음 판을 유지한다. 누락 inventory는 unchecked로 전환되지 않는다 |
| 서버당 실제 CLI 하나 | `live_config.py`와 `server.py`에 명시적 1–2 provider 설정, 전체·개별 상한, 두 실행 자리, 일괄 준비 조회를 연결했다. 기존 controller 스레드/거래/봉인 구조를 재사용한다. 별도 오케스트레이터·큐·SDK는 추가하지 않았다 |

새 runtime 의존성은 없다. JSON 설정은 잘못된 이름·중복 provider·불리언 상한·빈 모델 이름을 거절한다. 상대 경로는 설정 파일 기준이다. 기존 단일 `--live-cli`도 유지했다. 실제 실행 전에 정확한 판의 기존 허가와 시작 직전 재검사가 필요하며, 이 변경이 관측 기록을 자동 합격으로 만들지 않는다.

합성 동시 실행 시험은 두 작업을 모두 시작시킨 뒤 한쪽만 먼저 끝내도 초안이 공개되지 않음을 확인하고, 둘 다 끝난 뒤 함께 공개되는지 검사한다. 이것은 실제 공급자 두 곳의 성공·지연·구독 호환성 시험이 아니다.

## 2. ‘지금 구조로는 불가능’ 판단의 정정

### 계정 한도: 미구현이었으며 메타데이터 통로가 있다

[Codex 공식 app-server 문서](https://developers.openai.com/codex/app-server)의 `account/rateLimits/read`는 한도 창의 사용 비율과 초기화 시점을 제공한다. `account/read`는 인증 종류를 확인할 수 있다. 확인일: 2026-09-24. 이는 모든 ChatGPT 앱의 잔여 토큰·남은 질문 횟수를 보장하는 값은 아니다.

`tools/w2/codex_account.py`는 기존 `tools.review_boundary.quota_projection`을 재사용한다. 기본 실행은 프로세스를 시작하지 않는다. 명시적 `--probe`에서만 기존 Linux 격리 안의 Codex app-server를 띄워 정해진 메타데이터 메서드를 보낸다. 질문 시작, 로그인 변경, 추가 크레딧 요청, 유료 API 대체는 없다. 계정 이메일·요금제·인증 정보·원시 프로토콜은 출력하거나 저장하지 않는다. 시간·출력 크기를 제한하고 실패 시 종료/회수한다.

가짜 stdio 서버뿐 아니라 실제 bubblewrap 안에서 같은 helper를 실행했다. 이 과정에서 격리가 `PYTHONPATH`를 버리고 CI의 Python이 `/usr` 밖에 있을 수 있다는 결함을 잡아, `/usr/bin/python3`와 명시적 helper 검색 경로로 수정했다. **사용자 설치판에서 실제 quota 응답을 받는 검증과 제품 화면 연결은 남아 있다.** 미지원·거절·시간 초과는 unknown이지 잔여 0이 아니다.

### 실제 제공 모델: 관측 경로는 있으나 이번에 교체하지 않았다

같은 공식 문서의 `model/rerouted`는 요청이 다른 모델로 재지정되는 사건을 설명한다. 현재 exec 응답만으로 제공 모델을 알 수 없다는 한계와, 모든 공식 경로에서 불가능하다는 주장은 다르다. 다음 transport 검토에서 요청 이름·서비스 보고 이름·재지정 사건을 분리한다. 보고가 없으면 요청 이름으로 대신 채우지 않는다. app-server를 실제 논의자 transport로 바꾸는 것은 새 계획·권한·종료 검증을 요구하므로 메타데이터 도구를 몰래 논의자 실행기로 확대하지 않았다. 서비스 보고 역시 실제 모델 가중치의 외부 증명은 아니다.

### C3: 통제 가능한 개인 설정부터 줄이되 독립성을 거짓 확정하지 않는다

[Claude 공식 CLI 문서](https://code.claude.com/docs/en/cli-reference)의 `--safe-mode`는 일반 인증을 유지하면서 개인 지시문·자동 메모리·플러그인 등 사용자 정의 기능을 끄는 경로다. 관리 정책은 일부 계속 적용된다. `--bare`와 혼동하지 않는다. 확인일: 2026-09-24. 설치판 지원과 실제 적용은 별도 관측 대상이며 지금 검증된 argv에 옵션을 몰래 추가하지 않았다.

실용적 다음 순서는 설치판·로컬 설정·원격 연결 목록 대조, 별도 최소 프로필의 지원 여부 확인, 합성 표식 양성/음성 대조다. 표식이 나오면 누출 근거지만 나오지 않았다는 결과만으로 모든 개인 문맥의 부재를 증명하지는 못한다. 약 13.7K 입력 토큰만으로 그 안의 내용이나 개인 메모리 포함을 단정하지 않는다. 기존 C3 failed와 명시적 context-unverified 정책을 보존했고, 미확인 응답을 엄격한 독립 정족수에 넣지 않는다.

### Claude: ‘정상 답 1회면 전송·권한이 함께 열린다’는 설명은 잘못됐다

기존 `claude_preflight.py`의 assess도 정상 result JSON으로는 전송 증거만 평가한다고 명시한다. 이전 stream-json/Read/자료 있음 관측을 현재 json/도구 없음/자료 없음 판에 복사하면 안 된다. 이번 provider별 입력 분리는 이 판이 우연히 바뀌는 문제를 고쳤을 뿐, 권한 집행 증거를 새로 만든 것이 아니다.

PC 관측자는 먼저 정확한 판에서 권한을 입증할 증거 경로를 정해야 한다. 다른 진단 판의 init이나 모델 자기 보고를 현재 판의 권한 성공으로 올리지 않는다. 이를 충족한 inventory로 준비 조회를 통과한 뒤 실제 병렬 실험을 한다. 같은 짧은 질문을 반복해도 부족한 종류의 증거가 자동으로 생기지는 않는다. 수동 원본 앱 답도 사용자 확인만으로 독립성이 확인되지 않는다.

## 3. PC 세션의 다음 실행 절차

먼저 이 PR의 미적용 Windows 패치를 검토·적용한다. 기존 원장은 새 스키마로 열기 전에 백업한다. 추가 실험은 기존 소진 원장을 증액하는 대신 목적과 상한을 기록한 별도 원장을 사용한다. 사용자에게 기술적 선택을 다시 승인받기보다 이미 정한 구독·격리·상한 조건에서 진행한다.

1. **무모델 준비:** `python tools/w2/codex_account.py`로 조회 계획을 확인한다. 실제 계정 메타데이터를 볼 때만 `--probe --data-dir <controller 원장 폴더>`를 사용한다. 인증 값·전체 로그는 저장소로 옮기지 않는다.
2. **Claude 증거:** 기존 `tools/w2/claude_preflight.py`의 plan/preflight/assess를 사용해 현재 판과 진단 판을 분리한다. permission 관측 근거가 없는 채 manifest를 편집하지 않는다.
3. **동시 실행:** 아래처럼 provider별 실제 설치 모델 이름·관측 경로를 넣는다. 자리표시자를 실제 관측값으로 바꾸며 유효한 모델을 추측하지 않는다.

```json
{
  "providers": [
    {"adapter_id":"codex", "model":"<관측한 전체 모델 이름>",
     "inventory":"/절대/경로/codex-manifest.json", "input_dir":"/절대/경로/빈폴더", "call_budget":1},
    {"adapter_id":"claude-code", "model":"<관측한 전체 모델 이름>",
     "inventory":"/절대/경로/claude-manifest.json", "call_budget":1}
  ]
}
```

```bash
# 프로세스/서버/모델을 시작하지 않는 전체 준비 조회
python -m app.server --check-config /path/live.json --data-dir /path/new-ledger --allow-context-unverified
# 두 provider가 같은 계획으로 모두 eligible일 때만 서버 시작; 실제 질문은 화면에서 시작
python -m app.server --live-config /path/live.json --data-dir /path/new-ledger --allow-context-unverified --timeout 180
```

기존 Codex K46 호환 목적의 빈 폴더를 Claude에 추가하지 않는다. 자료가 생기면 공통 자료 스냅샷/해시 전달은 아직 구현되지 않았음을 고려하고 각 판을 다시 검토한다. 같은 비민감 질문의 초안을 서로 보지 않고 작성→공개→모의 대조하는 실험부터 한다. 실패·한도 도달·UNKNOWN에서 자동 재호출하지 않는다. 끝나면 작업 세션이 서버와 자손 종료를 확인하고 끈다.

사용량 비교에서는 예약 수, 실제 시작 여부, CLI 토큰, 계정 한도 창 변화를 따로 기록한다. 원본 앱/단일/교차 검토의 답 품질과 사용량을 함께 비교하되 토큰 수를 구독 차감률로 환산하지 않는다.

## 4. 검증·커밋 기록

제품 코드 검증 head: `2ac311136d63b757f4f9c2f4f6514ea7b81ce423`. [push CI run](https://github.com/inlight37-design/decision-model_lab/actions/runs/35994129824)에서 Python 3.12·3.13 모두 성공했고 `DML_REQUIRE_BWRAP=1`로 격리 시험을 필수 실행했다. Windows job은 위 출력 문제로 전체 시험 전에 실패했다. 이후 문서 head의 최신 결과는 PR의 Checks를 기준으로 확인한다. 모든 CI가 녹색이라고 주장하지 않는다.

웹 컨테이너의 해당 코드 의미와 대응하는 전체 시험은 Python 3.13.5/Node 22.16.0에서 442개 발견, 420개 실행, 22개 OS/격리 관련 건너뜀으로 성공했다. 컨테이너가 실행할 수 없는 격리 시험을 성공으로 세지 않았다. 일부 새 파일의 마지막 줄바꿈 차이로 로컬 git tree가 원격 tree와 완전히 같다는 주장은 하지 않으며 실제 원격 코드 검증은 위 CI가 기준이다. Windows 출력 패치의 추가 CP1252 회귀 시험도 로컬에서 통과했다.

화면 변이 M6: confirmed 판정을 CLI 전송 여부로 되돌렸더니 실제 JavaScript 시험이 실패했고 복구 뒤 통과했다. 전체 그래픽 브라우저/사용자 조작 시험과는 구분한다. 인코딩 검사·compile·diff 검사도 수행했다.

주요 중간 저장: `34ade75c4d8a314283396652ded9d5e6d2cbc614`(상한), `74aac44e111df531f058173557f6acd486773f60`(provider별 계획), `24564377ffd0660b22fe46cbde74edbd65b63884`(회계), `a86cba471232921de7fdf2b04f8338f686aa75cb`(서버 연결), `54d92002ccf19ed39f7427fc716c768a2351a5ed`(계정 진단), `31586e351b1b896aae9f2bf2fb26af3064b30171`(동시/설정 시험), 위 제품 검증 head(격리 helper·Windows CI·임시 workflow 제거). 전체 이력은 PR에 있다.

GitHub 코드 쓰기가 가능했던 동안 정상 connector commit을 사용했다. 최초 소스 전달용 workflow는 `contents: read`만 사용했고 제품 검증 head에서 삭제했다. 마지막 Windows 수정 요청이 차단된 뒤에는 평문 미적용 패치만 남겼고 봇이나 workflow에 대신 적용시키지 않았다. 계정·모델·권한 관측 실패를 성공으로 바꾸는 수정도 없다.
