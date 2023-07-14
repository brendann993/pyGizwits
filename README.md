# pyGizwits

This package is a wrapper for Gizwits OpenAPI and websocket API.
It allows you get connect using the App ID for the device type you have registered, then register for websocket updates for the devices you choose.

## Example Usage ##

The below will login to the US api and get the devices currently bound to your devices. It will then fetch their current status as well as then subscribe to receive the websocket updates for the devices.
```
import asyncio
from aiohttp import ClientSession
import logging
import pyGizwits

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("pyGizwits")

async def main():
    # Configure your login credentials and app details
    username = "youremailaddress"
    password = "yourpassword"
    app_id = "appidfromappyourdeviceisregisteredin"
    session = ClientSession()
    region = pyGizwits.GizwitsClient.Region.US

    # Create a device manager and login
    device_manager = pyGizwits.DeviceManager(session, app_id, region)
    await device_manager.login(username, password)

    # Get the list of devices bound to your account
    await device_manager.get_devices()

    # Subscribe to device status updates
    device_manager.on("device_status_update", print)

    # Iterate through the devices and perform actions
    for device_id, device in device_manager.devices.items():
        print(f"Device ID: {device_id} is online {device.is_online}")
        print(f"Device is: {device.product_name}")
        
        # Subscribe to device updates via WebSocket
        await device.subscribe_to_device_updates()

        print("------")

    # Sleep for a certain duration to receive updates
    await asyncio.sleep(60)
    await session.close()

asyncio.run(main())

```
## DeviceManager Class ##

The `DeviceManager` class is responsible for managing the devices returned by the Gizwits platform.

### Initialization ###

```
device_manager = pyGizwits.DeviceManager(session, app_id, region)
```

- session (aiohttp.ClientSession): An instance of ClientSession from aiohttp library.
- app_id (str): The ID of the app where your device is registered.
- region (pyGizwits.GizwitsClient.Region): The region where the API is located (e.g., pyGizwits.GizwitsClient.Region.US).

### Login ###

```
await device_manager.login(username, password)
```
- username (str): The username for the login request.
- password (str): The password for the login request.

### Get Devices ###

```
await device_manager.get_devices()
```
Retrieves the list of devices bound to your Gizwits account.

### Subscribe to Events ###

```
device_manager.on(event_name, callback_function)
```
Subscribes to events on the `DeviceManager` and executes the specified callback function whenever it is fired.

### DeviceManager Events ###
event_name: `device_status_update`: Triggered when a device status update is received.
data: The latest status of the device.

## GizwitsDevice Class ##
The GizwitsDevice class represents a device connected to the Gizwits platform.

### Initialization ###
GizwitsDevices are automatically initialized for each device return from the Gizwits Server.

### Subscribe to Device Updates ###
```
await device.subscribe_to_device_updates()
```
Subscribes to updates for the device via a WebSocket connection.

### Get Device Status ###
```
await device.get_device_status()
```
Retrieves the latest status of the device.

### Set Device Attribute ###
```
await device.set_device_attribute(key, value)
```
Sets a specific attribute of the device to the specified value.
- key (str): The attribute to be set
- value (any): The value the attribute should be set to
