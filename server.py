"""여행 정보 MCP 서버 (환율 · 날씨 · 여행환경 분석)

실행:
    .venv/bin/python server.py            # stdio (Claude Desktop / Claude Code 연결용)
    .venv/bin/fastmcp run server.py:mcp   # fastmcp CLI 로 실행

데이터 출처:
    환율      https://open.er-api.com/v6/latest/{BASE}
    도시 좌표  https://geocoding-api.open-meteo.com/v1/search
    날씨      https://api.open-meteo.com/v1/forecast
"""

from __future__ import annotations

from typing import Any

import httpx
from fastmcp import FastMCP

mcp = FastMCP(
    name="travel-info",
    instructions=(
        "환율, 날씨, 여행환경 분석 도구를 제공합니다. "
        "통화는 ISO 코드(USD, JPY) 또는 국가명(일본, 미국)으로, "
        "장소는 도시명/국가명(도쿄, Paris)으로 입력할 수 있습니다."
    ),
)

EXCHANGE_URL = "https://open.er-api.com/v6/latest/{base}"
GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TIMEOUT = httpx.Timeout(10.0)


def _client() -> httpx.AsyncClient:
    # 일부 네트워크에서 open-meteo의 IPv6 경로가 응답하지 않아 IPv4로 고정한다.
    return httpx.AsyncClient(
        timeout=TIMEOUT,
        transport=httpx.AsyncHTTPTransport(local_address="0.0.0.0", retries=2),
    )

# ---------------------------------------------------------------------------
# 참조 데이터
# ---------------------------------------------------------------------------

# 국가 코드(ISO 3166-1 alpha-2) -> 통화 코드
COUNTRY_CURRENCY: dict[str, str] = {
    "KR": "KRW", "US": "USD", "JP": "JPY", "CN": "CNY", "HK": "HKD", "TW": "TWD",
    "MO": "MOP", "MN": "MNT", "SG": "SGD", "TH": "THB", "VN": "VND", "PH": "PHP",
    "MY": "MYR", "ID": "IDR", "KH": "KHR", "LA": "LAK", "MM": "MMK", "IN": "INR",
    "NP": "NPR", "LK": "LKR", "MV": "MVR", "PK": "PKR", "BD": "BDT", "AE": "AED",
    "SA": "SAR", "QA": "QAR", "IL": "ILS", "JO": "JOD", "TR": "TRY", "EG": "EGP",
    "MA": "MAD", "ZA": "ZAR", "KE": "KES", "GB": "GBP", "CH": "CHF", "NO": "NOK",
    "SE": "SEK", "DK": "DKK", "IS": "ISK", "PL": "PLN", "CZ": "CZK", "HU": "HUF",
    "RO": "RON", "RU": "RUB", "UA": "UAH", "AU": "AUD", "NZ": "NZD", "CA": "CAD",
    "MX": "MXN", "BR": "BRL", "AR": "ARS", "CL": "CLP", "PE": "PEN", "CO": "COP",
    "CU": "CUP", "FJ": "FJD", "GU": "USD", "MP": "USD", "PR": "USD",
    # 유로존
    **{c: "EUR" for c in (
        "DE", "FR", "IT", "ES", "PT", "NL", "BE", "AT", "IE", "FI", "GR", "LU",
        "SK", "SI", "EE", "LV", "LT", "MT", "CY", "HR", "MC", "VA", "SM", "AD",
    )},
}

# 자주 쓰는 국가/통화 이름 -> 통화 코드
NAME_CURRENCY: dict[str, str] = {
    "한국": "KRW", "대한민국": "KRW", "원": "KRW", "원화": "KRW", "korea": "KRW",
    "미국": "USD", "달러": "USD", "usa": "USD", "united states": "USD",
    "일본": "JPY", "엔": "JPY", "엔화": "JPY", "japan": "JPY",
    "중국": "CNY", "위안": "CNY", "china": "CNY",
    "홍콩": "HKD", "hong kong": "HKD", "대만": "TWD", "taiwan": "TWD",
    "마카오": "MOP", "몽골": "MNT", "싱가포르": "SGD", "singapore": "SGD",
    "태국": "THB", "thailand": "THB", "베트남": "VND", "vietnam": "VND",
    "필리핀": "PHP", "philippines": "PHP", "말레이시아": "MYR", "malaysia": "MYR",
    "인도네시아": "IDR", "indonesia": "IDR", "캄보디아": "KHR", "라오스": "LAK",
    "인도": "INR", "india": "INR", "네팔": "NPR", "몰디브": "MVR",
    "아랍에미리트": "AED", "uae": "AED", "두바이": "AED", "튀르키예": "TRY",
    "터키": "TRY", "turkey": "TRY", "이집트": "EGP", "egypt": "EGP",
    "영국": "GBP", "파운드": "GBP", "uk": "GBP", "united kingdom": "GBP",
    "유럽": "EUR", "유로": "EUR", "europe": "EUR", "독일": "EUR", "germany": "EUR",
    "프랑스": "EUR", "france": "EUR", "이탈리아": "EUR", "italy": "EUR",
    "스페인": "EUR", "spain": "EUR", "포르투갈": "EUR", "네덜란드": "EUR",
    "오스트리아": "EUR", "그리스": "EUR", "핀란드": "EUR", "크로아티아": "EUR",
    "스위스": "CHF", "switzerland": "CHF", "노르웨이": "NOK", "스웨덴": "SEK",
    "덴마크": "DKK", "아이슬란드": "ISK", "체코": "CZK", "헝가리": "HUF",
    "폴란드": "PLN", "러시아": "RUB", "호주": "AUD", "australia": "AUD",
    "뉴질랜드": "NZD", "new zealand": "NZD", "캐나다": "CAD", "canada": "CAD",
    "멕시코": "MXN", "mexico": "MXN", "브라질": "BRL", "brazil": "BRL",
    "아르헨티나": "ARS", "칠레": "CLP", "페루": "PEN", "남아공": "ZAR",
    "괌": "USD", "사이판": "USD", "하와이": "USD",
}

# WMO 날씨 코드 -> 한국어 설명
WEATHER_CODES: dict[int, str] = {
    0: "맑음", 1: "대체로 맑음", 2: "부분적으로 흐림", 3: "흐림",
    45: "안개", 48: "서리 안개",
    51: "약한 이슬비", 53: "이슬비", 55: "강한 이슬비",
    56: "약한 어는 이슬비", 57: "강한 어는 이슬비",
    61: "약한 비", 63: "비", 65: "강한 비",
    66: "약한 어는 비", 67: "강한 어는 비",
    71: "약한 눈", 73: "눈", 75: "강한 눈", 77: "싸락눈",
    80: "약한 소나기", 81: "소나기", 82: "강한 소나기",
    85: "약한 눈보라", 86: "강한 눈보라",
    95: "뇌우", 96: "약한 우박 동반 뇌우", 99: "강한 우박 동반 뇌우",
}


# ---------------------------------------------------------------------------
# 내부 헬퍼
# ---------------------------------------------------------------------------

def _resolve_currency(value: str) -> str:
    """'USD', '미국', 'japan', 'JP' 등을 통화 코드로 변환."""
    v = value.strip()
    if v.lower() in NAME_CURRENCY:
        return NAME_CURRENCY[v.lower()]
    if v in NAME_CURRENCY:
        return NAME_CURRENCY[v]
    up = v.upper()
    if len(up) == 2 and up in COUNTRY_CURRENCY:
        return COUNTRY_CURRENCY[up]
    if len(up) == 3 and up.isalpha():
        return up
    raise ValueError(f"'{value}'을(를) 통화 코드로 해석할 수 없습니다. USD, JPY 같은 ISO 코드를 사용하세요.")


async def _fetch_rates(base: str) -> dict[str, Any]:
    async with _client() as client:
        r = await client.get(EXCHANGE_URL.format(base=base))
        r.raise_for_status()
        data = r.json()
    if data.get("result") != "success":
        raise ValueError(f"환율 조회 실패 ({base}): {data.get('error-type', 'unknown error')}")
    return data


async def _geocode(location: str) -> dict[str, Any]:
    async with _client() as client:
        r = await client.get(
            GEOCODING_URL,
            params={"name": location.strip(), "count": 1, "language": "ko", "format": "json"},
        )
        r.raise_for_status()
        results = r.json().get("results") or []
    if not results:
        raise ValueError(f"'{location}' 위치를 찾을 수 없습니다. 도시 이름을 영어로도 시도해 보세요.")
    return results[0]


async def _fetch_weather(lat: float, lon: float, days: int) -> dict[str, Any]:
    params = {
        "latitude": lat,
        "longitude": lon,
        "current": "temperature_2m,apparent_temperature,relative_humidity_2m,"
                   "precipitation,weather_code,wind_speed_10m",
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,"
                 "precipitation_sum,precipitation_probability_max,wind_speed_10m_max,uv_index_max",
        "timezone": "auto",
        "forecast_days": days,
    }
    async with _client() as client:
        r = await client.get(FORECAST_URL, params=params)
        r.raise_for_status()
        return r.json()


def _place_info(geo: dict[str, Any]) -> dict[str, Any]:
    name_parts = [geo.get("name"), geo.get("admin1"), geo.get("country")]
    return {
        "name": ", ".join(p for p in dict.fromkeys(name_parts) if p),
        "country": geo.get("country"),
        "country_code": geo.get("country_code"),
        "latitude": geo.get("latitude"),
        "longitude": geo.get("longitude"),
        "timezone": geo.get("timezone"),
    }


def _format_weather(raw: dict[str, Any]) -> dict[str, Any]:
    cur = raw.get("current", {})
    units = raw.get("current_units", {})
    d = raw.get("daily", {})
    daily = []
    for i, date in enumerate(d.get("time", [])):
        code = d["weather_code"][i]
        daily.append({
            "date": date,
            "weather": WEATHER_CODES.get(code, f"코드 {code}"),
            "weather_code": code,
            "temp_max_c": d["temperature_2m_max"][i],
            "temp_min_c": d["temperature_2m_min"][i],
            "precipitation_mm": d["precipitation_sum"][i],
            "precipitation_probability_pct": d["precipitation_probability_max"][i],
            "wind_max_kmh": d["wind_speed_10m_max"][i],
            "uv_index_max": d["uv_index_max"][i],
        })
    return {
        "current": {
            "time": cur.get("time"),
            "weather": WEATHER_CODES.get(cur.get("weather_code"), f"코드 {cur.get('weather_code')}"),
            "temperature_c": cur.get("temperature_2m"),
            "apparent_temperature_c": cur.get("apparent_temperature"),
            "humidity_pct": cur.get("relative_humidity_2m"),
            "precipitation_mm": cur.get("precipitation"),
            "wind_speed_kmh": cur.get("wind_speed_10m"),
        },
        "daily": daily,
        "units": units,
    }


def _score_day(day: dict[str, Any]) -> tuple[int, list[str]]:
    """하루 날씨를 0~100점으로 평가하고 감점 사유를 돌려준다."""
    score, notes = 100, []
    tmax, tmin = day["temp_max_c"], day["temp_min_c"]
    avg = (tmax + tmin) / 2 if tmax is not None and tmin is not None else None
    if avg is not None:
        if avg < 0:
            score -= 30; notes.append("매우 추움")
        elif avg < 8:
            score -= 15; notes.append("쌀쌀함")
        elif avg > 32:
            score -= 30; notes.append("매우 더움")
        elif avg > 28:
            score -= 15; notes.append("더움")
    pop = day["precipitation_probability_pct"] or 0
    if pop >= 70:
        score -= 30; notes.append(f"강수확률 {pop}%")
    elif pop >= 40:
        score -= 15; notes.append(f"강수확률 {pop}%")
    wind = day["wind_max_kmh"] or 0
    if wind >= 50:
        score -= 20; notes.append(f"강풍 {wind}km/h")
    elif wind >= 30:
        score -= 8; notes.append(f"바람 {wind}km/h")
    if day["weather_code"] in (95, 96, 99):
        score -= 15; notes.append("뇌우")
    if day["weather_code"] in (65, 67, 75, 82, 86):
        score -= 10; notes.append("강한 강수/강설")
    return max(score, 0), notes


def _grade(score: float) -> str:
    if score >= 85:
        return "매우 좋음"
    if score >= 70:
        return "좋음"
    if score >= 50:
        return "보통"
    if score >= 30:
        return "나쁨"
    return "매우 나쁨"


# ---------------------------------------------------------------------------
# MCP 도구
# ---------------------------------------------------------------------------

@mcp.tool
async def get_exchange_rate(
    base: str = "USD",
    target: str | None = None,
    amount: float = 1.0,
) -> dict[str, Any]:
    """환율을 조회합니다.

    Args:
        base: 기준 통화. ISO 코드(USD) 또는 국가/통화 이름(미국, 일본, 유로).
        target: 대상 통화. 생략하면 주요 통화 목록을 반환합니다.
        amount: 환산할 금액 (기준 통화 단위). 기본 1.
    """
    base_code = _resolve_currency(base)
    data = await _fetch_rates(base_code)
    rates: dict[str, float] = data["rates"]
    result: dict[str, Any] = {
        "base": base_code,
        "amount": amount,
        "last_updated_utc": data.get("time_last_update_utc"),
        "next_update_utc": data.get("time_next_update_utc"),
        "source": "open.er-api.com",
    }
    if target:
        target_code = _resolve_currency(target)
        if target_code not in rates:
            raise ValueError(f"지원하지 않는 통화입니다: {target_code}")
        rate = rates[target_code]
        result.update({
            "target": target_code,
            "rate": rate,
            "converted": round(amount * rate, 4),
            "inverse_rate": round(1 / rate, 6) if rate else None,
            "summary": f"{amount:,g} {base_code} = {amount * rate:,.2f} {target_code}",
        })
    else:
        majors = ["KRW", "USD", "EUR", "JPY", "CNY", "GBP", "AUD", "CAD", "CHF", "HKD", "SGD", "THB", "VND"]
        result["rates"] = {c: round(amount * rates[c], 4) for c in majors if c in rates and c != base_code}
    return result


@mcp.tool
async def get_weather(location: str, days: int = 3) -> dict[str, Any]:
    """도시나 국가의 현재 날씨와 일별 예보를 조회합니다.

    Args:
        location: 도시 또는 국가 이름 (예: 서울, 도쿄, Paris, 태국).
        days: 예보 일수 (1~16). 기본 3.
    """
    days = max(1, min(int(days), 16))
    geo = await _geocode(location)
    raw = await _fetch_weather(geo["latitude"], geo["longitude"], days)
    return {
        "location": _place_info(geo),
        **_format_weather(raw),
        "source": "open-meteo.com",
    }


@mcp.tool
async def analyze_travel_condition(
    destination: str,
    home_currency: str = "KRW",
    days: int = 5,
    budget: float | None = None,
) -> dict[str, Any]:
    """목적지의 날씨 예보와 환율을 함께 조회해 여행 환경을 분석합니다.

    Args:
        destination: 여행지 도시 또는 국가 이름 (예: 오사카, 방콕, Rome).
        home_currency: 출발지(본인) 통화. 기본 KRW.
        days: 분석할 예보 일수 (1~16). 기본 5.
        budget: 본인 통화 기준 여행 예산. 입력하면 현지 통화로 환산합니다.
    """
    days = max(1, min(int(days), 16))
    home = _resolve_currency(home_currency)
    geo = await _geocode(destination)
    place = _place_info(geo)
    local = COUNTRY_CURRENCY.get((place["country_code"] or "").upper())

    raw = await _fetch_weather(geo["latitude"], geo["longitude"], days)
    weather = _format_weather(raw)

    # --- 날씨 분석 ---
    day_scores = []
    for day in weather["daily"]:
        s, notes = _score_day(day)
        day_scores.append({
            "date": day["date"], "weather": day["weather"],
            "temp": f"{day['temp_min_c']}~{day['temp_max_c']}°C",
            "score": s, "grade": _grade(s), "notes": notes,
        })
    avg_score = round(sum(d["score"] for d in day_scores) / len(day_scores), 1)
    best = max(day_scores, key=lambda d: d["score"])
    worst = min(day_scores, key=lambda d: d["score"])

    tips: list[str] = []
    daily = weather["daily"]
    if any((d["precipitation_probability_pct"] or 0) >= 40 for d in daily):
        tips.append("비 예보가 있으니 우산·방수 외투를 챙기세요.")
    lows = [d["temp_min_c"] for d in daily if d["temp_min_c"] is not None]
    highs = [d["temp_max_c"] for d in daily if d["temp_max_c"] is not None]
    if lows and min(lows) < 5:
        tips.append(f"최저 {min(lows)}°C까지 내려가니 두꺼운 외투가 필요합니다.")
    if highs and max(highs) > 30:
        tips.append(f"최고 {max(highs)}°C까지 오르니 더위·탈수에 주의하세요.")
    if highs and lows and (max(highs) - min(lows)) >= 12:
        tips.append("일교차가 크니 겹쳐 입을 옷을 준비하세요.")
    if any((d["uv_index_max"] or 0) >= 8 for d in daily):
        tips.append("자외선 지수가 매우 높으니 자외선 차단제를 챙기세요.")
    if any((d["wind_max_kmh"] or 0) >= 40 for d in daily):
        tips.append("강풍 예보가 있어 항공·선박 일정 변동 가능성을 확인하세요.")
    if not tips:
        tips.append("특별한 날씨 위험 요소가 없습니다.")

    # --- 환율 분석 ---
    exchange: dict[str, Any]
    if not local:
        exchange = {"note": f"{place['country']}의 통화를 자동으로 판별하지 못했습니다. get_exchange_rate를 직접 사용하세요."}
    elif local == home:
        exchange = {"local_currency": local, "note": "본인 통화와 현지 통화가 같아 환전이 필요 없습니다."}
    else:
        data = await _fetch_rates(home)
        rate = data["rates"].get(local)
        if rate is None:
            exchange = {"local_currency": local, "note": f"{local} 환율 정보를 제공받지 못했습니다."}
        else:
            exchange = {
                "home_currency": home,
                "local_currency": local,
                "rate": rate,
                "summary": f"1 {home} = {rate:.6g} {local} / 1 {local} = {1 / rate:,.2f} {home}",
                "examples": {
                    f"{amt:,} {home}": f"{amt * rate:,.2f} {local}"
                    for amt in ((10_000, 100_000, 1_000_000) if home == "KRW" else (10, 100, 1000))
                },
                "last_updated_utc": data.get("time_last_update_utc"),
            }
            if budget:
                exchange["budget"] = {
                    "home": f"{budget:,.0f} {home}",
                    "local": f"{budget * rate:,.2f} {local}",
                    "per_day_local": f"{budget * rate / days:,.2f} {local} ({days}일 기준)",
                }
            exchange["note"] = (
                "환율 API는 현재 시세만 제공하므로 과거 대비 유불리는 판단하지 않습니다. "
                "실제 환전 시에는 은행·카드 수수료가 추가됩니다."
            )

    # --- 종합 ---
    grade = _grade(avg_score)
    summary = (
        f"{place['name']}의 향후 {len(day_scores)}일 여행 날씨는 평균 {avg_score}점({grade})입니다."
    )
    if best["score"] != worst["score"]:
        summary += (
            f" 가장 좋은 날은 {best['date']}({best['weather']}, {best['score']}점), "
            f"가장 나쁜 날은 {worst['date']}({worst['weather']}, {worst['score']}점)입니다."
        )
    if "summary" in exchange:
        summary += f" 환율: {exchange['summary']}."

    return {
        "destination": place,
        "overall": {"weather_score": avg_score, "grade": grade, "summary": summary},
        "weather_by_day": day_scores,
        "current_weather": weather["current"],
        "packing_tips": tips,
        "exchange": exchange,
        "sources": ["open-meteo.com", "open.er-api.com"],
    }


if __name__ == "__main__":
    mcp.run()
