from __future__ import annotations

import asyncio
from datetime import timedelta
import logging
from typing import Any, Final, TYPE_CHECKING

import aiohttp
import async_timeout
import voluptuous as vol

from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.const import CONF_NAME, CONF_SCAN_INTERVAL
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.aiohttp_client import async_get_clientsession

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

# YAML Sensor Variables
CONF_OWNCAST_URL = "owncast_url"
CONF_TIMEOUT = "timeout"
CONF_VERIFY_SSL = "verify"

# Default Values
DEFAULT_TIMEOUT = 10 # Seconds
DEFAULT_VERIFY_SSL = True
DEFAULT_SCAN_INTERVAL = timedelta(minutes=1)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_OWNCAST_URL): cv.string, # can this be replaced with a builtin?
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int, # can this be replaced with a builtin?
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean, # can this be replaced with a builtin?
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
                url=config[CONF_OWNCAST_URL],
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
        self._url = url
        self._attr_name = name
        self._attr_icon = "mdi:something"
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._scan_interval = scan_interval
        self._attr_extra_state_attributes = {"viewers": 0}
        self._attr_attribution = "Data retrieved using Owncast Parser"
        _LOGGER.debug(f"Owncast Tracker for {self.name} initialized.")

    async def async_update(self: OwncastParserSensor) -> None:
        _LOGGER.debug(f"Owncast Tracker {self.name} pulling current data from {self._url}")
        session = async_get_clientsession(self._hass, verify_ssl=self._verify_ssl)
        
        attrs = self._attr_extra_state_attributes
        try:
            async with async_timeout.timeout(self._timeout):
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                start_time = self._hass.loop.time()
                async with session.get(self._url, timeout=timeout) as response:
                    data: Any | None = None
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type.lower():
                        data = await response.json()
                    else:
                        data = await response.read()
                        _LOGGER.debug(f"Owncast status fetch for {self._url} failed: unusual API response: {data}")
                        self._attr_native_value = "offline"
                elapsed_time = int((self._hass.loop.time() - start_time) * 1000)
                # set reponse time attr

                if isinstance(data, dict):
                    self._attr_available = True
                    attrs["viewers"] = data.get("online") or 0
        except (aiohttp.ClientError, asyncio.TimeoutError) as error:
            _LOGGER.warning(f"Owncast status check failed for {self._url}: {error}")
            self._attr_native_value = "offline"
            self._attr_available = False
        except Exception as error:
            _LOGGER.warning(f"Unexpected error checking Owncast Server {self._url}: {error}")
            self._attr_native_value = "offline"
            self._attr_available = False
        _LOGGER.debug(f"Owncast state updated for {self._url}.")
        