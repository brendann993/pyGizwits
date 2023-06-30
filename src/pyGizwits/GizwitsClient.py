import asyncio
from dataclasses import dataclass
from enum import Enum
from time import time
from typing import Any, Dict
from urllib.parse import urljoin

from aiohttp import ClientError, ClientSession
from pyee.base import EventEmitter

from .GizwitsDevice import GizwitsDevice, GizwitsDeviceReport, GizwitsDeviceStatus
from .pyGizwits import (
    ErrorCodes,
    GizwitsAuthException,
    GizwitsDeviceNotBound,
    GizwitsException,
    GizwitsIncorrectPasswordException,
    GizwitsOfflineException,
    GizwitsTokenInvalidException,
    GizwitsUserDoesNotExistException,
    logger,
    raise_for_status,
)
from .WebSocketConnection import WebSocketConnection


@dataclass
class GizwitsUserToken:
    """User authentication token, obtained following a successful login."""

    user_id: str
    user_token: str
    expiry: int


class GizwitsClient(EventEmitter):
    """Gizwits client representing a connection to the Gizwits server."""

    class Region(Enum):
        """Gizwits region."""

        US = "us"
        EU = "eu"
        DEFAULT = "default"

    def __init__(
        self, session: ClientSession,
        app_id: str,
        region: Region = Region.DEFAULT
    ):
        super().__init__()
        self.base_url = self.get_base_url(region)
        self.region = region
        self.app_id = app_id
        self.token: str
        self.uid: str
        self.expires_at: int
        self.bindings: Dict[str, GizwitsDevice] = {}
        self.sockets: Dict[str, WebSocketConnection] = {}
        self._session = session

    @staticmethod
    def get_base_url(region: Region) -> str:
        """
        Retrieves the base URL for the given region.
        Args:
            region (Region): The region for which to retrieve the base URL.
        Returns:
            str: The base URL corresponding to the given region.
        """
        if region == GizwitsClient.Region.US:
            return "https://usapi.gizwits.com"
        if region == GizwitsClient.Region.EU:
            return "https://euapi.gizwits.com"
        return "https://api.gizwits.com"

    def token_expired(self):
        """
        Emits a 'token_expired' event.

        Returns:
            None
        """
        self.emit('token_expired')

    async def get_token(self, username: str, password: str) -> GizwitsUserToken:
        """
        Retrieves the user token using the provided username and password.

        Args:
            username (str): The username for the login request.
            password (str): The password for the login request.
        Returns:
            GizwitsUserToken: An instance of GizwitsUserToken.
        Raises:
            GizwitsException: If an error occurs during the token retrieval process.
        """
        # Set the URL and headers
        url = urljoin(self.base_url, "/app/login")
        headers = {"X-Gizwits-Application-Id": self.app_id}

        # Set the payload
        payload = {"username": username, "password": password, "lang": "en"}

        # Send a POST request and get the response
        async with self._session.post(url, headers=headers, json=payload) as response:
            await raise_for_status(response)

            # Extract the token and uid from the response
            data = await response.json()

        # Return the uid and token
        return GizwitsUserToken(data["uid"], data["token"], data["expire_at"])

    async def login(self, username: str, password: str) -> None:
        """
        Login to the Gizwits OpenAPI.

        Sends a POST request to the login endpoint with the given username and password.
        The X-Gizwits-Application-Id header is set to the app_id stored in the class.
        The payload contains the given username, password, and language code.
        If the request is successful, the response json is extracted to set the token and
        uid class variables. Finally, the uid and token are returned as a tuple.

        Args:
            username (str): The username for the login request.
            password (str): The password for the login request.
        Returns:
            None
        Raises:
            GizwitsException: If an error occurs during the login process.
        """
        login_data = await self.get_token(username, password)
        self.token = login_data.user_token
        self.uid = login_data.user_id
        self.expires_at = login_data.expiry
        # Schedule the token refresh
        expiry_time = self.expires_at - time()  # Calculate time remaining until expiry
        asyncio.create_task(self.refresh_token(expiry_time, username, password))

    async def refresh_token(self, expiry_time, username, password):
        """
        Handle token expiry.

        Asynchronously refreshes the token by sleeping until the token expiry time,
        then calling the token_expired() method and refreshing the token by calling
        the login method with the provided username and password.

        Args:
            expiry_time (int): An integer representing the duration 
            in seconds until the token expires.
            username (str): A string representing the username.
            password (str): A string representing the password.
        Returns:
            None
        """
        # Sleep until the token expiry time
        await asyncio.sleep(expiry_time)
        self.token_expired()

        # Refresh the token
        await self.login(username, password)

    async def _get(self, endpoint: str) -> Dict[str, Any]:
        """
        An async function that retrieves data from a specific API endpoint.

        Args:
            endpoint (str): The API endpoint to retrieve data from.
        Returns:
            Dict[str, Any]: A dictionary containing the response data.
        """
        url = urljoin(self.base_url, endpoint)
        headers = {
            "X-Gizwits-Application-Id": self.app_id,
            "X-Gizwits-User-Token": self.token
        }

        async with self._session.get(url, headers=headers) as response:
            await raise_for_status(response)
            response_json: Dict[str, Any] = await response.json(content_type=None)
            return response_json

    async def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Asynchronously sends a POST request to the specified endpoint with data.

        Args:
            endpoint (str): The endpoint to send the request to.
            data (Dict[str, Any]): The data to send with the request.

        Returns:
            Dict[str, Any]: A dictionary representing the JSON data 
            returned by the response.
        """
        url = urljoin(self.base_url, endpoint)
        headers = {
            "X-Gizwits-Application-Id": self.app_id,
            "X-Gizwits-User-Token": self.token
        }
        headers = {k: v if v is not None else "" for k, v in headers.items()}
        async with self._session.post(url, headers=headers, json=data) as response:
            await raise_for_status(response)
            return await response.json()

    async def _get_bindings(self) -> Dict[str, GizwitsDevice]:
        """
        Asynchronously retrieves device bindings from Gizwits.

        Using the '/app/bindings' endpoint

        Returns:
            Dict[str, GizwitsDevice]: A dictionary containing the bound devices, 
            with each device's 'did' as the key and a GizwitsDevice instance as the value.

        Raises:
            GizwitsException: if an error occurs while retrieving the device bindings.
        """
        bound_devices: Dict[str, GizwitsDevice] = {}
        limit = 20
        skip = 0
        more = True
        url = "/app/bindings"
        while more:
            query = f"?show_disabled=0&limit={limit}&skip={skip}"
            endpoint = url + query
            try:
                response_data = await self._get(endpoint)
                if 'devices' in response_data and response_data['devices']:
                    for device in response_data['devices']:
                        did = device["did"]
                        bound_devices[did] = GizwitsDevice(
                            device["did"],
                            device["dev_alias"],
                            device["product_name"],
                            device['mac'],
                            device['ws_port'],
                            device['host'],
                            device['wss_port'],
                            device['protoc'],
                            device["mcu_soft_version"],
                            device["mcu_hard_version"],
                            device["wifi_soft_version"],
                            device["is_online"],
                        )
                    if len(response_data['devices']) == limit:
                        skip += limit
                    else:
                        more = False
                else:
                    more = False
            except ClientError as e:
                logger.error(f"Request error: {e}")
                raise GizwitsException(
                    "Error occurred while retrieving device bindings."
                ) from e
            except Exception as e:
                logger.error(f"Error: {e}")
                raise GizwitsException(
                    "Unknown error occurred while retrieving device bindings."
                ) from e
        return bound_devices

    async def refresh_bindings(self) -> None:
        """
        Asynchronously refreshes the bindings of the current session 

        Emits a 'bindings_refreshed' event with the updated bindings.

        Returns:
            None
        """
        self.bindings = await self._get_bindings()
        self.emit('bindings_refreshed', self.bindings)

    async def fetch_device(self, device_id: str) -> GizwitsDeviceReport:
        """
        Asynchronously fetches the latest data for a specific device.

        Args:
            device_id (str): The ID of the device to fetch.
        Returns:
            GizwitsDeviceReport: The latest data for the device.
        Raises:
            GizwitsDeviceNotBound: if the device is not bound.
        """
        if device_id not in self.bindings.items():
            raise GizwitsDeviceNotBound()
        device_info = self.bindings[device_id]
        logger.debug(f"Fetching device {device_id}")
        latest_data = await self._get(f"/app/devdata/{device_id}/latest")
        # Get the age of the data according to the API
        api_update_timestamp = latest_data["updated_at"]

        # Zero indicates the device is offline
        # This has been observed after a device was offline for a few months
        if api_update_timestamp == 0:
            # In testing, the 'attrs' dictionary has been observed to be empty
            return GizwitsDeviceReport(device_info, None)

        device_status = GizwitsDeviceStatus(
            latest_data["updated_at"],
            attributes=latest_data
        )
        return GizwitsDeviceReport(device_info, device_status)

    async def fetch_devices(self) -> dict[str, GizwitsDeviceReport]:
        """
        Asynchronously fetches the latest data for all currently bound devices.

        Only devices that are currently bound will be included in the results.

        Returns:
            A dictionary where each key is a device ID and each value is a
            `GizwitsDeviceReport` object containing the latest data for that
            device. If no data is available for a device (i.e. the device is
            offline), its `GizwitsDeviceReport` object will have a `None`
            `GizwitsDeviceStatus` object. If no devices are currently bound, an
            empty dictionary is returned.
        """
        results: dict[str, GizwitsDeviceReport] = {}

        if not self.bindings:
            return results

        for did, device_info in self.bindings.items():
            logger.debug(f"Fetching device {did}")
            latest_data = await self._get(f"/app/devdata/{did}/latest")
            # Get the age of the data according to the API
            api_update_timestamp = latest_data["updated_at"]

            # Zero indicates the device is offline
            # This has been observed after a device was offline for a few months
            if api_update_timestamp == 0:
                # In testing, the 'attrs' dictionary has been observed to be empty
                results[did] = GizwitsDeviceReport(device_info, None)
                continue

            device_status = GizwitsDeviceStatus(
                latest_data["updated_at"],
                attributes=latest_data
            )
            results[did] = GizwitsDeviceReport(device_info, device_status)
        return results

    async def Subscribe_to_device_updates(self, device: GizwitsDevice):
        """
        Subscribes to updates from a given GizwitsDevice via a WebSocket connection.

        Args:
            device (GizwitsDevice): The device for which updates are to be subscribed.
        Returns:
            None
        """
        sockets = self.sockets
        websocket_info, websocket_url = device.get_websocketConnInfo()
        if websocket_url in sockets:
            logger.debug(f"Using existing websocket for {websocket_url}")
            await sockets[websocket_url].add_device_sub(device.device_id)
        else:
            logger.debug(f"Creating websocket for {websocket_url}")
            socket = WebSocketConnection(self._session, self, websocket_info)
            await socket.connect()
            await socket.login()
            await socket.add_device_sub(device.device_id)
            sockets[websocket_url] = socket

    async def got_device_status_update(self, device_update: dict):
        """
        Asynchronously takes in a device update and produces a GizwitsDeviceReport.

        Args:
            device_update (dict): A dictionary containing information about the device.
        Returns:
            None
        """
        did = device_update["did"]
        device_info = self.bindings.get(did)
        device_status = GizwitsDeviceStatus(
            int(time()),
            attributes=device_update["attrs"]
        )
        result = GizwitsDeviceReport(device_info, device_status)
        self.emit('device_status_update', result)
