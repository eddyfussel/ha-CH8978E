"""Sensor platform for the Pyur Modem integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import PyurModemCoordinator
from .pyur_modem_lib.client import ModemData

PARALLEL_UPDATES = 1


@dataclass(frozen=True, kw_only=True)
class PyurSensorEntityDescription(SensorEntityDescription):
    """Extends SensorEntityDescription with a typed value accessor."""

    value_fn: Callable[[ModemData], Any]


SENSOR_DESCRIPTIONS: tuple[PyurSensorEntityDescription, ...] = (
    PyurSensorEntityDescription(
        key="cm_status",
        name="CM Status",
        icon="mdi:cable-data",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.cm_status,
    ),
    PyurSensorEntityDescription(
        key="docsis_version",
        name="DOCSIS Version",
        icon="mdi:information-outline",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.docsis_version,
    ),
    PyurSensorEntityDescription(
        key="device_mode",
        name="Device Mode",
        icon="mdi:router-network",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.device_mode,
    ),
    PyurSensorEntityDescription(
        key="mac_address",
        name="MAC Address",
        icon="mdi:ethernet",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.mac_address,
    ),
    PyurSensorEntityDescription(
        key="serial_number",
        name="Serial Number",
        icon="mdi:barcode",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.serial_number,
    ),
    PyurSensorEntityDescription(
        key="firmware_version",
        name="Firmware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.firmware_version,
    ),
    PyurSensorEntityDescription(
        key="hardware_version",
        name="Hardware Version",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
        entity_registry_enabled_default=False,
        value_fn=lambda d: d.hardware_version,
    ),
    PyurSensorEntityDescription(
        key="current_time",
        name="Modem Time",
        device_class=SensorDeviceClass.TIMESTAMP,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda d: d.current_time,
    ),
    PyurSensorEntityDescription(
        key="uptime_seconds",
        name="Uptime",
        device_class=SensorDeviceClass.DURATION,
        state_class=SensorStateClass.TOTAL_INCREASING,
        native_unit_of_measurement=UnitOfTime.SECONDS,
        icon="mdi:timer-outline",
        value_fn=lambda d: d.uptime_seconds or None,
    ),
)


def _build_device_info(coordinator: PyurModemCoordinator) -> DeviceInfo:
    data = coordinator.data
    return DeviceInfo(
        identifiers={(DOMAIN, data.mac_address or data.serial_number)},
        name="Pyur CH8978E Modem",
        manufacturer="Compal",
        model="CH8978E",
        sw_version=data.firmware_version,
        hw_version=data.hardware_version,
        serial_number=data.serial_number,
    )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: PyurModemCoordinator = entry.runtime_data
    async_add_entities(
        PyurModemSensor(coordinator, description)
        for description in SENSOR_DESCRIPTIONS
    )


class PyurModemSensor(CoordinatorEntity[PyurModemCoordinator], SensorEntity):
    """Represents one ModemData field as a sensor entity."""

    _attr_has_entity_name = True
    entity_description: PyurSensorEntityDescription

    def __init__(
        self,
        coordinator: PyurModemCoordinator,
        description: PyurSensorEntityDescription,
    ) -> None:
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.data.mac_address}_{description.key}"
        )
        self._attr_device_info = _build_device_info(coordinator)

    @property
    def native_value(self) -> Any:
        return self.entity_description.value_fn(self.coordinator.data)
