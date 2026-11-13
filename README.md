# travel-info MCP 서버

환율, 날씨, 여행 환경 분석 도구를 제공하는 MCP 서버입니다. [FastMCP](https://github.com/jlowin/fastmcp)로 만들었습니다.
Claude Code나 Claude Desktop 같은 MCP 클라이언트에 연결하면 "도쿄 날씨 어때?", "100달러 원화로 얼마야?", "다음 주 오사카 여행 괜찮을까?" 같은 질문에 실시간 데이터로 답할 수 있습니다.

- API 키가 필요 없습니다. 무료 공개 API만 사용합니다.
- 통화는 `USD`, `JPY` 같은 ISO 코드나 `미국`, `엔화`, `유로` 같은 한국어/영어 이름으로 입력할 수 있습니다.
- 장소는 `서울`, `도쿄`, `Paris`처럼 도시명이나 국가명으로 입력합니다.

## 제공 도구

| 도구 | 설명 | 주요 인자 |
| --- | --- | --- |
| `get_exchange_rate` | 환율 조회 및 금액 환산 | `base` (기본 `USD`), `target` (생략 시 주요 통화 목록), `amount` (기본 `1`) |
| `get_weather` | 현재 날씨와 일별 예보 | `location`, `days` (1~16, 기본 `3`) |
| `analyze_travel_condition` | 날씨와 환율을 묶어 여행 환경을 종합 분석 | `destination`, `home_currency` (기본 `KRW`), `days` (1~16, 기본 `5`), `budget` (선택) |

### `analyze_travel_condition` 분석 방식

- **날씨 점수**: 하루를 100점에서 시작해 기온(너무 춥거나 더움), 강수확률, 바람, 뇌우, 강한 비나 눈에 따라 감점합니다. 점수에 따라 `매우 좋음`(85+), `좋음`(70+), `보통`(50+), `나쁨`(30+), `매우 나쁨`으로 등급을 매깁니다.
- **준비물 팁**: 비, 추위, 더위, 큰 일교차, 강한 자외선, 강풍 예보에 맞춰 팁을 줍니다.
- **환율**: 목적지 국가의 통화를 자동으로 판별해 본인 통화와의 환율과 환산 예시를 보여 줍니다. `budget`을 넣으면 현지 통화 기준 총액과 하루 예산도 계산합니다.
- **종합 요약**: 평균 점수, 가장 좋은 날과 나쁜 날, 환율을 한 문장으로 정리합니다.

> 환율 API는 현재 시세만 제공하므로 과거 대비 유불리는 판단하지 않습니다. 실제 환전할 때는 은행이나 카드 수수료가 추가됩니다.

## 설치

Python 3.10 이상이 필요합니다.

```bash
git clone https://github.com/chaejh1009/modulab_mcp_example.git
cd modulab_mcp_example
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

[uv](https://docs.astral.sh/uv/)를 쓴다면 아래처럼 설치해도 됩니다.

```bash
uv venv .venv && uv pip install -p .venv/bin/python -r requirements.txt
```

## 실행과 연결

### 방법 1: stdio로 연결 (권장)

클라이언트가 서버 프로세스를 직접 띄우므로 따로 실행해 둘 필요가 없습니다.

**Claude Code**

```bash
claude mcp add travel-info -- /절대경로/modulab_mcp_example/.venv/bin/python /절대경로/modulab_mcp_example/server.py
```

**Claude Desktop**: `claude_desktop_config.json`에 다음을 추가합니다.

```json
{
  "mcpServers": {
    "travel-info": {
      "command": "/절대경로/modulab_mcp_example/.venv/bin/python",
      "args": ["/절대경로/modulab_mcp_example/server.py"]
    }
  }
}
```

### 방법 2: HTTP 서버로 실행

서버를 직접 띄워 두고 URL로 연결합니다.

```bash
.venv/bin/fastmcp run server.py:mcp --transport http --port 8000
```

```bash
claude mcp add --transport http travel-info http://127.0.0.1:8000/mcp
```

이 방식은 터미널을 닫으면 서버도 꺼집니다. 쓰기 전에 서버가 떠 있는지 확인하세요.

### 연결 확인

```bash
claude mcp list
```

`travel-info: ... - ✔ Connected`가 보이면 연결된 것입니다.

## 사용 예시

Claude에게 이렇게 물어보면 됩니다.

- "지금 1달러 몇 원이야?" → `get_exchange_rate(base="USD", target="KRW")`
- "엔화 5만 엔은 원화로 얼마야?" → `get_exchange_rate(base="엔화", target="원화", amount=50000)`
- "파리 일주일 날씨 알려줘" → `get_weather(location="Paris", days=7)`
- "다음 5일 방콕 여행 어때? 예산은 100만 원이야" → `analyze_travel_condition(destination="방콕", budget=1000000)`

`analyze_travel_condition` 응답은 대략 이런 모양입니다.

```json
{
  "destination": { "name": "방콕, 태국", "country_code": "TH", "timezone": "Asia/Bangkok" },
  "overall": { "weather_score": 72.0, "grade": "좋음", "summary": "방콕, 태국의 향후 5일 여행 날씨는 평균 72.0점(좋음)입니다. ..." },
  "weather_by_day": [ { "date": "...", "weather": "부분적으로 흐림", "temp": "25~33°C", "score": 70, "grade": "좋음", "notes": ["더움"] } ],
  "current_weather": { "temperature_c": 30.1, "humidity_pct": 70 },
  "packing_tips": ["비 예보가 있으니 우산·방수 외투를 챙기세요."],
  "exchange": { "home_currency": "KRW", "local_currency": "THB", "summary": "1 KRW = ... THB / 1 THB = ... KRW", "budget": { "per_day_local": "... THB (5일 기준)" } },
  "sources": ["open-meteo.com", "open.er-api.com"]
}
```

(숫자는 예시이며 실제 값은 조회 시점에 따라 다릅니다.)

## 데이터 출처

| 데이터 | API |
| --- | --- |
| 환율 | [open.er-api.com](https://www.exchangerate-api.com/docs/free) (`/v6/latest/{BASE}`) |
| 도시 좌표 | [Open-Meteo Geocoding API](https://open-meteo.com/en/docs/geocoding-api) |
| 날씨 예보 | [Open-Meteo Forecast API](https://open-meteo.com/en/docs) |

## 문제 해결

- **날씨 조회가 시간 초과로 실패할 때**: 일부 네트워크에서는 open-meteo의 IPv6 경로가 응답하지 않습니다. 그래서 서버는 IPv4로 고정해 요청합니다(`_client()` 참고).
- **위치를 찾지 못할 때**: 도시 이름을 영어로 입력해 보세요. 예: `오사카` 대신 `Osaka`.
- **통화를 해석하지 못할 때**: `USD`, `JPY` 같은 3자리 ISO 코드를 사용하세요.
- **`Failed to connect`가 뜰 때**: HTTP 방식이라면 서버가 실행 중인지 먼저 확인하세요. stdio 방식이라면 `command`와 `args`가 `.venv` 안의 python과 `server.py`의 절대경로를 가리키는지 확인하세요.

## 파일 구성

```
.
├── server.py          # MCP 서버 (도구 3개)
├── requirements.txt   # fastmcp, httpx
└── README.md
```
