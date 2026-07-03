"""Grundig Connect (COSA) entegrasyonu — socket.io gercek-zamanli."""
from __future__ import annotations

import asyncio

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_EMAIL, CONF_PASSWORD
from .coordinator import GrundigCoordinator
from .socket_client import CosaSocketClient

PLATFORMS = [Platform.CLIMATE, Platform.SENSOR, Platform.SWITCH]

type GrundigConfigEntry = ConfigEntry[GrundigCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: GrundigConfigEntry) -> bool:
    session = async_get_clientsession(hass)
    client = CosaSocketClient(
        session, entry.data[CONF_EMAIL], entry.data[CONF_PASSWORD]
    )
    coordinator = GrundigCoordinator(hass, entry, client)
    await client.start()
    try:
        await client.wait_ready(30)
    except (asyncio.TimeoutError, Exception) as err:  # noqa: BLE001
        await client.stop()
        raise ConfigEntryNotReady(f"Cosa socket'e baglanilamadi: {err}") from err

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: GrundigConfigEntry) -> bool:
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.client.stop()
    return unloaded
