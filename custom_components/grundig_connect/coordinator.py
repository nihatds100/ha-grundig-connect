"""Grundig Connect — push-mode coordinator (socket.io besler, polling YOK)."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .const import DOMAIN, LOGGER
from .socket_client import CosaSocketClient


class GrundigCoordinator(DataUpdateCoordinator[dict]):
    """Durumu socket.io push'larindan alir; update_interval yok."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: CosaSocketClient
    ) -> None:
        super().__init__(
            hass, LOGGER, name=DOMAIN, update_interval=None, config_entry=entry
        )
        self.client = client
        self.endpoints: dict[str, str] = {}
        client.set_callback(self._on_update)

    @callback
    def _on_update(self, ep_id: str, name: str, ha_state: dict) -> None:
        """Socket'ten gelen her guncellemeyi entity'lere anlik yansit."""
        self.endpoints[ep_id] = name
        data = dict(self.data or {})
        data[ep_id] = ha_state
        self.async_set_updated_data(data)
