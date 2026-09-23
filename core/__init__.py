"""V04-03 실행 코어. 표준 라이브러리만 쓴다.

runner: native CLI 한 번을 셸 없이 실행하고, 끝났는지 확인한 만큼만 말한다.
adapters: CLI별 argv 조립·옵션 검증·출력 해석·자식 환경.
membership: 실행 중 참여자 구성이 바뀔 때의 결정.

모델 품질, 인증의 정당성, 권한 제한이 실제로 지켜지는지는 이 패키지가 판정하지 않는다.
그것은 V04-03 conformance 관측이 정한다. 절차: NEXT-SESSION.md 4절.
"""
