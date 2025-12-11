# Auntie Sounds

A library for interacting with BBC radio stations via an interface to BBC Sounds. It was written to be used for the BBC Sounds provider for [Music Assistant](https://music-assistant.io/) but exists as a standalone library.

## Features

✅ Signing into a BBC Sounds account<br />
✅ Listing current station programming<br />
✅ Obtaining a stream to listen to a station<br />
✅ Getting the current and previous segments (typically songs) on a station
✅ Displaying and listening to previous shows

### Not implemented

❌ Pausing or rewinding live radio<br />


## Notes
- It is written as an async library
- A BBC account is not required for most actions, but as BBC region-locks streams and is turning off non-UK access soon, is it the supported way to use it

## Example Usage

```python
import asyncio
from sounds import exceptions
from sounds.client import SoundsClient

async def main():
    try:
        client = SoundsClient()
        if await client.auth.authenticate(username, password):
            stations = await client.stations.get_stations()
            schedule = await client.schedules.get_schedule("bbc_6music", date="2025-10-26")
            bbc_6music = await client.stations.get_station("bbc_6music", include_stream=True)
            
    except exceptions.LoginFailedError:
        ...
    except exceptions.APIResponseError:
        ...
    except exceptions.NetworkError:
        ...

asyncio.run(main())
```