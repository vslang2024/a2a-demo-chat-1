import os
import httpx
from typing import Optional

from mcp.client.session import ClientSession
from mcp.client.streamable_http import streamable_http_client

from ..utils.logger import get_logger, log_context


logger = get_logger(__name__)


class WeatherAgent:
    def __init__(self, mcp_url: Optional[str] = None):
        self.mcp_url = mcp_url or os.getenv("MCP_WEATHER_URL", "http://localhost:8080/mcp")

    async def get_weather_summary(self, city: str, start_date: str, end_date: str) -> str:
        with log_context(agent="weather_agent"):
            logger.info("Weather lookup start for %s", city)

        try:
            async with streamable_http_client(self.mcp_url) as transport:
                try:
                    read, write = transport
                except ValueError:
                    read, write, _ = transport
                except TypeError:
                    read = transport.read
                    write = transport.write
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    tools = await session.list_tools()
                    tool_names = [tool.name for tool in tools.tools]

                    if "get_weather_by_datetime_range" in tool_names:
                        tool_name = "get_weather_by_datetime_range"
                        arguments = {
                            "city": city,
                            "start_date": start_date,
                            "end_date": end_date,
                        }
                    elif "get_weather" in tool_names:
                        tool_name = "get_weather"
                        arguments = {"city": city}
                    elif "get_current_weather" in tool_names:
                        tool_name = "get_current_weather"
                        arguments = {"city": city}
                    else:
                        raise RuntimeError(f"No compatible weather tool found: {tool_names}")

                    result = await session.call_tool(tool_name, arguments=arguments)

            if getattr(result, "isError", False):
                raise RuntimeError(str(result))
        except Exception as e:
            with log_context(agent="weather_agent"):
                logger.exception("Weather lookup failed")
                if isinstance(e, ExceptionGroup):
                    for idx, sub in enumerate(e.exceptions, start=1):
                        logger.exception("Weather lookup sub-exception %s", idx, exc_info=sub)
            # Fallback to Open-Meteo when MCP server is unreachable.
            if _is_connection_error(e):
                summary = await _fallback_open_meteo(city, start_date, end_date)
                if summary:
                    with log_context(agent="weather_agent"):
                        logger.info("Weather fallback complete for %s", city)
                    return summary
            if isinstance(e, ExceptionGroup):
                details = "; ".join(str(sub) for sub in e.exceptions)
                raise RuntimeError(details) from e
            raise

        texts: list[str] = []
        for item in getattr(result, "content", []) or []:
            text = getattr(item, "text", None)
            if text:
                texts.append(text)
            else:
                texts.append(str(item))

        summary = "\n".join(texts).strip()
        if not summary:
            summary = str(result)

        with log_context(agent="weather_agent"):
            logger.info("Weather lookup complete for %s", city)
        return summary


def _is_connection_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.ConnectError):
        return True
    if isinstance(exc, ExceptionGroup):
        return any(isinstance(sub, httpx.ConnectError) for sub in exc.exceptions)
    return False


async def _fallback_open_meteo(city: str, start_date: str, end_date: str) -> str | None:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            geo = await client.get(
                "https://geocoding-api.open-meteo.com/v1/search",
                params={"name": city, "count": 1, "language": "en", "format": "json"},
            )
            geo.raise_for_status()
            geo_data = geo.json()
            results = geo_data.get("results") or []
            if not results:
                return None
            location = results[0]
            lat = location.get("latitude")
            lon = location.get("longitude")
            name = location.get("name")
            country = location.get("country")

            forecast = await client.get(
                "https://api.open-meteo.com/v1/forecast",
                params={
                    "latitude": lat,
                    "longitude": lon,
                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                    "timezone": "auto",
                    "start_date": start_date,
                    "end_date": end_date,
                },
            )
            forecast.raise_for_status()
            data = forecast.json()
            daily = data.get("daily") or {}
            temps_max = daily.get("temperature_2m_max") or []
            temps_min = daily.get("temperature_2m_min") or []
            precip = daily.get("precipitation_sum") or []

            if not temps_max and not temps_min and not precip:
                return None

            max_avg = sum(temps_max) / len(temps_max) if temps_max else None
            min_avg = sum(temps_min) / len(temps_min) if temps_min else None
            precip_total = sum(precip) if precip else None

            parts = [f"Weather for {name}, {country} ({start_date} to {end_date})"]
            if max_avg is not None:
                parts.append(f"Avg max temp: {max_avg:.1f}°C")
            if min_avg is not None:
                parts.append(f"Avg min temp: {min_avg:.1f}°C")
            if precip_total is not None:
                parts.append(f"Total precipitation: {precip_total:.1f} mm")
            parts.append("Source: Open-Meteo (fallback)")
            return " | ".join(parts)
    except Exception:
        return None
