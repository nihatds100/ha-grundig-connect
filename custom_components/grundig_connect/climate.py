"""Grundig Connect climate — socket.io gercek-zamanli. HA = SAF AYNA.

- HA kendi derece BASMAZ; derece HER ZAMAN cloud'dan gelir.
  SWITCH (farkli mod): yalniz acMode -> cloud default (cool=18/heat=30), HA gosterir.
  RESUME (ayni mod, kapali): yalniz acPower=1 -> cloud son state'i getirir.
- Dikey + YATAY salinim (native SWING_HORIZONTAL) kartta ayri acilirlarda.
- Turbo climate'te DEGIL, ayri switch entity'sinde.
"""
from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import GrundigConfigEntry
from .api import HA_FAN_TO_AC, HA_HSWING_TO_AC, HA_MODE_TO_AC, HA_VSWING_TO_AC, NO_TEMP_MODES
from .const import DOMAIN, FAN_MODES, HSWING_MODES, MAX_TEMP, MIN_TEMP, SWING_MODES
from .coordinator import GrundigCoordinator

HA_TO_HVAC = {
    "off": HVACMode.OFF,
    "cool": HVACMode.COOL,
    "dry": HVACMode.DRY,
    "fan_only": HVACMode.FAN_ONLY,
    "heat": HVACMode.HEAT,
    "auto": HVACMode.AUTO,
}
HVAC_TO_HA = {v: k for k, v in HA_TO_HVAC.items()}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: GrundigConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        GrundigClimate(coordinator, ep_id, name)
        for ep_id, name in coordinator.endpoints.items()
    )


class GrundigClimate(CoordinatorEntity[GrundigCoordinator], ClimateEntity):
    """Bir Grundig klimayi temsil eder (gercek-zamanli, saf ayna)."""

    _attr_has_entity_name = True
    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_hvac_modes = [
        HVACMode.OFF,
        HVACMode.COOL,
        HVACMode.DRY,
        HVACMode.FAN_ONLY,
        HVACMode.HEAT,
        HVACMode.AUTO,
    ]
    _attr_fan_modes = FAN_MODES
    _attr_swing_modes = SWING_MODES
    _attr_swing_horizontal_modes = HSWING_MODES
    _attr_min_temp = MIN_TEMP
    _attr_max_temp = MAX_TEMP
    _attr_target_temperature_step = 1.0

    def __init__(
        self, coordinator: GrundigCoordinator, ep_id: str, name: str
    ) -> None:
        super().__init__(coordinator)
        self._ep = ep_id
        self._attr_unique_id = f"grundig_{ep_id}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, ep_id)},
            "name": name,
            "manufacturer": "Grundig",
            "model": "Connect AC",
        }

    @property
    def _s(self) -> dict:
        return (self.coordinator.data or {}).get(self._ep) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._s) and self._s.get("connected", True)

    @property
    def supported_features(self) -> ClimateEntityFeature:
        feat = (
            ClimateEntityFeature.FAN_MODE
            | ClimateEntityFeature.SWING_MODE
            | ClimateEntityFeature.SWING_HORIZONTAL_MODE
            | ClimateEntityFeature.TURN_ON
            | ClimateEntityFeature.TURN_OFF
        )
        s = self._s
        if s.get("on") and s.get("mode") not in NO_TEMP_MODES:
            feat |= ClimateEntityFeature.TARGET_TEMPERATURE
        return feat

    @property
    def hvac_mode(self) -> HVACMode | None:
        s = self._s
        if not s:
            return None
        if not s.get("on"):
            return HVACMode.OFF
        return HA_TO_HVAC.get(s.get("mode"), HVACMode.COOL)

    @property
    def fan_mode(self) -> str | None:
        return self._s.get("fan_mode", "auto")

    @property
    def swing_mode(self) -> str | None:
        return self._s.get("vertical_swing", "oto")

    @property
    def swing_horizontal_mode(self) -> str | None:
        return self._s.get("horizontal_swing", "off")

    @property
    def target_temperature(self) -> float | None:
        v = self._s.get("target_temperature")
        return None if v is None else float(v)

    @property
    def current_temperature(self) -> float | None:
        v = self._s.get("current_temperature")
        return None if v is None else float(v)

    # ---- komutlar ----
    async def _send(self, field: str, value: int) -> None:
        await self.coordinator.client.send_ac_state(self._ep, field, value)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._send("acPower", 0)
            return
        target = HVAC_TO_HA[hvac_mode]
        s = self._s
        if s.get("mode") == target:
            if not s.get("on"):
                await self._send("acPower", 1)  # RESUME: derece cloud'dan
            return
        await self._send("acMode", HA_MODE_TO_AC[target])  # SWITCH: derece cloud'dan

    async def async_turn_on(self) -> None:
        await self._send("acPower", 1)

    async def async_turn_off(self) -> None:
        await self._send("acPower", 0)

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        await self._send("acFanSpeed", HA_FAN_TO_AC[fan_mode])

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self._send("acVerticalSwing", HA_VSWING_TO_AC[swing_mode])

    async def async_set_swing_horizontal_mode(self, swing_horizontal_mode: str) -> None:
        await self._send("acHorizontalSwing", HA_HSWING_TO_AC[swing_horizontal_mode])

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temp = kwargs.get(ATTR_TEMPERATURE)
        if temp is None:
            return
        await self._send(
            "targetTemperature", max(MIN_TEMP, min(MAX_TEMP, int(round(float(temp)))))
        )
