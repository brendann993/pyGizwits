from dataclasses import dataclass
from time import time
from typing import Any, Dict

from pyGizwits.pyGizwits import logger

_CONNECTIVITY_TIMEOUT = 1000

@dataclass
class GizwitsDevice:
    """A device under a user's account."""

    device_id: str
    alias: str
    product_name: str
    mac: str
    ws_port: int
    host: str
    wss_port: int
    protocol_version: int
    mcu_soft_version: str
    mcu_hard_version: str
    wifi_soft_version: str
    is_online: bool
    _socketType: str = "ssl_socket"
    
    def get_websocketConnInfo(self) -> tuple[dict[str, str], str]:
        ws_info: Dict[str, str] = {'host': self.host, 'path': '/ws/app/v1'}
        if self._socketType == "ssl_socket":
            ws_info['pre'] = "wss://"
            ws_info['port'] = str(self.wss_port)
        else:
            ws_info['pre'] = "ws://"
            ws_info['port'] = str(self.ws_port)
        return (
            ws_info, 
            f"{ws_info['pre'] + ws_info['host'] + ':' + ws_info['port'] + ws_info['path']}"
        )


@dataclass
class GizwitsDeviceStatus:
    """A snapshot of the status of a device."""

    timestamp: int
    attributes: dict[str, Any]

    @property
    def online(self) -> bool:
        """Determine whether the device is online based on the age of the latest update."""
        return self.timestamp > (time() - _CONNECTIVITY_TIMEOUT)


@dataclass
class GizwitsDeviceReport:
    """A device report, which combines device metadata with a current status snapshot."""

    device: GizwitsDevice
    status: GizwitsDeviceStatus | None
