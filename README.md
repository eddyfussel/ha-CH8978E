# ha-CH8978E — Pyur Cable Modem Integration for Home Assistant

> **Disclaimer:** This project was built with the assistance of [Claude](https://claude.ai) (Anthropic). All code, configuration, and documentation were AI-generated and reviewed by the repository owner. This software is provided **as-is, without any warranty of any kind**. The author accepts no liability for any damage, data loss, or malfunction arising from the use of this software. Use at your own risk — the modem's web interface is undocumented and may change with firmware updates.

A Home Assistant custom component that exposes status data from a **Pyur Compal CH8978E** cable modem as sensor entities.

The integration polls the modem's web interface every 60 seconds and surfaces all available data through the device registry.

---

## Available Entities

One **device** named *Pyur CH8978E Modem* is created with the following entities:

| Entity | Type | Description | Enabled by default |
|---|---|---|---|
| CM Status | Sensor | Raw connection status (e.g. `OPERATIONAL`) | ✓ |
| Operational | Binary Sensor | `On` when CM Status is `OPERATIONAL` | ✓ |
| DOCSIS Version | Sensor | DOCSIS protocol version (e.g. `3.1`) | ✓ |
| Device Mode | Sensor | `Bridge` or `Router` | ✓ |
| Firmware Version | Sensor | Installed firmware version | ✓ |
| Modem Time | Sensor | System time reported by the modem | ✓ |
| Uptime | Sensor | Time since last reboot in seconds | ✓ |
| MAC Address | Sensor | Cable modem MAC address | — |
| Serial Number | Sensor | Device serial number | — |
| Hardware Version | Sensor | Hardware revision | — |

Disabled-by-default entities can be enabled at any time in **Settings → Devices & Services → Pyur Cable Modem → device → entity**.

---

## Installing in Home Assistant OS (HASSOS)

### Method A — Manual file copy (no HACS required)

1. On your development machine, clone or download this repository.
2. Copy the folder `custom_components/pyur_modem/` into the `custom_components/` directory on your Home Assistant instance.

   **Via SSH add-on:**
   ```bash
   scp -r custom_components/pyur_modem/ homeassistant@<ha-ip>:/config/custom_components/
   ```

   **Via Samba add-on:** Open the `config` share, navigate to `custom_components/`, and paste the `pyur_modem` folder.

   **Via File Editor add-on:** Upload each file individually through the HA web UI.

3. Restart Home Assistant: **Settings → System → Restart**.
4. Go to **Settings → Devices & Services → Add Integration**, search for *Pyur Cable Modem*, and complete the setup form.

### Method B — HACS (custom repository)

1. Open HACS in your Home Assistant.
2. Click the three-dot menu → **Custom repositories**.
3. Add `https://github.com/eddyfussel/ha-CH8978E` with category **Integration**.
4. Search for *Pyur Cable Modem* in HACS and install it.
5. Restart Home Assistant.
6. Go to **Settings → Devices & Services → Add Integration** and complete the setup.

---

## Configuration

The integration is set up entirely through the UI. No YAML edits are needed.

**Settings → Devices & Services → Add Integration → Pyur Cable Modem**

| Field | Example value | Description |
|---|---|---|
| Host | `https://192.168.100.1` | IP address or URL of the modem. `https://` is added automatically if omitted. |
| Username | `admin` | Modem web interface username (default: `admin`) |
| Password | *(your password)* | Modem web interface password |

The integration validates the credentials by attempting a login before saving. If the modem is unreachable or the password is wrong, an error is shown inline.

> **Note:** The modem uses a self-signed HTTPS certificate. SSL verification is intentionally disabled.

### Re-authentication

If your modem password changes, Home Assistant will show a re-authentication notification. Go to **Settings → Devices & Services → Pyur Cable Modem → Re-authenticate** and enter the new credentials.

---

## Removing the Integration

1. Go to **Settings → Devices & Services**.
2. Find *Pyur Cable Modem* and click the three-dot menu → **Delete**.
3. All entities and the device entry are removed automatically.

If you installed via **manual file copy**, also delete the `custom_components/pyur_modem/` folder from your HA config directory and restart Home Assistant.

If you installed via **HACS**, use HACS → *Pyur Cable Modem* → **Remove**, then restart Home Assistant.

---

## Development

### Prerequisites

- Python 3.14.2+ (`brew install python@3.14`)
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- [Task](https://taskfile.dev) (`brew install go-task`)

### Quick start

```bash
# Clone the repository
git clone https://github.com/eddyfussel/ha-CH8978E
cd ha-CH8978E

# One-time: install dependencies and create the component symlink (~2 min)
task setup

# Start a local Home Assistant instance
task run
```

Open `http://localhost:8123` in your browser. Complete the one-time onboarding wizard, then go to **Settings → Devices & Services → Add Integration → Pyur Cable Modem** to add your modem.

`task setup` installs Home Assistant 2026.5 into `.venv` and symlinks `custom_components/pyur_modem` into `config/custom_components/`. Source file changes are picked up on the next HA restart (`Ctrl-C`, then `task run`).

### Available tasks

| Command | Description |
|---|---|
| `task setup` | Install dependencies and symlink component into `config/` (one-time) |
| `task run` | Start local Home Assistant at `http://localhost:8123` |
| `task test` | Run the unit test suite |
| `task lint` | Run `ruff` linter |
| `task clean` | Remove HA runtime files from `config/` (logs, database, `.storage/`) |

### Project structure

```
ha-CH8978E/
├── custom_components/
│   └── pyur_modem/          # The integration
│       ├── pyur_modem_lib/  # Bundled modem client library (from py-CH8978E)
│       ├── __init__.py
│       ├── config_flow.py
│       ├── coordinator.py
│       ├── sensor.py
│       ├── binary_sensor.py
│       ├── manifest.json
│       └── translations/
├── tests/                   # Unit tests (pytest)
├── config/                  # Local HA config dir (runtime data is gitignored)
├── Taskfile.yml
└── pyproject.toml
```

### Running tests

```bash
task test
# or directly:
.venv/bin/pytest tests/ -v
```

Tests use `pytest-homeassistant-custom-component`, which provides the `hass` fixture without needing a running HA instance.

### VS Code devcontainer

Open the repository in VS Code. When prompted, click **Reopen in Container**. The container uses the official HA devcontainer image and installs all dependencies automatically.

---

## Library

The modem communication is handled by the [`pyur_modem`](https://github.com/eddyfussel/py-CH8978E) Python library, bundled at `custom_components/pyur_modem/pyur_modem_lib/`.

The library reverse-engineers the modem's undocumented web interface and may break on firmware updates. Once published to PyPI, the bundled copy will be replaced with a `requirements` entry in `manifest.json`.

---

## License

MIT License — see [LICENSE.md](LICENSE.md).

