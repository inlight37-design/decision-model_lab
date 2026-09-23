# V04-03 보조 스크립트

| 파일 | 하는 일 |
|---|---|
| [`conformance.py`](conformance.py) | 합성 파일(허용·금지·지시문 표식)로 읽기 전용 논의자 설정을 관측한다. [`core/`](../../core/README.md)의 runner·adapter로 실행한다. `setup`과 `codex-prompt-input`은 모델을 부르지 않고, `claude`·`codex`는 한 번씩 부른다 |

- 모델을 부르는 명령은 구독 사용량을 쓴다. 사용자 승인 뒤 한 번씩 실행하고 결과를 읽은 다음 넘어간다.
- 원 출력은 저장소 밖 `%TEMP%\v0403-conf\results\`에 남는다. 저장소에는 [요약](../../docs/experiments/v04-03-conformance/aux-pc.md)만 옮긴다.
- Windows 전용이다(레지스트리로 자식 환경을 만든다).
