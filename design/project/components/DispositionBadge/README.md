# DispositionBadge

주장 하나의 최종 처리를 나타내는 배지. checker가 정의한 네 값과 관측 실패 하나만 받는다.

`supported` `qualified` `rejected` `unresolved` 외의 값은 렌더링하지 않고 개발 중 오류를 던진다. 중간 상태를 임의로 만들면 `report` 검사와 화면이 갈라진다.

## 규칙

- **`unresolved`가 가장 큰 목소리다.** 나머지 셋보다 대비가 높고, 목록 정렬의 기본값에서 맨 위로 온다.
- **`rejected`에 경보색을 쓰지 않는다.** 반박은 해결된 상태다. `rejected-soft` 위의 `rejected`(slate)를 쓴다.
- **`supported`는 외부 검사가 통과한 주장에만.** `kind`가 `vote`나 `self_report`인 근거만으로 이 배지를 달 수 없다. 화면은 checker의 판정을 표시할 뿐 스스로 승격하지 않는다.
- **`unknown`은 파선이다.** 채운 배경을 주지 않는다. 배경을 채우면 나머지 넷과 같은 무게로 읽힌다.

## 소비자가 제공하는 것

`disposition` 문자열과, 선택적으로 해당 주장을 대상으로 기록된 검사 수. 배지는 자기 스스로 근거를 해석하지 않는다.

## 접근성

색만으로 구분하지 않는다. 각 배지는 글자를 함께 싣고, `unknown`은 파선이라는 형태 차이도 갖는다. 목록에서 `aria-label`에 disposition 이름을 그대로 넣는다.
