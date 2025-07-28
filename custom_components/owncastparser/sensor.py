from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Final, TYPE_CHECKING

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_TIMEOUT, CONF_URL, CONF_VERIFY_SSL, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType



COMPOENENT_REPO = "https://github.com/glyphscribe/owncastparser" # copy

CONF_SERVER_URL = "url"

DEFAULT_SCAN_INTERVAL = timedelta(minutes=1)
DEFAULT_TIMEOUT = 10
DEFAULT_VERIFY_SSL = True

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_SERVER_URL): cv.string,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(int, vol.Range(min=1, max=300)),
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period
    },
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_devices: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None
) -> None:
    async_add_devices(
        [
            OwncastParserSensor(
                hass=hass,
                name = config[CONF_NAME],
                server_url = config[CONF_SERVER_URL],
                timeout = config[CONF_TIMEOUT],
                verify_ssl = config[CONF_VERIFY_SSL],
                scan_interval = config[CONF_SCAN_INTERVAL]
            ),
        ],
        update_before_add=True,
    )

class OwncastParserSensor(SensorEntity):
    _attr_force_update = True

    def __init__(
            self: OwncastParserSensor,
            hass: HomeAssistant,
            name: str,
            server_url: str,
            timeout: int,
            verify_ssl: bool,
    ) -> None:
        self._hass = hass
        self._name = name
        self._server_url = server_url
        self._timeout = timeout
        self._verify_ssl = verify_ssl

        # State & Attributes
        self._attr_native_value = None # "online" / "offline"
        self._attr_extra_state_attributes = {
            "url": server_url,
            "response_time_ms": None,
            "live": None,
            "viewers": None,
            "topic": None,
            "time_online": None
        }

    async def async_update(self) -> None:
        session = async_get_clientsession(self._hass, verify_ssl=self._verify_ssl)

        attrs = self._attr_extra_state_attributes

        try:
            async with async_timeout.timeout(self._timeout):
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                start = self._hass.loop.time()
                async with session.get(self._server_url, timeout=timeout) as resp:
                    data: Any | None = None
                    content_type = resp.headers.get("Content-Type", "")
                    if "application/json" in content_type.lower():
                        data = await resp.json()
                    else:
                        data = await resp.read()
                        _LOGGER.debug(F"Owncast status fetch for {self._url} failed: unusual API response: {data}")
                        self._attr_native_value = "error"
                elapsed_ms = int((self._hass.loop.time() - start) * 1000)
                attrs["response_time_ms"] = elapsed_ms

                if isinstance(data, dict):
                    self._attr_available = True
                    attrs["live"] = data.get("online") or False
                    attrs["viewers"] = data.get("viewerCount")
                    attrs["topic"] = "Not Implemented Yet" # FIXME
                    attrs["time_online"] = "Not Implemented Yet" #FIXME

        except (aiohttp.ClientError, asyncio.TimeoutError) as err:
            _LOGGER.debug(f"Owncast status check failed for {self._server_url}: {err}")
            self._attr_native_value = "offline"
            self._attr_available = False
        except Exception as err:
            _LOGGER.debug(f"Unexpected error checking {self._server_url}")
            self._attr_native_value = "offline"
            self._attr_available = False