from dataclasses import dataclass
from time import time
from typing import TYPE_CHECKING, Any, Dict

from pyGizwits.logger import logger

if TYPE_CHECKING:
    from pyGizwits.GizwitsClient import GizwitsClient
    from pyGizwits.DeviceManager import DeviceManager

from pyGizwits.WebSocketConnection import WebSocketConnection

_CONNECTIVITY_TIMEOUT = 1000


class GizwitsDevice:
    """Gizwits device."""

    def __init__(
        self,
        device_id,
        alias,
        product_name,
        mac,
        ws_port,
        host,
        wss_port,
        protocol_version,
        mcu_soft_version,
        mcu_hard_version,
        wifi_soft_version,
        is_online,
        client_connection,
        Device_manager,
    ):
        self.device_id = device_id
        self.alias = alias
        self.product_name = product_name
        self.mac = mac
        self.ws_port = ws_port
        self.host = host
        self.wss_port = wss_port
        self.protocol_version = protocol_version
        self.mcu_soft_version = mcu_soft_version
        self.mcu_hard_version = mcu_hard_version
        self.wifi_soft_version = wifi_soft_version
        self.is_online = is_online
        self.attributes: Dict[str, Any] = {}
        self.client_connection: 'GizwitsClient' = client_connection
        self.device_manager: 'DeviceManager' = Device_manager
        self._socketType = "ssl_socket"
        self.websocket_connection: 'WebSocketConnection'

    def get_websocketConnInfo(self) -> tuple[dict[str, str], str]:
        """
        Get the WebSocket connection information.
        Returns:
            A tuple containing a dictionary with keys 'host', 'path', 'pre', and 'port',
            and a string representing the WebSocket connection URL.
        """
        ws_info: Dict[str, str] = {'host': self.host, 'path': '/ws/app/v1'}
        if self._socketType == "ssl_socket":
            ws_info['pre'] = "wss://"
            ws_info['port'] = str(self.wss_port)
        else:
            ws_info['pre'] = "ws://"
            ws_info['port'] = str(self.ws_port)
        return (
            ws_info,
            f"{ws_info['pre']}{ws_info['host']}:{ws_info['port']}{ws_info['path']}",
        )

    async def subscribe_to_device_updates(self):
        """
        Subscribes to updates from a given GizwitsDevice via a WebSocket connection.

        Args:
            device (GizwitsDevice): The device for which updates are to be subscribed.
        Returns:
            None
        """
        websocket_info, websocket_url = self.get_websocketConnInfo()
        sockets: Dict[str, WebSocketConnection] = self.device_manager.sockets
        if websocket_url in sockets:
            logger.debug("Using existing websocket for %s", websocket_url)
            await sockets[websocket_url].add_device_sub(self.device_id)
        else:
            logger.debug("Creating websocket for %s", websocket_url)
            socket = WebSocketConnection(
                self.device_manager.client.session, self.device_manager, websocket_info
            )
            await socket.connect()
            await socket.login()
            await socket.add_device_sub(self.device_id)
            sockets[websocket_url] = socket

    async def get_device_status(self):
        """
        Asynchronously retrieves device status from Gizwits.
        Returns:
            A GizwitsDeviceReport object.
        """
        return await self.client_connection.fetch_device(self.device_id)

    async def set_device_attribute(self, key, value):
        """
        Set a device attribute.

        Args:
            key: The key of the attribute to set.
            value: The value to set for the attribute.
        Returns:
            The result of setting the attribute.
        """
        return await self.client_connection.set_device_attribute(
            self.device_id, key, value
        )


@dataclass
class GizwitsDeviceStatus:
    """A snapshot of the status of a device."""

    timestamp: int
    attributes: dict[str, Any]

    @property
    def online(self) -> bool:
        """Determine if the device is online based on the age of the latest update."""
        return self.timestamp > (time() - _CONNECTIVITY_TIMEOUT)
