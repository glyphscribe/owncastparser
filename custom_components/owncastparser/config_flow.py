from __future__ import annotations

import asyncio
from urllib.parse import urlparse

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL, CONF_TIMEOUT, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_TIMEOUT, DEFAULT_VERIFY_SSL


DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_NAME, default="Owncast Server"): str,
        vol.Required(CONF_URL): str,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
    }
)


class OwncastParserConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}

        if user_input is not None:
            url = user_input[CONF_URL].rstrip("/")
            user_input[CONF_URL] = url

            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                errors["base"] = "invalid_url"
            else:
                await self.async_set_unique_id(self._normalize_url(url))
                self._abort_if_unique_id_configured()

                if await self._test_connection(url, user_input):
                    return self.async_create_entry(
                        title=user_input[CONF_NAME], data=user_input
                    )
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )

    async def async_step_import(self, import_data):
        url = import_data[CONF_URL].rstrip("/")
        import_data[CONF_URL] = url

        await self.async_set_unique_id(self._normalize_url(url))
        self._abort_if_unique_id_configured()

        return self.async_create_entry(
            title=import_data[CONF_NAME], data=import_data
        )

    @staticmethod
    def _normalize_url(url: str) -> str:
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.hostname}{':' + str(parsed.port) if parsed.port else ''}{parsed.path}".lower()

    async def _test_connection(self, url, config):
        session = async_get_clientsession(
            self.hass, verify_ssl=config.get(
                CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        )
        try:
            async with asyncio.timeout(config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)):
                async with session.get(f"{url}/api/status") as response:
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type.lower():
                        return True
        except (aiohttp.ClientError, TimeoutError):
            pass
        return False
