"""Binary sensor platform for the Pyur Modem integration."""
from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .coordinator import PyurModemCoordinator
from .sensor import _build_device_info  # noqa: PLC2701

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PyurModemCoordinator = entry.runtime_data
    async_add_entities([PyurOperationalSensor(coordinator)])


class PyurOperationalSensor(CoordinatorEntity[PyurModemCoordinator], BinarySensorEntity):
    """Binary sensor that reflects whether the modem is fully operational."""

    _attr_has_entity_name = True
    _attr_name = "Operational"
    _attr_device_class = BinarySensorDeviceClass.CONNECTIVITY

    def __init__(self, coordinator: PyurModemCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.data.mac_address}_is_operational"
        self._attr_device_info = _build_device_info(coordinator)

    @property
    def is_on(self) -> bool:
        return self.coordinator.data.is_operational
