# C3 합성 진단 재현

두 스크립트는 이 저장소의 `core.isolation.run()`을 쓴다. Linux/WSL에서 설치된 네이티브 Codex CLI와 root 소유 bubblewrap, `unshare`, Python 3가 필요하다. Windows exe를 대신 실행하지 않는다. 최초 기록은 Codex 0.156.1이며 재실행은 실제 설치판을 결과에 적는다.

저장소 루트에서 출력 폴더를 **저장소 밖**에 지정한다. 아래는 현재 셸의 임시 폴더를 쓰는 예다.

```bash
result_dir=$(mktemp -d /tmp/dml-c3-results-XXXXXX)
python3 docs/reviews/2026-09-24-cli-readiness/c3_prompt_probe.py --output-dir "$result_dir"
python3 docs/reviews/2026-09-24-cli-readiness/c3_appserver_probe.py --output-dir "$result_dir"
```

`--output-dir`은 필수이며 저장소 안의 경로는 거절한다. raw와 새 요약은 그 폴더에 생성된다. raw를 저장소에 복사하지 말고 검토한 개수·scope·표식 boolean·hash만 공유한다. tmp 경로 등이 달라 전체 출력 hash는 재실행마다 달라질 수 있다.

- CLI는 읽기 전용 release 폴더만 연결하고, HOME/config/AGENTS/skill/MCP는 임시 합성 자료로 만든다. 실제 인증 폴더나 계정 설정을 연결하지 않는다.
- 바깥 `isolation.run()` 안에서 별도 user/network namespace를 만들며 외부 네트워크 통신이 불가능하다. 이 경계가 실패하면 진단 결과를 성공으로 쓰지 않는다.
- prompt 스크립트는 로컬 입력 렌더링과 MCP 설정 목록만 읽는다. app-server 스크립트는 initialize 후 목록 RPC 세 개만 보내며 thread/turn/login/tool call은 없다.
- app-server의 각 응답 대기는 20초다. 종료 시 stdin을 닫고 필요하면 종료 신호로 정리하며 전체 자손 종료 확인을 기록한다.

[가린 prompt 결과](c3-prompt-results.json), [가린 app-server 결과](c3-appserver-results.json)는 이번 실행의 정적 증거다. [선택 help](c3-help-selected.json)와 [schema 발췌](c3-schema-excerpts.json)는 설치판에서 읽은 지원 근거이며 전체 schema 검증기로 배포하는 파일은 아니다. 실제 exec의 최종 모델 요청 또는 문맥 독립성의 증명으로 해석하지 않는다.

