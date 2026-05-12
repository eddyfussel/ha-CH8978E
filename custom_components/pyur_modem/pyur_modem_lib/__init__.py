"""Pyur Compal CH8978E cable modem Python client.

Bundled from https://github.com/eddyfussel/py-CH8978E — update manually when the
upstream library changes, or replace with a PyPI requirement once published.
"""

from .client import ConnectionStatus, ModemData, PyurModemClient

__all__ = ["PyurModemClient", "ModemData", "ConnectionStatus"]
__version__ = "0.1.0"
