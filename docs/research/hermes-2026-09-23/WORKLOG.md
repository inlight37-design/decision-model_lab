# Hermes 패턴 선별 조사 — 작업 기록

날짜: 2026-09-23 (Asia/Seoul). 작성: ChatGPT 웹 세션.

## 조사 요청과 범위

사용자는 `NousResearch/hermes-agent`에서 우리 프로젝트가 가져올 만한 것을 꼼꼼하게 분석하고 GitHub에 문서로 남기도록 요청했다. 이 작업은 조사·설계 제안이며 Hermes 설치, 사용자 PC 변경, 실제 모델 호출, provider 추가, main 직접 변경은 하지 않는다.

## 고정한 판본

- 우리 저장소 시작점: `0865e3d9493c36921e94c01ad9f6c803a6d78363` (`main`).
- Hermes 관측 시작점: `c0d7294769a38c17ceae51d8f7995e66e1dcae27` (`main`, commit 시각 2026-09-23T04:02:02Z).
- 조사 브랜치: `chatgpt/hermes-patterns-20260923`.
- 시작 시 열린 PR 목록은 비어 있었다. 원격 브랜치에는 병합된 과거 작업 브랜치가 남아 있었다. 목록과 `NEXT-SESSION.md`를 확인했다.

## 유지할 전제

한 제품을 통째로 채택하지 않는다. Python 코어·native 구독 CLI·exec 우선, 유료 API 자동 전환 금지, 구성 축소 명시, blind 첫 초안·읽기 전용 논의자·단일 writer·미합의 보존을 유지한다. 사용자의 보조 PC 기록은 이번 세션의 관측으로 재분류하지 않는다.

## 접근 및 검증 범위

GitHub 커넥터로 원문과 고정 commit의 파일을 읽으며 공개 공식 문서도 대조한다. 웹 컨테이너의 일반 Git clone은 DNS 접근 실패로 실행되지 않았다. 사용자의 PC·설치 CLI·인증·구독 잔량은 이번 세션에서 관측하지 않는다. 원격 소스 정적 검토와 실제 실행 검증을 구분한다.

## 진행 기록

### 체크포인트 1 — 방향과 판본 고정

`README.md`, `NEXT-SESSION.md`, `AGENTS.md`, `docs/COLLABORATION.md`, 원격 브랜치와 열린 PR, Hermes README와 architecture 문서를 확인했다. Hermes는 자체 AIAgent 런타임이며 native CLI를 보존하는 우리 controller와 동일한 계층으로 간주하면 안 된다. 스킬·메모리·세션·권한·도구·비용·복구를 나누어 코드와 문서를 더 확인한다.

## 다음 작업

Hermes 하위 시스템의 실제 코드와 우리 설계의 접점을 대조한다. 기능별 채택/변형/보류 판정, 출처·검토 범위, 보안·과금·독립성 위험, 적용 순서와 검증 조건을 문서화한다. 같은 PR에서 인계와 탐색 링크를 갱신하고 GitHub Actions 결과를 확인한다. 병합은 수행하지 않는다.
