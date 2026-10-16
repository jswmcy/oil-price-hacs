"""Data fetch + parse + coordinator for China Oil Price."""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from typing import Any

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import (
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.util import dt as dt_util

from .const import (
    BASE_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    OIL_TYPES,
    USER_AGENT,
)

_LOGGER = logging.getLogger(__name__)

# Direction keywords, most specific first so "上调"/"下调" win over "维持".
_DIRECTION_RE = re.compile(r"(上调|下调|搁浅|不作调整|不调整|维持|不变)")
# e.g. "预计92号汽油价格上调0.11元/升" — tolerant to full/half width, optional #.
_CHANGE_RE = re.compile(
    r"(9[258](?:#|号)?|0(?:#|号)?)\D{0,10}?(上调|下调)\D{0,4}?([\d.]+)\s*元"
)
# Extract the first number out of a price cell like "8.58" or "8.58元".
_PRICE_NUM_RE = re.compile(r"[-+]?\d+(?:\.\d+)?")


def _decode(raw: bytes) -> str:
    """Decode response bytes. Site currently declares UTF-8, older served
    GB2312/GBK, so try UTF-8 first then GB18030 as a safety net."""
    for enc in ("utf-8", "gb18030"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", "replace")


def parse_oil_data(html: str) -> dict[str, Any]:
    """Parse one region page into {'prices': {...}, 'hint': {...}}.

    Parsing is content-driven (never positional nth-child) and never raises on
    a missing/changed section — it just omits that field, so the entities keep
    whatever they already had instead of going fully unknown.
    """
    soup = BeautifulSoup(html, "lxml")

    # ---- prices --------------------------------------------------------
    prices: dict[str, float] = {}
    price_box = soup.select_one("#youjia")
    if price_box:
        for dl in price_box.select("dl"):
            dt = dl.find("dt")
            dd = dl.find("dd")
            if not dt or not dd:
                continue
            label = dt.get_text(strip=True)
            value = _PRICE_NUM_RE.search(dd.get_text(strip=True))
            if not value:
                continue
            for key in OIL_TYPES:
                if key in label and key not in prices:
                    prices[key] = float(value.group(0))

    # ---- hint (next adjustment + up/down) ------------------------------
    hint = _parse_hint(soup)

    return {"prices": prices, "hint": hint}


def _find_hint_box(soup: BeautifulSoup):
    """Locate the red-bordered '下次油价…调整' box inside #youjiaCont.

    Prefer the distinctive border color; fall back to any block mentioning
    调整/调价. This survives the site adding/removing sibling divs.
    """
    container = soup.select_one("#youjiaCont") or soup
    candidates = container.find_all("div", recursive=False) or container.find_all("div")
    # 1st pass: border color
    for div in candidates:
        style = (div.get("style") or "").lower()
        if "#ea5146" in style and "调整" in div.get_text():
            return div
    # 2nd pass: any block whose own text mentions 调整/调价 (exclude big parents)
    for div in candidates:
        own = _own_text(div)
        if ("调整" in own or "调价" in own) and "下次" in own:
            return div
    for div in candidates:
        own = _own_text(div)
        if "调整" in own or "调价" in own:
            return div
    return None


def _own_text(div) -> str:
    """Text of a div excluding nested <script>/<style> noise."""
    clone = BeautifulSoup(str(div), "lxml")
    for tag in clone(["script", "style"]):
        tag.decompose()
    return clone.get_text(" ", strip=True)


def _parse_hint(soup: BeautifulSoup) -> dict[str, Any]:
    box = _find_hint_box(soup)
    if box is None:
        return {}

    text = _own_text(box)
    if not text:
        return {}

    next_adjust = None
    m = re.search(r"下次(?:油价)?(.{0,15}?)调整", text)
    if m:
        next_adjust = m.group(1).strip("，, ：:")

    direction = None
    d = _DIRECTION_RE.search(text)
    if d:
        direction = d.group(1)

    changes = {}
    for grade, dirn, amount in _CHANGE_RE.findall(text):
        changes[grade] = f"{dirn}{amount}元/升"

    return {
        "text": text,
        "next_adjust": next_adjust,
        "direction": direction,
        "changes": changes,
    }


async def async_fetch_and_parse(
    session: aiohttp.ClientSession,
    region: str,
    timeout: int = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    """Fetch a region page and parse it. Raises on network/HTTP error so the
    caller can decide (coordinator -> UpdateFailed, config flow -> form error)."""
    url = BASE_URL.format(region=region)
    headers = {"User-Agent": USER_AGENT}
    client_timeout = aiohttp.ClientTimeout(total=timeout)

    async with session.get(
        url, headers=headers, timeout=client_timeout
    ) as response:
        if response.status != 200:
            raise aiohttp.ClientResponseError(
                response.request_info,
                response.history,
                status=response.status,
                message=f"HTTP {response.status}",
            )
        raw = await response.read()

    data = parse_oil_data(_decode(raw))

    # A valid region page must yield at least the 92# price; otherwise the slug
    # is wrong or the layout broke. Used to reject bad region input up-front.
    if "92#" not in data["prices"]:
        raise ValueError(f"Region '{region}' returned no recognizable oil prices")

    return data


class OilPriceCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch & parse the region page once per update for all entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        region: str,
        scan_interval: timedelta = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{region}",
            update_interval=scan_interval,
        )
        self.region = region

    async def _async_update_data(self) -> dict[str, Any]:
        session = async_get_clientsession(self.hass)
        try:
            data = await async_fetch_and_parse(
                session, self.region, timeout=DEFAULT_TIMEOUT
            )
        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            raise UpdateFailed(f"Error communicating with qiyoujiage.com: {err}")
        except ValueError as err:
            # Layout changed / bad slug: treat as update failure, keep old data.
            raise UpdateFailed(f"Oil price data not found for {self.region}: {err}")

        data["update_time"] = dt_util.utcnow().isoformat()
        return data
