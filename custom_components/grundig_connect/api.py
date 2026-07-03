"""COSA / Grundig Connect — REST login + alan eslemeleri + state donusumu.

Gercek-zamanli iletisim socket_client.py'de (socket.io). Burada sadece:
- REST login (authToken almak icin),
- acMode/acFanSpeed/... <-> HA eslemeleri,
- ham endpoint dict -> HA state donusumu.
"""
from __future__ import annotations

import aiohttp

BASE = "https://kiwi.cosa.com.tr"
PROVIDER = "grundig"

# acMode: cool=0, dry=1, fan_only=2, heat=4, auto=6
HA_MODE_TO_AC = {"cool": 0, "dry": 1, "fan_only": 2, "heat": 4, "auto": 6}
AC_MODE_TO_HA = {0: "cool", 1: "dry", 2: "fan_only", 4: "heat", 6: "auto"}

HA_FAN_TO_AC = {"auto": 8, "1": 2, "2": 3, "3": 4, "4": 5, "5": 6}
AC_FAN_TO_HA = {v: k for k, v in HA_FAN_TO_AC.items()}

HA_VSWING_TO_AC = {"oto": 100, "1": 6, "2": 5, "3": 4, "4": 3, "5": 2}
AC_VSWING_TO_HA = {v: k for k, v in HA_VSWING_TO_AC.items()}

HA_HSWING_TO_AC = {"oto": 100, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5, "left": 13, "right": 35, "off": 0}
AC_HSWING_TO_HA = {v: k for k, v in HA_HSWING_TO_AC.items()}

MIN_TEMP, MAX_TEMP = 18, 30

# derece OLMAYAN modlar (kart derece surgusu bu modlarda gizlenir)
NO_TEMP_MODES = {"fan_only", "auto"}


class CosaAuthError(Exception):
    """Login / yetki hatasi."""


class CosaError(Exception):
    """Genel API hatasi."""


async def cosa_login(session: aiohttp.ClientSession, email: str, password: str) -> str:
    """REST ile login -> authToken (suresiz JWT)."""
    try:
        async with session.post(
            f"{BASE}/api/users/login",
            json={"email": email, "password": password},
            headers={"provider": PROVIDER},
            timeout=aiohttp.ClientTimeout(total=20),
        ) as r:
            data = await r.json()
    except aiohttp.ClientError as err:
        raise CosaError(f"Login baglanti hatasi: {err}") from err
    token = data.get("authToken")
    if not token:
        raise CosaAuthError(f"Login basarisiz: {data}")
    return token


def endpoint_to_ha_state(ep: dict) -> dict:
    """Ham COSA endpoint dict -> HA state (gercek mod + tum ozellikler)."""
    power = ep.get("acPower", 0)
    acmode = ep.get("acMode", 0)
    fan = ep.get("acFanSpeed", 8)
    target = ep.get("targetTemperature")
    if target is not None:
        target = max(MIN_TEMP, min(MAX_TEMP, target))
    device = ep.get("device") or {}
    return {
        "on": power == 1,
        "mode": AC_MODE_TO_HA.get(acmode, "cool"),
        "fan_mode": AC_FAN_TO_HA.get(fan, "auto"),
        "vertical_swing": AC_VSWING_TO_HA.get(ep.get("acVerticalSwing", 100), "oto"),
        "horizontal_swing": AC_HSWING_TO_HA.get(ep.get("acHorizontalSwing", 0), "off"),
        "target_temperature": target,
        "current_temperature": ep.get("temperature"),
        "turbo": ep.get("acTurbo", 0) == 1,
        "instant_power": ep.get("acInstantPower"),
        "energy": ep.get("acPowerConsumption"),
        "connected": bool(ep.get("isConnected", device.get("isConnected", True))),
    }
