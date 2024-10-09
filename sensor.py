"""Platform for sensor integration."""
from __future__ import annotations

import logging

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)

from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.core import HomeAssistant, callback
from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import DOMAIN
from .coordinator import NetworkSwitchDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

TPlinkStatus = {'0': "Link Down", '1': "LS 1", '2': "10M Half", '3': "10M Full", '4': "LS 4", '5': "100M Full", '6': "1000M Full"}
TPstate = {'0': 'Disabled', '1': 'Enabled'}
PortStatLookup = {
    'TxGoodPkt': {
        'name': 'Transimitted Packets',
        'entity_prefix': 'txgoodpkt'
    },
    'TxBadPkt': {
        'name': 'Failed Transimitted Packets',
        'entity_prefix': 'txbadpkt'
    },
    'RxGoodPkt': {
        'name': 'Recieved Packets',
        'entity_prefix': 'rxgoodpkt'
    },
    'RxBadPkt': {
        'name': 'Failed Recieved Packets',
        'entity_prefix': 'rxbadpkt'
    }
}
SwitchStatLookup = {
    'max_ports': {
        'name': 'Max Ports',
        'entity_prefix': 'max_ports'
    },
    'ports_in_use': {
        'name': 'Active Ports',
        'entity_prefix': 'active_ports'
    }
}

async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    """Set up the sensor platform."""

    config = hass.data[DOMAIN][config_entry.entry_id]

    host = config['host']
    coordinator =  config['coordinator']
    _LOGGER.info("--------------THE CONFIG---------------------------")
    _LOGGER.info(config)

    sensors = []
    switch_info = coordinator.data.get("switch_data")

    # Every Port on the Switchs entities/devices
    active_port_counter = 0
    for port, stats in coordinator.data.get('port_data').items():
        _LOGGER.info(stats)
        port_enabled = stats.get("state")
        port_speed = stats.get("link_status")
        if port_enabled and port_speed and port_enabled == 'Enabled' and port_speed != 'Link Down':
            active_port_counter += 1
            _LOGGER.info('in port enabled check')
            for key, data in PortStatLookup.items():
                sensors.append(NetworkSwitchPortSensor(coordinator, port, host, port_speed, switch_info, stats.get(key), data, key))

    # Main Switch Device
    sensors.append(NetworkSwitchSensor(host, switch_info, coordinator.data.get("total_ports"), SwitchStatLookup.get('max_ports')))
    sensors.append(NetworkSwitchSensor(host, switch_info, active_port_counter, SwitchStatLookup.get('ports_in_use')))

    async_add_entities(sensors, True)

class NetworkSwitchSensor(SensorEntity):
    def __init__(self, host, switch_info, data, name_info):
        _LOGGER.info("Setting up switch")
        _LOGGER.info(switch_info)

        self.host = host
        self.switch_info = switch_info
        self.name_info = name_info

        self._name = name_info.get('name')
        self._state = data
        self._attr_extra_state_attributes = {}
        self.attrs = {}
        self._available = True
        self.entity_id = f'sensor.tplink_switch_{self.host}_{name_info.get('entity_prefix')}'

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.host, self.switch_info.get('mac_address'))},
            name=f'{self.host} Switch',
            configuration_url = f'http://{self.host}',
            model=f'{self.switch_info.get('hardware_version')}',
            sw_version=f'{self.switch_info.get('firmware_version')}'
        )

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.attrs

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f'sensor.tplink_switch_{self.host}_{self.name_info.get('entity_prefix')}'


class NetworkSwitchPortSensor(CoordinatorEntity, SensorEntity):
    def __init__(self, coordinator, port, host, speed, switch_info, packets, name_info, key):
        super().__init__(coordinator)
        _LOGGER.info("Setting up port on switch")
        
        self.host = host
        self.switch_info = switch_info
        self.port = port
        self.name_info = name_info
        self.key = key

        self._name = name_info.get('name')
        self._state = packets
        self._attr_extra_state_attributes = {}
        self.attrs = {}
        self._available = True
        self.entity_id = f'sensor.tplink_switch_{self.host}_p{self.port}_{name_info.get('entity_prefix')}'

    @property
    def device_info(self) -> DeviceInfo:
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self.host, self.port, self.switch_info.get('mac_address'))},
            name=f'Port {self.port}',
            configuration_url = f'http://{self.host}',
            model=f'{self.switch_info.get('hardware_version')}',
            sw_version=f'{self.switch_info.get('firmware_version')}'
        )

    @property
    def state_class(self) -> SensorStateClass:
        """Handle string instances."""
        return SensorStateClass.TOTAL_INCREASING

    @property
    def name(self) -> str:
        """Return the name of the entity."""
        return self._name

    @property
    def state(self) -> str | None:
        return self._state

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self.attrs

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def unique_id(self):
        """Return a unique ID."""
        return f'sensor.tplink_switch_{self.host}_p{self.port}_{self.name_info.get('entity_prefix')}'

    @callback
    def _handle_coordinator_update(self):
        port_data = self.coordinator.data.get('port_data').get(self.port, {})

        self._state = port_data.get(self.key)
        self.async_write_ha_state()
