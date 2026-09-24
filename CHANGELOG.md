# CHANGELOG

## [Unreleased]

* New feature: added international radio stations
* Fix: ensure the correct Radio 4 ID is used across all endpoints
 
### API Changes

* `Client.get_menu(MenuRecommendationOptions.ONLY)` is no longer supported, use `Client.get_recommendation_folders()`
  instead
* The `logger` parameter has been removed from `SoundsClient.__init__()`
* `StreamingService` has been split into `ContentService` and `PlaybackService` as below:
    * PlaybackService
        * get_live_stream
        * get_best_stream
        * get_episode_stream
        * get_heartbeat_details
        * update_play_status
        * get_stream_jwt_token → renamed to get_stream_token
    * ContentService
        * get_by_pid
        * get_pid_container
        * get_container
        * get_category
        * get_collection
        * get_playlist_contents
        * search
        * podcast/radio methods
        * get_show_segments
* UserService.is_in_uk () -> UserService.is_geo_located_in_uk ()
* UserService.is_uk_listener () -> UserService.is_uk_account_and_location ()
* StationService.get_stations_details -> StationService.get_networks
* StationService.get_station_schedule_menu -> StationService.get_schedule_menu
* PersonalService.continue_listening -> PersonalService.get_continue_listening

## [2.0.9] - 2026-09-03

* Fix: Playlists weren't correctly converted

## [2.0.8] - 2026-09-02

* Fix: StreamingService.get_by_pid () was not using RequestManager.run () to use the authenticated endpoint

## [2.0.7] - 2026-08-29

* Fix: remove internal station list cache which was causing upstream bugs

## [2.0.6] - 2026-08-29

* Fix: local stations not being returned correctly

## [2.0.5] - 2026-08-29

* Fix: add the schedule menu back for international listeners

## [v2.0.4]

* Relax remaining dependencies to >= to prevent upstream being blocked

## [v2.0.3]

* Fix: recommendation folder options were not being passed to `Client.get_menu()`
* Relax aiohttp dependency to >= 3.14.1​ to prevent upstream being blocked

## [2.0.2]

* Fix: fix discrepancy between session-provided cookie jars, new session jars and saving to disk
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
