"""Constants for the Grundig Connect (COSA) integration — socket.io real-time."""
from __future__ import annotations

import logging

DOMAIN = "grundig_connect"
LOGGER = logging.getLogger(__package__)

CONF_EMAIL = "email"
CONF_PASSWORD = "password"

# HA modlar: tam set (fan_only + auto dahil)
FAN_MODES = ["auto", "1", "2", "3", "4", "5"]
SWING_MODES = ["oto", "1", "2", "3", "4", "5"]
HSWING_MODES = ["oto", "1", "2", "3", "4", "5", "left", "right", "off"]
MIN_TEMP = 18
MAX_TEMP = 30
