from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

# MCP Serverを作成
mcp = FastMCP("weather")

# アメリカ国立気象局 API
NWS_API_BASE = "https://api.weather.gov"

# リクエストヘッダー（NWS公式の要件）
USER_AGENT = "weather-mcp/1.0"


async def make_nws_request(url: str) -> dict[str, Any] | None:
    """
    NWS APIにリクエストを送信
    """

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "application/geo+json",
    }

    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            return response.json()

        except Exception as e:
            print(f"Request Error: {e}")
            return None


def format_forecast(data: dict) -> str:
    """
    天気予報を整形
    """

    if not data:
        return "No forecast data."

    periods = data["properties"]["periods"]

    forecasts = []

    for period in periods[:5]:
        forecasts.append(
            f"""
{period["name"]}

Temperature: {period["temperature"]}°
Wind: {period["windSpeed"]} {period["windDirection"]}

Forecast:
{period["detailedForecast"]}
"""
        )

    return "\n------------------------\n".join(forecasts)


def format_alert(feature: dict) -> str:
    """
    気象警報を整形
    """

    props = feature["properties"]

    return f"""
Event:
{props.get("event", "Unknown")}

Area:
{props.get("areaDesc", "Unknown")}

Severity:
{props.get("severity", "Unknown")}

Headline:
{props.get("headline", "")}

Description:
{props.get("description", "")}

Instruction:
{props.get("instruction", "No instructions")}
"""


@mcp.tool()
async def get_forecast(latitude: float, longitude: float) -> str:
    """
    指定した場所の天気予報を取得

    Args:
        latitude: 緯度
        longitude: 経度
    """

    points_url = f"{NWS_API_BASE}/points/{latitude},{longitude}"

    points_data = await make_nws_request(points_url)

    if not points_data:
        return "Unable to fetch forecast data for this location."

    forecast_url = points_data["properties"]["forecast"]

    forecast_data = await make_nws_request(forecast_url)

    if not forecast_data:
        return "Unable to fetch forecast."

    return format_forecast(forecast_data)


@mcp.tool()
async def get_alerts(state: str) -> str:
    """
    アメリカの州の気象警報を取得

    Args:
        state: アメリカの州コード、例：
            CA
            NY
            TX
            FL
    """

    url = f"{NWS_API_BASE}/alerts/active/area/{state}"

    data = await make_nws_request(url)

    if not data or "features" not in data:
        return "Unable to fetch alerts or no alerts found."

    if not data["features"]:
        return "No active alerts for this state."

    alerts = [format_alert(feature) for feature in data["features"]]

    return "\n============================\n".join(alerts)


if __name__ == "__main__":
    mcp.run()