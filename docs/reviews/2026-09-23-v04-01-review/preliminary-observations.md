# 원 출력 선검토 메모

검토 기준: `47934759c5d59cc5940aeb32687d00de25e57180`, 2026-09-23.
작성 시점: tier2의 모든 txt와 help의 모든 txt를 읽은 뒤, runtime_inventory/절차서/RESULTS/manifest.tier2 상세를 읽기 전. 최종 검토는 이 폴더의 README에 남긴다.

방법상 한계: NEXT-SESSION.md에서 2절 위치를 찾으려고 1–75줄을 요청했을 때 1절의 요약 판정까지 함께 반환되었다. 따라서 완전한 맹검 독립 판정이라고 주장하지 않는다. 요청서 자체에도 비교 대상 결론과 P4b 잔여 항목이 제시되어 있다. 아래는 원 출력에서 확인 가능한 사실을 별도로 고정한 메모이며 기존 RESULTS 상세와의 대조 전 작성했다.

- P1: Claude, Codex, agy가 명시한 호출에서 exit 0과 OK를 반환했다. Claude만 모델/firstParty/modelUsage를 출력한다. Codex/agy 결과에는 선택/실행 모델 식별자가 없다. 이 출력만으로 구독 청구 경로 또는 계정 전체 상태를 독립 검증하지 못한다.
- P2: Claude --bare는 exit 1, is_error=true, API 호출량 0, 로그인 요구를 반환한다. subtype=success이므로 subtype만 판정하는 adapter는 오류를 성공으로 분류할 수 있다.
- P3: Claude의 잘못된 permission-mode와 Codex의 잘못된 sandbox 값은 실행 전 거절된다. agy의 output-format=notaformat은 exit 0/OK 텍스트를 반환한다. 다른 옵션 값의 처리 또는 모델 fallback은 아직 관측하지 않았다.
- P3b: 세 CLI 모두 잘못된 옵션 이름을 거절한다. 이름 오타 거절과 값 유효성은 별도다.
- P4/P4b: Claude 파일은 원 stream이 아닌 작성 세션의 요약이다. P4b 요약상 tools/MCP/skills/slash_commands=0, plugins=2, agents=5. 정책/시스템 프롬프트/메모리/플러그인 본문 또는 peer 정보가 없다는 부정 명제는 이 요약과 OK 응답으로 입증되지 않는다. 잔여 기본 agent/plugin의 존재만으로 실제 오염을 단정할 수도 없다.
- Claude help: restricted는 user/project/local settings를 무시하지만 managed settings 및 --settings를 남긴다. safe-mode는 CLAUDE.md·customizations를 더 넓게 끄되 auth와 built-in plugins/tools는 남긴다고 명시된다. 이 조합의 실제 동작은 추가 검증 대상이다.
- P4 Codex: --ignore-user-config --ignore-rules 후 호출 성공. help는 후자를 execpolicy .rules에 한정하며 AGENTS.md/기억/모든 문맥 제외를 약속하지 않는다. P4에는 --sandbox read-only/--model 명시가 없다.
- P5: agy models는 선택 가능한 ID 목록을 반환한다. 목록에 나온 모델의 실제 호출 성공 및 기본 Flash 사용은 이 파일만으로 입증되지 않는다.
- help: 세 제품의 읽은 top-level/exec help에 ACP 표기는 없고 exec/print가 존재한다. 모든 제품·bridge에서 ACP가 불가능하다는 증거는 아니다. 현 단계 exec 우선을 뒤집을 관측은 없다.

예비 판정: Claude/Codex exec adapter 골격과 오프라인 검증은 진행할 근거가 있다. 실제 blind 운영 준비 완료와 동의어는 아니다. Antigravity는 옵션 값·모델 식별·권한 격리의 추가 검증이 필요하며 약관은 공식 원문 확인 전 보류한다.
