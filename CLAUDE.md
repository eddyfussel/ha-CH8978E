# CLAUDE.md — Project Guide for AI Assistants

This file gives a future Claude session everything it needs to work productively in this repo without re-deriving context from scratch.

---

## What this project is

A **Home Assistant custom component** (`pyur_modem`) that exposes sensor data from a **Pyur Compal CH8978E** cable modem. The modem is reachable at `https://192.168.100.1`.

The component polls the modem every 60 seconds and surfaces all available data as HA sensor and binary-sensor entities under one device.

---

## Repo layout

```
ha-CH8978E/
├── custom_components/pyur_modem/   # The HA integration
│   ├── __init__.py                 # Entry setup / unload, defines PyurModemConfigEntry
│   ├── config_flow.py              # UI config flow (host, username, password)
│   ├── coordinator.py              # DataUpdateCoordinator — wraps sync client in executor
│   ├── sensor.py                   # 9 sensor entities
│   ├── binary_sensor.py            # 1 binary sensor (is_operational / connectivity)
│   ├── const.py                    # DOMAIN, DEFAULT_SCAN_INTERVAL, DEFAULT_TIMEOUT
│   ├── manifest.json               # HA integration manifest (version, iot_class, …)
│   ├── strings.json                # Config flow UI strings (source of truth)
│   ├── translations/en.json        # English translations (identical to strings.json)
│   └── pyur_modem_lib/             # Bundled modem client library (not on PyPI)
│       ├── __init__.py             # Re-exports PyurModemClient
│       └── client.py               # PyurModemClient, ModemData, AuthError, ParseError
├── tests/
│   ├── conftest.py                 # Fixtures: MOCK_MODEM_DATA, mock_client, enable_custom_integrations
│   └── test_config_flow.py         # 6 config flow tests
├── config/                         # Local HA dev instance config dir
│   └── configuration.yaml          # Minimal HA config for dev (committed)
├── conftest.py                     # Root conftest — sys.path + custom_components.__path__ fix
├── pyproject.toml                  # Project metadata + dev deps + ruff config
├── Taskfile.yml                    # Developer workflow (see below)
└── uv.lock                         # Locked dependency graph (committed)
```

---

## Development workflow

### Prerequisites (macOS)

```bash
brew install python@3.14 uv go-task
```

### First time

```bash
task setup   # installs .venv with HA 2026.5.1 + test/lint deps, creates symlink
```

### Daily

```bash
task run     # starts HA at http://localhost:8123
task test    # runs unit tests (no running HA needed)
task lint    # ruff check
task clean   # resets HA state (DB, storage, logs) — keeps deps and symlink
```

`task setup` is idempotent (guarded by `status` checks); subsequent calls are instant.

### How `task run` works

- Runs `.venv/bin/hass -c config`
- Sets `CPATH=/Library/Developer/CommandLineTools/SDKs/MacOSX.sdk/usr/include/c++/v1` — required on macOS because Xcode CLT 21+ ships C++ standard headers inside the SDK rather than the global include path. Without it, HA's runtime C-extension builds (e.g. `pymicro-vad`, `pyspeex-noise`) fail with `cstdint not found`.
- The component is loaded via a symlink: `config/custom_components/pyur_modem → custom_components/pyur_modem`
- Source file changes are picked up on HA restart (Ctrl-C → `task run`)

---

## Key architectural decisions

### Bundled library
`pyur_modem_lib/` is a verbatim copy of the [`py-CH8978E`](https://github.com/eddyfussel/py-CH8978E) library repo. It is bundled because the library is not on PyPI. `manifest.json` keeps `"requirements": []`. When the library is published to PyPI, delete `pyur_modem_lib/` and add it to `requirements` instead.

### Sync HTTP client wrapped in executor
`PyurModemClient` uses `requests` (synchronous). It is called via `hass.async_add_executor_job()` in `coordinator.py` to avoid blocking the HA event loop.

### `entry.runtime_data` (HA 2024.4+ API)
The coordinator is stored on `entry.runtime_data` — **not** in `hass.data[DOMAIN]`. This is the modern HA pattern. Both `sensor.py` and `binary_sensor.py` access it as `entry.runtime_data`.

### Python / HA version
- HA 2026.5.1 requires **Python 3.14.2+**
- `pytest-homeassistant-custom-component==0.13.330` is the test package that pins this HA version
- `pyproject.toml` targets `py314`

### `--no-install-project` in uv
`uv sync --no-install-project` is intentional. Installing this project as a Python package adds a synthetic path hook to `custom_components.__path__` that breaks HA's integration loader (`os.listdir` on a non-directory path). The component is discovered via the `config/custom_components/` symlink instead.

### `config/custom_components/` symlink
`task setup` creates `config/custom_components/pyur_modem → <abs-path>/custom_components/pyur_modem` using an absolute symlink. It removes any pre-existing target first (`rm -rf`) to avoid a known `ln -sf` footgun: if the target is already a directory, `ln -sf` places the symlink *inside* it instead of replacing it.

---

## Testing

Tests use `pytest-homeassistant-custom-component` which provides a `hass` fixture without a running HA instance.

Critical test fixtures (in `tests/conftest.py`):
- `auto_enable_custom_integrations` (autouse) — HA test instances block custom component discovery by default; this fixture re-enables it.
- `mock_client` — `MagicMock` for `PyurModemClient` with `.login`, `.fetch`, `.logout`.
- `MOCK_MODEM_DATA` — a fully populated `ModemData` instance.

Tests that create a config entry (`test_successful_setup`, `test_duplicate_entry_aborted`) must patch **both** import sites:
- `custom_components.pyur_modem.config_flow.PyurModemClient` (validation in config flow)
- `custom_components.pyur_modem.PyurModemClient` (coordinator setup in `__init__.py`)

Without the second patch, HA calls `async_setup_entry` after entry creation and the real client attempts a socket connection, triggering `HASocketBlockedError` in test teardown.

---

## Common tasks for an AI assistant

| Goal | What to do |
|---|---|
| Add a new sensor | Add a `PyurSensorEntityDescription` entry to `SENSOR_DESCRIPTIONS` in `sensor.py` with a `value_fn` that reads the right field from `ModemData` |
| Add a new `ModemData` field | Edit `pyur_modem_lib/client.py` (sync with `py-CH8978E` source), then expose it via sensor.py |
| Change poll interval | `const.py` → `DEFAULT_SCAN_INTERVAL` |
| Change config flow fields | `config_flow.py` + `strings.json` + `translations/en.json` |
| Run only one test | `.venv/bin/pytest tests/test_config_flow.py::test_successful_setup -v` |
| Check HA logs during dev | `tail -f config/home-assistant.log` (debug level for `custom_components.pyur_modem` is set in `configuration.yaml`) |
