# CHANGELOG

## [Unreleased]

## [2.0.5] - 2026-08-29
* Fix: add the schedule menu back for international listeners

## [v2.0.4]
* Relax remaining dependencies to >= to prevent upstream being blocked

## [v2.0.3]
* Fix: recommendation folder options were not being passed to `Client.get_menu()`
* Relax aiohttp dependency to >= 3.14.1​ to prevent upstream being blocked

## [2.0.2]
* Fix: fix discrepency between session-provided cookie jars, new session jars and saving to disk
* Fix: handle edge-case when a previous session is present when a new anonymous client is created 

## [2.0.1]
* Fix: errors with email and password stages were not being detected

## [2.0]

### API Changes
* `SoundsClient.authenticate()` has been removed, username and password are passed directly to `SoundsClient()`
* The `Broadcast` model has been deprecated

## [1.1.8]

* Fix: Fix NameError when running in Music Assistant

## [1.1.7]

* Fix: Always get local stations when finding a station with `Stations.get_station()`
* Fix: `Auth.user_info()` wouldn't be set if renewing a session

## [1.1.6]

* Fix: `Streaming.get_by_pid()` can fail with stale sessions

## [1.1.5]

* Fix: non-UK logins not logging in correctly

## [1.1.4]

* Fix: Radio 4 uses two different IDs, use the correct one

## [1.1.3]

* Fix: The API response in `StreamingService.get_heartbeat_details()` could raise an uncaught TypeError

## [1.1.2]

* Improved type checking

## [1.1.1]

* Improved type checking

## [1.1.0]

* Add the `stream_format` parameter to allow selection of preferred stream type

## [1.0] 

Initial release
