from __future__ import annotations

from typing import Any, TYPE_CHECKING
from datetime import timedelta
import asyncio
import logging

import aiohttp
import async_timeout
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_URL, CONF_TIMEOUT, CONF_VERIFY_SSL, CONF_SCAN_INTERVAL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

# Default Values
DEFAULT_TIMEOUT = 10 # Seconds
DEFAULT_VERIFY_SSL = True
DEFAULT_SCAN_INTERVAL = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_URL): cv.url,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period
    },
)

_LOGGER: logging.Logger = logging.getLogger(__name__)

async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_devices: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
) -> None:
    async_add_devices(
        [
            OwncastParserSensor(
                url=config[CONF_URL],
                name=config[CONF_NAME],
                timeout=config[CONF_TIMEOUT],
                verify_ssl=config[CONF_VERIFY_SSL],
                scan_interval=config[CONF_SCAN_INTERVAL]
            ),
        ],
        update_before_add=True,
    )

class OwncastParserSensor(SensorEntity):
    _attr_force_update = True

    def __init__(
            self: OwncastParserSensor,
            url: str,
            name: str,
            timeout: int,
            verify_ssl: bool,
            scan_interval: timedelta
    ) -> None:
        self._url = url.rstrip('/') + '/api/status'
        self._attr_name = name
        self._attr_icon = "mdi:video-off-outline"
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._scan_interval = scan_interval
        self._attr_extra_state_attributes = {}
        self._attr_attribution = "Data retrieved using Owncast Parser"
        _LOGGER.debug(f"Owncast Parser for {self._url} initialized.")

    async def async_update(self: OwncastParserSensor) -> None:
        _LOGGER.debug(f"Owncast Parser attempting to read state data from: {self._url}")
        session = async_get_clientsession(self.hass, verify_ssl=self._verify_ssl)
        
        attrs = self._attr_extra_state_attributes
        try:
            async with async_timeout.timeout(self._timeout):
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                start_time = self.hass.loop.time()
                async with session.get(self._url, timeout=timeout) as response:
                    data: Any | None = None
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type.lower():
                        data = await response.json()
                    else:
                        data = await response.read()
                        _LOGGER.debug(f"Owncast Parser fetch for {self._url} failed with unusual API response: {data}")
                        self._attr_native_value = "offline"
                elapsed_time = int((self.hass.loop.time() - start_time) * 1000)
                attrs["response_time"] = elapsed_time

                if isinstance(data, dict):
                    self._attr_available = True
                    attrs["viewers"] = data.get("viewerCount", 0)

                    if data.get("online", False) == True:
                        attrs["stream_title"] = data.get("streamTitle", "")
                        self._attr_native_value = "online"
                        self._attr_icon = "mdi:video-outline"
                    else:
                        attrs["stream_title"] = ""
                        self._attr_native_value = "offline"
                        self._attr_icon = "mdi:video-off-outline"

        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.warning(f"Owncast Parser fetch failed for {self._url}: {error}")
            self._attr_native_value = "offline"
            self._attr_available = False

        except Exception as error:
            _LOGGER.warning(f"Owncast Parser failed to fetch {self._url} with unusual error: {error}")
            self._attr_native_value = "offline"
            self._attr_available = False
            
        _LOGGER.debug(f"Owncast state updated for {self._url}.")
