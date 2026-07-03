<p align="center">
  <img src="logo.png" alt="HA Grundig Connect" width="200"/>
</p>

<h1 align="center">HA Grundig Connect</h1>

<p align="center">
  Real-time Home Assistant integration for <b>Grundig Connect</b> air conditioners.
</p>

<p align="center">
  <a href="https://my.home-assistant.io/redirect/hacs_repository/?owner=nihatds100&repository=ha-grundig-connect&category=integration">
    <img src="https://my.home-assistant.io/badges/hacs_repository.svg" alt="Add repository to HACS">
  </a>
  <a href="https://my.home-assistant.io/redirect/config_flow_start/?domain=grundig_connect">
    <img src="https://my.home-assistant.io/badges/config_flow_start.svg" alt="Add integration to Home Assistant">
  </a>
</p>

---

## ✨ Features

- **Real-time** state over a persistent WebSocket push connection — no polling, changes appear instantly (even when set from the vendor app or remote)
- Full HVAC modes: **off / cool / dry / fan only / heat / auto**
- Target temperature and fan speed
- **Vertical *and* horizontal swing** — both inside the standard thermostat card
- **Turbo** switch
- **Instant power** (W) and **energy** (Wh) sensors — ready for the HA Energy Dashboard
- **Outdoor temperature** sensor
- Simple UI setup — just your account e-mail and password

## 📦 Installation

### HACS (recommended)

1. In HACS open the **⋮** menu → **Custom repositories**
2. Add `https://github.com/nihatds100/ha-grundig-connect` with category **Integration**
3. Install **HA Grundig Connect** and restart Home Assistant

[![Add repository to HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=nihatds100&repository=ha-grundig-connect&category=integration)

### Manual

Copy `custom_components/grundig_connect` into your Home Assistant `config/custom_components/` directory and restart.

## ⚙️ Configuration

**Settings → Devices & Services → Add Integration → “Grundig Connect”**, then enter your account **e-mail** and **password**. Everything else is handled automatically.

[![Add integration to Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=grundig_connect)

## 🔌 Provided entities

| Entity | Description |
|--------|-------------|
| `climate.*` | Air conditioner — mode, target temperature, fan, vertical + horizontal swing |
| `switch.*_turbo` | Turbo (boost) mode |
| `sensor.*` power | Instantaneous power draw (W) |
| `sensor.*` energy | Cumulative energy (Wh) — add it to the Energy Dashboard |
| `sensor.*` outdoor temp | Measured outdoor temperature (°C) |

## ⚠️ Disclaimer

This is an **unofficial**, community-built integration. It is **not affiliated with, endorsed by, or supported by** the manufacturer or any brand owner. It talks to the vendor's private cloud interface, which may change at any time without notice and break this integration. **Use at your own risk** — the author accepts no liability for any damage or data loss.

## 📄 License

[PolyForm Noncommercial License 1.0.0](LICENSE) — free for **noncommercial** use. Commercial use is not permitted.
