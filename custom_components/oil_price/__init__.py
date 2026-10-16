"""The China Oil Price integration."""

from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_REGION,
    CONF_SCAN_INTERVAL_HOURS,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import OilPriceCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    region = entry.data[CONF_REGION]
    hours = entry.data.get(CONF_SCAN_INTERVAL_HOURS)
    scan_interval = timedelta(hours=hours) if hours else DEFAULT_SCAN_INTERVAL

    coordinator = OilPriceCoordinator(hass, region, scan_interval)
    # Pull once before platforms load so entities start with real data;
    # raises ConfigEntryNotReady on failure so HA retries automatically.
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
