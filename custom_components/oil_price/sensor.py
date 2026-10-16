"""Sensor platform for China Oil Price."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)

from .const import (
    DOMAIN,
    ICON_HINT,
    ICON_STATION,
    OIL_TYPES,
    UNIT_PRICE,
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    coordinator: DataUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]

    entities: list[SensorEntity] = [
        OilPriceSensor(coordinator, entry, oil_type) for oil_type in OIL_TYPES
    ]
    entities.append(OilPriceHintSensor(coordinator, entry))
    async_add_entities(entities)


class OilPriceSensorBase(CoordinatorEntity, SensorEntity):
    """Common wiring for all oil_price entities (coordinator + naming)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator)
        self._entry = entry
        # Availability follows the coordinator automatically via CoordinatorEntity.

    @property
    def _update_time(self):
        data = self.coordinator.data or {}
        return data.get("update_time")


class OilPriceSensor(OilPriceSensorBase):
    """A numeric fuel-price sensor (92#/95#/98#/0#)."""

    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UNIT_PRICE
    _attr_icon = ICON_STATION

    def __init__(
        self, coordinator: DataUpdateCoordinator, entry: ConfigEntry, oil_type: str
    ) -> None:
        super().__init__(coordinator, entry)
        self._oil_type = oil_type
        self._attr_name = oil_type
        self._attr_unique_id = f"{entry.entry_id}-{oil_type}"

    @property
    def available(self) -> bool:
        data = self.coordinator.data or {}
        return super().available and self._oil_type in data.get("prices", {})

    @property
    def native_value(self):
        data = self.coordinator.data or {}
        return data.get("prices", {}).get(self._oil_type)

    @property
    def extra_state_attributes(self):
        return {"update_time": self._update_time, "region": self._entry.data.get("region")}


class OilPriceHintSensor(OilPriceSensorBase):
    """Next adjustment time + expected up/down.

    State is the full human sentence (never silently empty); the parsed pieces
    (next_adjust / direction / changes) are exposed as attributes so Lovelace
    cards and automations can pick individual fields.
    """

    _attr_icon = ICON_HINT

    def __init__(self, coordinator: DataUpdateCoordinator, entry: ConfigEntry) -> None:
        super().__init__(coordinator, entry)
        self._attr_name = "调价提示"
        self._attr_unique_id = f"{entry.entry_id}-hint"

    @property
    def _hint(self) -> dict:
        data = self.coordinator.data or {}
        return data.get("hint", {}) or {}

    @property
    def available(self) -> bool:
        data = self.coordinator.data or {}
        return super().available and bool(data.get("hint", {}).get("text"))

    @property
    def native_value(self):
        # Fall back to any text; empty string means unavailable (see available).
        return self._hint.get("text")

    @property
    def extra_state_attributes(self):
        return {
            "next_adjust": self._hint.get("next_adjust"),
            "direction": self._hint.get("direction"),
            "changes": self._hint.get("changes", {}),
            "update_time": self._update_time,
            "region": self._entry.data.get("region"),
        }
