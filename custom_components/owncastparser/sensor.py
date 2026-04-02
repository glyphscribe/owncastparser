from __future__ import annotations

from typing import Any, TYPE_CHECKING
from datetime import timedelta
import asyncio
import logging
import time

import aiohttp
import voluptuous as vol

import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import SensorEntity, PLATFORM_SCHEMA
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_NAME, CONF_URL, CONF_TIMEOUT, CONF_VERIFY_SSL
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN, DEFAULT_TIMEOUT, DEFAULT_VERIFY_SSL, DEFAULT_SCAN_INTERVAL

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant
    from homeassistant.helpers.entity_platform import AddEntitiesCallback
    from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_NAME): cv.string,
        vol.Required(CONF_URL): cv.url,
        vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): cv.positive_int,
        vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): cv.boolean,
    },
)

_LOGGER: logging.Logger = logging.getLogger(__name__)


async def async_setup_platform(
        hass: HomeAssistant,
        config: ConfigType,
        async_add_devices: AddEntitiesCallback,
        discovery_info: DiscoveryInfoType | None = None,
) -> None:
    _LOGGER.warning(
        "Configuration of Owncast Parser via YAML is deprecated. "
        "Please configure via Settings > Devices & Services."
    )
    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN,
            context={"source": SOURCE_IMPORT},
            data={
                CONF_NAME: config[CONF_NAME],
                CONF_URL: config[CONF_URL],
                CONF_TIMEOUT: config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                CONF_VERIFY_SSL: config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            },
        )
    )


async def async_setup_entry(
        hass: HomeAssistant,
        config_entry: ConfigEntry,
        async_add_entities: AddEntitiesCallback,
) -> None:
    data = config_entry.data
    async_add_entities(
        [
            OwncastParserSensor(
                url=data[CONF_URL],
                name=data[CONF_NAME],
                timeout=data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                verify_ssl=data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                entry_id=config_entry.entry_id,
            ),
        ],
        update_before_add=True,
    )


class OwncastParserSensor(SensorEntity):
    _attr_force_update = True
    _attr_has_entity_name = True

    SCAN_INTERVAL = DEFAULT_SCAN_INTERVAL

    def __init__(
            self: OwncastParserSensor,
            url: str,
            name: str,
            timeout: int,
            verify_ssl: bool,
            entry_id: str,
    ) -> None:
        self._url = url.rstrip('/') + '/api/status'
        self._attr_name = name
        self._attr_unique_id = f"owncast_{entry_id}"
        self._attr_icon = "mdi:video-off-outline"
        self._timeout = timeout
        self._verify_ssl = verify_ssl
        self._attr_extra_state_attributes = {}
        self._attr_attribution = "Data retrieved using Owncast Parser"
        _LOGGER.debug(f"Owncast Parser for {self._url} initialized.")

    async def async_update(self: OwncastParserSensor) -> None:
        _LOGGER.debug(
            f"Owncast Parser attempting to read state data from: {self._url}")
        session = async_get_clientsession(
            self.hass, verify_ssl=self._verify_ssl)

        attrs = self._attr_extra_state_attributes
        try:
            async with asyncio.timeout(self._timeout):
                timeout = aiohttp.ClientTimeout(total=self._timeout)
                start_time = time.monotonic()

                async with session.get(self._url, timeout=timeout) as response:
                    data: Any | None = None
                    content_type = response.headers.get("Content-Type", "")
                    if "application/json" in content_type.lower():
                        if response.content_length and response.content_length > 1_000_000:
                            _LOGGER.warning(
                                "Owncast API response too large, skipping")
                            self._attr_native_value = "offline"
                            return
                        data = await response.json()
                    else:
                        data = await response.read()
                        _LOGGER.debug(
                            f"Owncast Parser fetch for {self._url} failed with unusual API response: {data}")
                        self._attr_native_value = "offline"

                elapsed_time = int((time.monotonic() - start_time) * 1000)
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
            _LOGGER.warning(
                f"Owncast Parser fetch failed for {self._url}: {error}")
            self._attr_native_value = "offline"
            self._attr_available = False

        except Exception as error:
            _LOGGER.warning(
                f"Owncast Parser failed to fetch {self._url} with unusual error: {error}")
            self._attr_native_value = "offline"
            self._attr_available = False

        _LOGGER.debug(f"Owncast state updated for {self._url}.")
