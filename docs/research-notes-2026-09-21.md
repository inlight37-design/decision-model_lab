# 2026-09-21 — Jev 및 공개 decision-model 구현 조사

> 상태: 자료 정리 초안  
> 작성 기준일: 2026-09-21  
> 목적: Jev 및 유사한 공개 decision-model / System-One 구현의 현재 공개 정보를 출처 중심으로 기록

이 문서는 특정 모델이나 접근법을 추천하거나 우열을 결론내리기 위한 문서가 아니다. 프로젝트가 직접 발표한 성능 수치는 가능한 한 **자체 보고(self-reported)** 로 표시했으며, 하드웨어·데이터셋·프롬프트·실행 방식이 다른 수치를 직접 비교하지 않는다.

---

## 1. TypeSafe AI Jev

TypeSafe AI는 2026년 9월 15일 Jev를 자사의 첫 **System One Model**로 공개했다.

공식 소개에 따르면 Jev는 일반적인 텍스트 생성 대신, 비정형 상태(state)를 입력받아 소프트웨어가 직접 사용할 수 있는 **typed probabilistic decisions**를 반환하는 것을 목표로 한다. TypeSafe는 새로운 모델 아키텍처, 병렬 sampler, 그리고 **RLCD (Reinforcement Learning for Calibrated Decisions)** 라고 부르는 학습 방식을 사용했다고 설명한다.

TypeSafe가 공개한 설명에서 Jev는 생성형 LLM과 달리 문자열 출력을 주목적으로 하지 않으며, 빠른 구조화 판단을 주요 용도로 제시한다.

### 확인된 공개 인터페이스

공개 SDK와 관련 프로젝트들이 사용하는 Jev의 System One API는 대체로 다음 형태를 가진다.

- 공통 `state`
- 여러 개의 typed question
- 질문 유형
  - `choice`
  - `score`
  - `noul` (yes/no probability)
- 선택 결과뿐 아니라 후보별 확률 또는 점수 정보 반환

Jev 내부 파라미터 수, 실제 모델 구조, 전체 학습 데이터 및 RLCD의 상세 학습 절차는 현재 공개된 공식 소개만으로는 재현할 수 있는 수준으로 공개되어 있지 않다.

### 출처

- TypeSafe AI — Introducing System One Models & Jev  
  https://typesafe.ai/blog/introducing-system-one-models-and-jev
- TypeSafe AI  
  https://typesafe.ai/
- TypeSafe Console / Docs  
  https://console.typesafe.ai/  
  https://docs.typesafe.ai/

---

## 2. Laya

Laya는 Jev와 유사한 typed-decision 인터페이스를 목표로 하는 공개 프로젝트다.

프로젝트 README 기준:

- 텍스트를 생성하지 않고 한 번의 forward pass에서 판단 결과를 반환
- `choice`, `score`, `noul` 지원
- 세 가지 공개 checkpoint
  - `laya`: ModernBERT-large, 421M parameters
  - `laya-multilingual`: mmBERT-base, 322M parameters
  - `laya-typed-decisions`: ModernBERT-large, 421M parameters
- 영어 및 다국어 모델 제공
- Hugging Face를 통해 모델 가중치 제공

프로젝트는 Tesla T4에서 자체 측정한 속도를 공개한다.

### 프로젝트 자체 보고 속도

| questions per call | laya | laya-multilingual |
|---:|---:|---:|
| 1 | 39.5 ms | 32.8 ms |
| 5 | 84.5 ms | 40.1 ms |
| 10 | 158.6 ms | 72.3 ms |
| 50 | 771 ms | 337 ms |

위 수치는 Laya 프로젝트의 자체 벤치마크이며 Jev API 또는 다른 모델의 동일 조건 측정값이 아니다.

### 출처

- GitHub — NandhaKishorM/laya  
  https://github.com/NandhaKishorM/laya
- README  
  https://github.com/NandhaKishorM/laya/blob/main/README.md

---

## 3. Kev

Kev는 Jared Palmer가 공개한 **Jev-inspired decision model** 프로젝트다.

현재 공개된 `kev-0.5b` 모델 카드 기준:

- base model: `Qwen/Qwen2.5-0.5B`
- backbone은 frozen
- LoRA adapter + small pointer/readout head
- 한 문서(state)와 여러 typed question을 한 번의 forward pass에서 처리
- decoding 없이 각 질문의 probability distribution 반환
- TypeSafe의 공개 `/v1/systemone` API contract와 호환되는 서버 제공
- Apache-2.0

프로젝트 설명에 따르면 각 질문은 block-causal mask를 통해 동일 state를 공유하되 다른 질문 branch를 보지 않도록 구성하고, `<decide>` 및 option 위치의 hidden representation을 pointer head가 점수화한다.

### 프로젝트 자체 보고 수치 — kev-0.5b

모델 카드의 mixed held-out split(1,350 questions) 기준:

- accuracy: 0.799
- ECE (10 bins): 0.065
- temperature scaling 후 ECE: 0.031

프로젝트는 해당 checkpoint를 **research prototype**이라고 명시한다.

### 출처

- GitHub — jaredpalmer/kev  
  https://github.com/jaredpalmer/kev
- Model card  
  https://github.com/jaredpalmer/kev/blob/main/MODEL_CARD.md
- 4B research preview  
  https://github.com/jaredpalmer/kev/blob/main/docs/model-cards/kev-4b.md

---

## 4. NanoJev

NanoJev는 Qwen3-0.6B를 기반으로 한 공개 decision-model 연구 프로젝트다.

프로젝트 README 기준:

- 0.6B 규모
- state + question + candidate set 입력
- complete probability distribution 출력
- output-token decoding 없음
- shared decision heads 사용
- choice / boolean / score 형태 지원
- 모델, 데이터셋, 학습 및 평가 파이프라인 공개

README에는 maze, Snake 등 게임 환경을 이용한 controller 평가가 포함되어 있다.

### 프로젝트 자체 보고 예시

초기 40-map navigation benchmark:

| system | 4×4 test | 6×6 OOD |
|---|---:|---:|
| NanoJev | 19/20 | 18/20 |
| Jev | 20/20 | 19/20 |
| Untuned Qwen3-0.6B | 7/20 | 3/20 |

이 표는 NanoJev 프로젝트의 특정 navigation benchmark 결과이며 범용 decision task 전체의 성능 비교를 의미하지 않는다.

### 출처

- GitHub — TianyuCodings/NanoJev  
  https://github.com/TianyuCodings/NanoJev
- Hugging Face model repository는 프로젝트 README에서 연결됨

---

## 5. OpenThai-SystemOne

OpenThai 팀은 2026년 9월 20일 **OpenThai-SystemOne**을 공개했다.

공식 발표 및 모델 카드 기준:

- 0.8B parameters
- Thai + English
- Qwen3.5-0.8B 기반
- 약 5B Thai tokens로 continued pretraining했다고 프로젝트가 설명
- 기존 LM head 대신 `256-slot decision head` 사용
- state + typed questions를 입력해 한 번의 forward pass에서 probability 기반 결과 반환
- `choice`, `score`, yes/no 계열 지원
- Apache-2.0
- weights, training scripts, configs, synthetic data 공개
- TypeSafe의 `POST /v1/systemone` 형태와 호환되는 API contract 제공

### 프로젝트 자체 보고 벤치마크

OpenThai 공식 발표에 따르면 Bespoke Nimble에서 사용한 13-subset public benchmark에 대해 다음 값을 보고했다.

- OpenThai-SystemOne 0.8B: 61.9
- Bespoke Nimble 9B: 74.8
- Jev: 76.0
- raw Qwen3.5-0.8B: 45.4

또한 Thai task에 대해 intent 86.4%, news topic 97.7%, XNLI-th 76.5%를 보고한다.

이 값들은 OpenThai 프로젝트가 공개한 자체 평가 결과다.

### 출처

- OpenThai 공식 발표  
  https://openthai.ai/en/openthai-systemone
- Hugging Face  
  https://huggingface.co/iapp/OpenThai-SystemOne
- GitHub는 공식 발표 페이지에서 연결됨

---

## 6. Bespoke Nimble

Bespoke Labs의 Nimble은 공개 모델과 학습 recipe를 사용해 Jev 형태의 typed decision을 구현하는 프로젝트다.

프로젝트 README 기준:

- text + schema를 입력
- choice 또는 true/false 질문 처리
- 각 허용 답안의 probability 반환
- reasoning text를 먼저 생성하지 않고 decision을 한 단계로 수행
- Jev에서 distillation하지 않았다고 명시
- Bespoke-Nimble-9B를 Apple Silicon 또는 NVIDIA GPU에서 실행 가능
- 학습 데이터 구성, 학습 recipe, serving 및 evaluation 코드 공개

### 프로젝트 자체 보고 benchmark

324개의 synthetic reference example에 대해 README가 보고한 주요 결과:

- Jev 1.13.0: 302/324 = 93.21%
- Bespoke-Nimble-9B는 Jev보다 10개 적은 reference label을 맞췄다고 프로젝트가 기록
- reference label은 synthetic
- 162개의 closely-related pair
- 6개 source family만 사용한 narrow test라고 프로젝트 스스로 명시

### 프로젝트 자체 보고 latency

README의 측정 조건이 서로 다르므로 아래는 동일 하드웨어 비교표가 아니다.

| model / runtime | median |
|---|---:|
| Gemma 3 270M IT, H100 | 21.8 ms |
| Qwen3.5-0.8B, H100 | 48.6 ms |
| Qwen3.5-4B, H100 | 58.0 ms |
| Qwen3.5-9B, H100 | 58.1 ms |
| Bespoke-Nimble-9B, H100, 120-sample subset | 106.0 ms |
| Bespoke-Nimble-9B, M5 Pro 64GB | 444.0 ms |
| Jev 1.13.0, TypeSafe API | 246.7 ms |

프로젝트가 직접 명시하듯 local model과 remote API, 그리고 일부 row의 sample count가 다르므로 latency 숫자는 실행 조건과 함께 보존해야 한다.

### 출처

- GitHub — bespokelabsai/nimble  
  https://github.com/bespokelabsai/nimble

---

## 7. SemIf — formerly OpenJev

`TheoLeeCJ/SemIf`는 처음에 OpenJev라는 이름을 사용하다가 **SemIf**로 이름을 변경한 독립 프로젝트다.

> 주의: 아래의 `razorback16/openjev`와 별개의 프로젝트다.

프로젝트 README 기준:

- 기존 open model에서 typed option probability를 직접 읽는 baseline
- answer sentence 또는 JSON을 생성하지 않고 candidate score를 직접 사용
- Qwen3.5-4B, MiniCPM5 2B 등 공개 모델을 이용한 실험
- CUDA 환경 및 Apple Silicon MLX backend 지원
- 동일 state를 여러 판단에서 공유할 경우 shared-state prefill 방식 제공
- MIT license

SemIf는 Jev의 비공개 내부 모델이나 학습 방식을 재현한다고 주장하지 않으며, **Jev의 interface pattern을 open model로 구현하는 독립 연구**라고 명시한다.

### 출처

- GitHub — TheoLeeCJ/SemIf  
  https://github.com/TheoLeeCJ/SemIf

---

## 8. DiffusionGemma

DiffusionGemma는 Google DeepMind가 2026년 6월 공개한 experimental open-weights generative model이다.

Google 공식 자료 기준:

- Gemma 4 계열 기반
- 26B Mixture of Experts
- inference 시 약 3.8B active parameters
- discrete text diffusion
- token-by-token autoregression 대신 block-autoregressive / multi-canvas sampling
- bidirectional context 사용
- Apache 2.0
- multimodal input
- vLLM, Hugging Face Transformers, SGLang, MLX 등 지원

Google은 quantized deployment가 18GB VRAM 범위에서도 가능하다고 설명한다. 한편 vLLM 공식 recipe의 현재 hardware guidance는 NVFP4 variant에 대해 24GB minimum을 표기한다. 두 수치는 모델 자체의 압축 가능성과 특정 serving stack의 실행 메모리 요구량이 다를 수 있음을 보여주므로 각각의 출처 조건을 유지해야 한다.

### 출처

- Google Developers Blog — DiffusionGemma: The Developer Guide  
  https://developers.googleblog.com/diffusiongemma-the-developer-guide/
- Google launch post  
  https://blog.google/innovation-and-ai/technology/developers-tools/diffusion-gemma-faster-text-generation/
- Google AI model card  
  https://ai.google.dev/gemma/docs/diffusiongemma/model_card
- vLLM recipe  
  https://github.com/vllm-project/recipes/blob/main/models/Google/diffusiongemma-26B-A4B-it.yaml

---

## 9. DiffusionGemma를 Jev 형태로 사용하는 구현

### 9.1 razorback16/openjev

`razorback16/openjev`는 DiffusionGemma 26B-A4B와 vLLM을 이용해 Jev-compatible System One API를 제공하는 공개 프로젝트다.

프로젝트 README 기준:

- `POST /v1/systemone`
- state + yes/no / choice / score 질문
- generated text를 parsing하지 않고 모델 확률에서 답을 읽는 방식
- TypeSafe SDK와 호환되는 wire API 제공
- 동일하게 로드된 DiffusionGemma를 `/v1/chat/completions`의 일반 생성에도 사용 가능
- 이미지 기반 질문도 지원한다고 프로젝트가 설명
- Apache-2.0

현재 구현은 upstream vLLM에 아직 merge되지 않은 `vllm-project/vllm#57250` 계열 patch에 의존한다고 README가 명시한다.

따라서 이 프로젝트는 **Jev의 미공개 내부 아키텍처를 증명하는 자료가 아니라, DiffusionGemma에서 structured probability read를 사용해 Jev와 유사한 API 동작을 구현한 프로젝트**로 구분해야 한다.

### 출처

- GitHub — razorback16/openjev  
  https://github.com/razorback16/openjev
- README  
  https://github.com/razorback16/openjev/blob/main/README.md

### 9.2 mmastrac/djev-spark

`djev-spark`는 DiffusionGemma 26B-A4B NVFP4를 DGX Spark에서 실행하고, Jev의 `POST /v1/systemone` 형태로 structured decisions를 제공하는 container recipe다.

README 기준:

- DGX Spark / GB10 환경을 주 대상으로 함
- patched vLLM structured-read engine 사용
- vLLM port 8010
- structured decision server port 8011
- NVIDIA NVFP4 checkpoint
- image 약 25 GB, checkpoint 약 18 GB라고 기록
- vLLM PR #57250 기반 patch 사용

### 출처

- GitHub — mmastrac/djev-spark  
  https://github.com/mmastrac/djev-spark
- README  
  https://github.com/mmastrac/djev-spark/blob/main/README.md

---

## 10. JevBench

`fstandhartinger/jevbench`는 Jev 계열 typed decision model을 비교하기 위해 공개된 독립 benchmark 프로젝트다.

현재 README에는 capability, cost, latency, reliability 등을 측정하는 benchmark 세트가 있으며, 최신 결과군에 다음과 같은 공개 구현이 포함되어 있다고 명시한다.

- OpenJev / DiffusionGemma 26B-A4B
- SemIf / Qwen3.5-4B
- open-alternative-jev
- system-one / Qwen3-8B
- Bespoke Nimble 9B
- Jev

해당 benchmark는 각 프로젝트의 저자 serving 방식 또는 remote endpoint를 사용하기도 하므로, 결과를 읽을 때 실행 위치 및 네트워크 조건을 같이 확인할 필요가 있다.

### 출처

- GitHub — fstandhartinger/jevbench  
  https://github.com/fstandhartinger/jevbench

---

## 11. 현재 공개 구현들의 구조적 분류

아래 분류는 각 프로젝트 README에 공개된 구현 방식만 정리한 것이다.

| 프로젝트 | 공개된 방식 | text decoding |
|---|---|---|
| Jev | TypeSafe 전용 System One model; 내부 세부 구조 비공개 | 일반 prose generation이 목적이 아님 |
| Laya | ModernBERT / mmBERT encoder + typed decision output | 없음 |
| Kev | Qwen backbone + LoRA + pointer/readout head | 없음 |
| NanoJev | Qwen3-0.6B backbone + shared decision heads | 없음 |
| OpenThai-SystemOne | Qwen3.5-0.8B 계열 + 256-slot decision head | 없음 |
| Bespoke Nimble | 공개 LLM을 typed-decision용으로 학습/score | reasoning text 생성 없이 decision |
| SemIf | 기존 open model의 candidate probability 직접 scoring | answer text decoding 없음 |
| OpenJev (razorback16) | DiffusionGemma structured probability read | decision path에서는 text 생성 없음 |
| djev-spark | DiffusionGemma + patched vLLM structured reads | decision path에서는 text 생성 없음 |

이 표는 성능 순위가 아니라 **현재 각 프로젝트가 공개한 구현 방식의 분류**다.

---

## 12. 아직 단정할 수 없는 항목

현재 공개 자료만으로 다음 사항은 확정하지 않는다.

1. Jev의 실제 parameter count와 내부 network architecture
2. Jev의 RLCD 상세 알고리즘과 공개 구현들의 학습법이 어느 정도 동일한지
3. 서로 다른 프로젝트의 benchmark 숫자를 동일 조건의 성능 순위로 해석할 수 있는지
4. 각 구현이 실제 장시간 production agent loop에서 갖는 안정성
5. calibration 수치가 서로 다른 task/domain에서 유지되는지
6. DiffusionGemma structured-read 구현이 Jev 내부 방식과 유사한지 여부

공개 구현들이 Jev와 **API/행동 패턴을 재현하는 것**과, Jev의 **실제 내부 구조를 재현하는 것**은 구분해서 기록한다.

---

## 13. 원문 링크 모음

### Jev / TypeSafe

- https://typesafe.ai/blog/introducing-system-one-models-and-jev
- https://typesafe.ai/
- https://docs.typesafe.ai/
- https://console.typesafe.ai/

### 공개 decision-model 프로젝트

- https://github.com/NandhaKishorM/laya
- https://github.com/jaredpalmer/kev
- https://github.com/TianyuCodings/NanoJev
- https://openthai.ai/en/openthai-systemone
- https://huggingface.co/iapp/OpenThai-SystemOne
- https://github.com/bespokelabsai/nimble
- https://github.com/TheoLeeCJ/SemIf

### DiffusionGemma / structured reads

- https://developers.googleblog.com/diffusiongemma-the-developer-guide/
- https://ai.google.dev/gemma/docs/diffusiongemma/model_card
- https://github.com/razorback16/openjev
- https://github.com/mmastrac/djev-spark
- https://github.com/fstandhartinger/jevbench

---

## 14. 변경 기록

- 2026-09-21: 최초 조사 노트 작성
