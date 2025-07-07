# Auntie Sounds

A library for interacting with BBC radio stations via an interface to BBC Sounds. It was written to be used for the BBC Sounds provider for [Music Assistant](https://music-assistant.io/) but exists as a standalone library.

## Features

✅ Signing into a BBC Sounds account<br />
✅ Listing current station programming<br />
✅ Obtaining a stream to listen to a station<br />
✅ Getting the current and previous segments (typically songs) on a station

### Not implemented

❌ Pausing or rewinding live radio<br />
❌ Displaying and listening to previous shows

## Notes
- While not a requirement, it is written as an async library
- A BBC account is required to authenticate with to retrieve a working stream

## Example Usage

```python
import asyncio
from sounds.client import SoundsClient

async def main():
    async with SoundsClient() as client:
        if await client.auth.authenticate("username", "password"):
            stations = await client.stations.get_stations()
            stream = await client.streaming.get_stream_info("bbc_6music")
            segments = await client.segments.now_playing("bbc_6music")

            # Services share state automatically
            assert client.auth._session is client.streaming._session


asyncio.run(main())
```