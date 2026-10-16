"""Config flow for China Oil Price."""

from __future__ import annotations

import asyncio
import logging

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_REGION,
    CONF_SCAN_INTERVAL_HOURS,
    DEFAULT_NAME,
    DEFAULT_REGION,
    DOMAIN,
)
from .coordinator import async_fetch_and_parse

_LOGGER = logging.getLogger(__name__)


class OilPriceConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for oil_price."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors: dict[str, str] = {}

        if user_input is not None:
            region = str(user_input[CONF_REGION]).strip().lower()
            user_input[CONF_REGION] = region
            session = async_get_clientsession(self.hass)

            try:
                # Trial-fetch once so a wrong slug fails here, not 8h later.
                await async_fetch_and_parse(session, region)
            except (aiohttp.ClientError, asyncio.TimeoutError):
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001 — ValueError(unknown region) / parse
                errors["base"] = "invalid_region"
            else:
                await self.async_set_unique_id(region)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data=user_input
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_REGION, default=DEFAULT_REGION): str,
                    vol.Optional(CONF_SCAN_INTERVAL_HOURS): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=168)
                    ),
                }
            ),
            errors=errors,
        )
