"""Grundig sensorleri: anlik guc (W), enerji tuketimi (Wh), olculen dis sicaklik."""
from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import UnitOfEnergy, UnitOfPower, UnitOfTemperature
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
    entities: list[SensorEntity] = []
    for ep_id in coordinator.endpoints:
        entities.append(GrundigPowerSensor(coordinator, ep_id))
        entities.append(GrundigEnergySensor(coordinator, ep_id))
        entities.append(GrundigOutsideTempSensor(coordinator, ep_id))
    async_add_entities(entities)


class _GrundigSensorBase(CoordinatorEntity[GrundigCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: GrundigCoordinator, ep_id: str, key: str, suffix: str
    ) -> None:
        super().__init__(coordinator)
        self._ep = ep_id
        self._key = key
        self._attr_unique_id = f"grundig_{ep_id}_{suffix}"
        self._attr_device_info = {"identifiers": {(DOMAIN, ep_id)}}

    @property
    def _s(self) -> dict:
        return (self.coordinator.data or {}).get(self._ep) or {}

    @property
    def available(self) -> bool:
        return super().available and bool(self._s)

    @property
    def native_value(self):
        return self._s.get(self._key)


class GrundigPowerSensor(_GrundigSensorBase):
    _attr_translation_key = "anlik_guc"
    _attr_name = "Anlık Güç"
    _attr_device_class = SensorDeviceClass.POWER
    _attr_native_unit_of_measurement = UnitOfPower.WATT
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GrundigCoordinator, ep_id: str) -> None:
        super().__init__(coordinator, ep_id, "instant_power", "power")


class GrundigEnergySensor(_GrundigSensorBase):
    # acPowerConsumption = kumulatif enerji (Wh); periyodik sifirlanir -> total_increasing.
    _attr_name = "Enerji Tüketimi"
    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = UnitOfEnergy.WATT_HOUR
    _attr_state_class = SensorStateClass.TOTAL_INCREASING

    def __init__(self, coordinator: GrundigCoordinator, ep_id: str) -> None:
        super().__init__(coordinator, ep_id, "energy", "consumption")


class GrundigOutsideTempSensor(_GrundigSensorBase):
    _attr_has_entity_name = False
    _attr_name = "Grundig Ölçülen Dış Sıcaklık"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: GrundigCoordinator, ep_id: str) -> None:
        super().__init__(coordinator, ep_id, "outside_temperature", "outside_temp")
