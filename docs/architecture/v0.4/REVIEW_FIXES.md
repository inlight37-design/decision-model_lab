# 외부 검토와 저장소 위생 보강 — 2026-09-22

기준 main: `c1605f90` ([PR #2](https://github.com/inlight37-design/decision-model_lab/pull/2) 병합 결과).
검토 성격: **외부 정적 검토 + 오프라인 재실행.** 실제 provider 연결·과금·권한 검증은 이번에도 없다.

이 문서는 [최종 검토](FINAL_REVIEW.md)와 [후속 근거 검토](EVIDENCE_FOLLOWUP.md) 다음에 오는 세 번째 검토 기록이다. 대상은 **근거의 내용이 아니라 저장소가 자기 주장을 유지하는 방식**이다. 새 설계 결정(D19 이상)을 만들지 않았고 F 원장에 새 항목을 추가하지 않았다.

## 1. 이번 검토가 다룬 문제

저장소의 규율은 "검증하지 않은 것을 검증했다고 적지 말라"인데, 그 규율을 저장소 자신에게 적용하는 장치가 부족했다.

| 문제 | 확인 방법 | 조치 |
|---|---|---|
| CI가 없어 71개 검사의 상태가 사람 기억에만 의존 | `.github/` 부재 확인, Actions 실행 0건 | push·PR마다 실행하는 워크플로 추가 |
| 의존성 미설치 환경에서 71개 중 26개가 traceback | 시스템 Python으로 재현 | 실패가 아니라 skip으로 표시 |
| 원장의 `limits`·`inspection`·`locator`가 무검사 | 필드 완전성 프로그램 감사 | 필수 필드 검사와 JSON Schema 추가 |
| F17/F18/F19에 날짜 필드 없음 | 24개 항목 날짜 필드 전수 확인 | v0.3의 동일 URL 항목에서 미러링 |
| 안내 문서의 원장 범위 표기가 F22–F24 추가를 못 따라감 | 문자열 회귀 검사 작성 | 수정 + 재발 방지 테스트 |
| 저장소 루트 밖에서 테스트 실행 시 import 실패 | 상위 디렉터리에서 재현 | `pyproject.toml`의 `pythonpath` |
| 문서에 고정한 code hash가 현재 코드와 불일치 | blob SHA-1 직접 계산 | 생성 도구로 대체 |

## 2. 검토 중 정정한 내 판단

외부 검토의 초기 지적 중 **두 건은 틀렸고**, 확인 과정에서 저장소 쪽이 옳았다. 기록해 둔다.

**(a) `published` 결측 8건은 결함이 아니다.** 살아 있는 제품 문서는 `revised`, 고정 commit의 코드는 `revision`(+`revision_date`)을 쓴다. 원장은 아는 만큼만 적는 원칙을 지키고 있었다. 실제 결함은 훨씬 좁았다 — **F17/F18/F19만 날짜 필드가 하나도 없었다.** 하필 이 셋은 `limits`에 "Recheck before implementation"이 적힌, 날짜가 가장 중요한 가변 공급자 문서다.

**(b) 날짜의 축소 정밀도도 결함이 아니다.** F09의 `"2025"`(학회 proceedings)와 F10의 `"2024-07"`(preprint)은 ISO 8601 축소 정밀도이며, 아는 것보다 정밀하게 적지 않은 올바른 처리다. 처음 작성한 스키마가 전체 날짜를 강요한 것이 잘못이었고, `published_date`를 별도 정의로 분리했다.

## 3. 변경 내역

### 새 파일

| 경로 | 역할 |
|---|---|
| [`.github/workflows/checks.yml`](../../../.github/workflows/checks.yml) | Python 3.12/3.13에서 전체 오프라인 검사 |
| [`contracts/sources.schema.json`](../../../contracts/sources.schema.json) | 근거 원장의 구조 계약 (v0.3/v0.4 별도 정의) |
| [`tools/validate_sources.py`](../../../tools/validate_sources.py) | 원장 스키마 검사기 |
| [`tools/print_code_hashes.py`](../../../tools/print_code_hashes.py) | 검사 코드의 현재 Git blob SHA-1 출력 |
| [`pyproject.toml`](../../../pyproject.toml) | 실행 경로 고정, pytest 호환 |
| [`.gitignore`](../../../.gitignore) | `__pycache__`·가상환경·raw trace 제외 |

### 수정

- [`tests/test_v02.py`](../../../tests/test_v02.py): jsonschema 의존 여부로 클래스를 분리. schema가 필요 없는 직렬화·중복 키 검사 2개는 의존성 없이도 계속 실행된다.
- [`tests/test_research_integrity.py`](../../../tests/test_research_integrity.py): 검사 3개 → 6개. 필수 필드, 날짜 필드, 안내 문서의 범위 표기, 원장–스키마 일치를 추가.
- [`sources.json`](sources.json): F17/F18/F19에 `published`와 `recheck` 추가. 값은 **URL이 동일한 v0.3 항목에서 그대로 가져왔다** — F17↔E02, F18↔E05, F19↔E08. 새로 추정한 값이 아니다.
- [`03-evaluation-and-roadmap.md`](03-evaluation-and-roadmap.md): V04-01 완료 조건에 구독 인증 경로의 정책 리스크 기록을 추가.
- [`../README.md`](../README.md): 버전 지도의 `F01–F21` → `F01–F24`.
- 루트 README, [v0.4 README](README.md), [HANDOFF](HANDOFF.md): 현재 검사 수와 새 도구 반영.

## 4. 실제로 실행한 검사

환경: Windows 11, Python 3.12.6, 저장소 밖 별도 가상환경, `jsonschema==4.26.0`.

```bash
python tools/check_frontier_protocol.py     # PASS
python tools/validate_design.py             # 25/25
python tools/validate_v02.py                # PASS
python tools/validate_sources.py            # 2개 원장 PASS (E 31 / F 24)
python -m unittest discover -s tests -v     # Ran 74 tests, OK
```

의존성 없는 시스템 Python에서도 `Ran 74 tests, OK (skipped=27)`를 확인했다. **수정 전에는 같은 조건에서 `FAILED (errors=26)`였다.**

CI 도입 전 이식성 사전 점검도 수행했다. Linux는 경로 대소문자를 구분하므로 Windows에서 통과한 링크 검사가 CI에서 깨질 수 있다. 상대 링크 **190개**를 대소문자 정확 일치로 재해석해 문제 0건을 확인했고, 코드 펜스 균형·전체 JSON 파싱·UTF-8 replacement 문자·CRLF/BOM도 함께 확인했다.

`74`는 unittest의 테스트 메서드 수다. 74개의 연구 주장이나 모델 호출이 아니다.

## 5. 이번에도 하지 않은 것

- 새 결정(D19+)을 만들지 않았다. 외부 조사에서 본 'Gemini CLI 소비자 인증 종료' 단서는 **원문 미확인이므로 원장에 등록하지 않았다.** 검증할 항목으로 V04-01 본문에만 남겼다.
- v0.4 원장 24개 중 F17/F18/F19를 제외한 21개에는 `recheck`를 채우지 않았다. `kind`로부터 기계적으로 유추할 수는 있으나, 그것은 원저자가 쓰지 않은 연구 메타데이터를 검토자가 만들어 넣는 일이다. **남은 작업으로 표시한다.** 스키마에서는 선택 필드로 정의해 두었다.
- v0.2 계약·fixture, frontier checker의 검증 로직, 근거의 내용과 해석은 변경하지 않았다.
- [FINAL_REVIEW](FINAL_REVIEW.md)와 [VALIDATION](VALIDATION.md) 1–4절의 숫자는 그 시점의 기록이므로 수정하지 않았다. 안내 문서의 범위 표기 회귀 검사도 commit SHA가 있는 줄은 이력으로 보고 건너뛴다.
- 실제 CLI 설치·로그인·모델 호출, 구독 과금, OS sandbox, 사용자 workload 품질은 여전히 미검증이다. [VALIDATION 5–6절](VALIDATION.md)의 범위가 그대로 유효하다.

## 6. 남은 작업

1. 원격에 push한 뒤 Actions 첫 실행이 녹색인지 확인한다. 확인 전에는 "CI가 통과한다"고 적지 않는다.
2. v0.4 원장 21개 항목의 `recheck` 값을 원저자가 채운다.
3. 저장소 description/topics 설정은 API 권한이 필요하므로 미적용이다.
4. 라이선스는 아직 뼈대 단계라는 판단으로 보류했다. **다만 이 저장소는 현재 비인증 접근이 가능한 공개 상태다.** 비공개로 의도했다면 GitHub 설정을 확인한다.
