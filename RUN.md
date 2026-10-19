# NextUp 로컬 실행 가이드

이 프로젝트에는 자동 테스트(pytest)가 없습니다. 앱을 띄워서 아래 데모 시나리오대로 직접 클릭해 보는 방식으로 테스트합니다.

## 0. 최초 세팅 (한 번만)

Python 3.11 이상이 필요합니다. macOS 기본 Python은 3.9라서 맞지 않습니다.

```bash
brew install python@3.12

cd next_up                  # 저장소를 clone한 폴더
/opt/homebrew/bin/python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env        # MONGODB_URI, LLM_* 값 채우기 (이미 있으면 생략)
python scripts/check_env.py # 4개 항목 모두 ✅ 이면 OK
```

`check_env.py`가 점검하는 항목은 MongoDB Atlas 연결, LLM 응답, LLM tool calling, 임베딩 모델입니다.

## 1. 데모 데이터 넣기

```bash
source .venv/bin/activate
python scripts/reset_demo.py
```

- 데모 컬렉션(volunteers, shifts, signups, approvals, messages, agent_log, agent_triggers, worker_state)을 **비운 뒤** 가짜 봉사자와 시프트 데이터를 새로 넣습니다.
- Atlas 벡터 인덱스도 이때 만들어집니다. 빌드에 1~2분 걸리지만, 그 사이에는 Python 코사인 유사도로 대신 계산하므로 바로 써도 됩니다.
- 데모를 처음 상태로 되돌리고 싶을 때도 이 명령을 다시 실행하면 됩니다.

## 2. 실행 (터미널 2개)

```bash
# 터미널 1: 워커 (취소 이벤트를 감지해서 에이전트를 실행)
source .venv/bin/activate
python worker.py
```

```bash
# 터미널 2: 웹 UI
source .venv/bin/activate
streamlit run app.py
```

브라우저에서 http://localhost:8501 이 열립니다.

> ⚠️ `worker.py`를 켜지 않으면 봉사자가 취소해도 에이전트가 반응하지 않습니다.

```bash
# (선택) 터미널 3: 이메일 발송 워커 — 코디네이터가 승인한 요청을 이메일로 보냄
source .venv/bin/activate
python notifier.py
```

> 기본값 `EMAIL_PROVIDER=console`은 실제로 보내지 않고 터미널에 로그만 찍습니다. 실제 발송은 `.env`에서 `smtp` 또는 `resend`로 바꾸고 `RESPONSE_LINK_SECRET`을 설정하세요. 데모 중에는 `EMAIL_REDIRECT_TO`로 모든 메일을 한 주소로 모을 수 있습니다.

## 3. 데모 시나리오

화면 왼쪽 사이드바에서 **Coordinator**와 **Volunteer** 화면을 전환합니다.

| # | 화면 | 할 일 | 기대 결과 |
|---|---|---|---|
| 1 | Volunteer (**Michael Brooks**) | **Saturday Delivery Run** 취소 | — |
| 2 | Coordinator | 기다리기 | 몇 초 안에 🚨 대체 인원 제안이 뜸. **🔍 Why?**를 열면 에이전트가 판단한 순서가 보임 |
| 3 | Coordinator | 초안 하나 수정 → 후보 2명 선택 → **Approve selected** | 승인 처리됨 |
| 4 | Volunteer (1번 후보) | 받은 요청에서 **Accept** | 토스트 알림 |
| 5 | Coordinator | 시프트 보드 확인 | Delivery Run이 🟢 filled, 활동 피드 갱신 |
| 6 | Coordinator | 에이전트에게 *"Need drivers for the Senior Grocery Delivery"* 입력 | 운전 가능한 사람만 제안됨 |
| 7 | Volunteer (**Priya Natarajan**) | Recommended 확인 | **Kids Reading Hour**가 맨 위 |

## 문제 해결

- **"No volunteers yet"**: 1단계 `reset_demo.py`를 실행하지 않은 상태입니다.
- **취소했는데 제안이 안 뜸**: 터미널 1에서 `worker.py`가 실행 중인지, 로그에 에러가 없는지 확인하세요.
- **`reset_demo.py`가 벡터 인덱스 생성에 실패함**: 출력된 JSON을 Atlas UI → Atlas Search → Create Search Index → JSON editor에 붙여 넣으세요.
- **연결 문제 전반**: `python scripts/check_env.py`로 어느 항목이 실패하는지 확인하세요.
