"""Grundig Turbo switch (acTurbo) — climate preset yerine ayri kontrol."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GrundigConfigEntry
from .const import DOMAIN
from .coordinator import GrundigCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrundigConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        GrundigTurboSwitch(coordinator, ep_id) for ep_id in coordinator.endpoints
    )


class GrundigTurboSwitch(CoordinatorEntity[GrundigCoordinator], SwitchEntity):
    _attr_has_entity_name = True
    _attr_name = "Turbo"
    _attr_icon = "mdi:fan-plus"

    def __init__(self, coordinator: GrundigCoordinator, ep_id: str) -> None:
        super().__init__(coordinator)
        self._ep = ep_id
        self._attr_unique_id = f"grundig_{ep_id}_turbo"
        self._attr_device_info = {"identifiers": {(DOMAIN, ep_id)}}

    @property
    def _s(self) -> dict:
        return (self.coordinator.data or {}).get(self._ep) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._s)

    @property
    def is_on(self) -> bool:
        return bool(self._s.get("turbo"))

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.send_ac_state(self._ep, "acTurbo", 1)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.send_ac_state(self._ep, "acTurbo", 0)
