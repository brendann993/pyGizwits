# pyGizwits

This package is a wrapper for Gizwits OpenAPI and websocket API.
It allows you get connect using the App ID for the device type you have registered, then register for websocket updates for the devices you choose.

**Example Usage**

The below will login to the US api and get the devices currently bound to your devices. It will then fetch their current status as well as then subscribe to receive the websocket updates for the devices.
```
from pyGizwits import pyGizwits
from aiohttp import ClientSession
import asyncio

async def main()
    username = 'youremailaddress'
    password = 'yourpassword'
    app_id = 'appidfromappyourdeviceisregisteredin'
    session = ClientSession()
    region = pyGizwits.GizwitsClient.Region.US
    client = pyGizwits.GizwitsClient(session,app_id,region)
    @client.on('device_status_update')
    def handle_device_status_update(update):
        print(f"Got Update")
        print(update)
    await client.login(username,password)
    await client.refresh_bindings()
    devices: dict[str, pyGizwits.GizwitsDeviceReport] = await client.fetch_devices()
    for device in devices:
        await client.Subscribe_to_device_updates(devices[device].device)
    await asyncio.sleep(60)
    await session.close()

asyncio.run(main())
```
