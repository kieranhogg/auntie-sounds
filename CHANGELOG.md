# CHANGELOG

## [Unreleased]

## [3.0.1] - 2026-11-12
* Change: tweak the main menu IDs to `live` and `schedules` from `radio` and `schedule`

## [3.0.0] - 2026-11-12
* New feature: added international radio stations
* New feature: podcast and radio series seasons. `Podcast.seasons` / `RadioSeries.seasons` hold `Season`
  containers; with `include_episodes=True`, episodes are grouped into their season and any that don't belong
  to one stay in `sub_items`
* New feature: `PlayableItem.series_pid`, the episode's series where it differs from its brand
* New feature: `Segment.apple_music_url` and `Segment.record_id`
* New feature: `auntie_sounds.parse()` can be used to read an API response without a client instance
* New feature: `RequestManager.get_json_response()` can page through results with `fetch_all_items` or `max_items`
* New feature: `DateOutOfRangeError` (a subclass of `APIResponseError`) is raised when a schedule is requested
  outside the range the API serves
* New feature: `Segment.offset` is now a `SegmentOffset` (`start`, `end`, `label`, `now_playing`) rather than a dict
* New feature: `ScheduleService.refresh_history()` and `history()` keep a per-station `SegmentHistory` of recent
  tracks. `SegmentHistory.lookup()` says whether a track, speech or nothing known was on air at a time
* New feature: single broadcast responses (`pid` rather than `id`, with a nested `programme`) get converted into a `ScheduleItem`
* Fix: podcasts with more than 30 episodes are no longer truncated
* Fix: ensure the correct Radio 4 ID is used across all endpoints

### API Changes

**Note**: see updated README for typical usage.

#### Package

* The import package is renamed from `sounds` to `auntie_sounds` to match the distribution of `auntie-sounds`
* Every exception class is now exported from `auntie_sounds`
* `pytz` has been dropped as a dependency

#### SoundsClient

* Services are created by `start()`, or by `async with SoundsClient(...)`, or by `await SoundsClient.create(...)`.
  Using a service before then raises `NotStartedError`
* The `logger`, `timezone` and `mock_session` parameters have been removed from `SoundsClient.__init__()`
* `setLogger()` has been removed. Pass `log_level` to `SoundsClient()` instead
* `has_session_cookie()` is now the `is_signed_in` property
* `get_menu(recommendations=...)` is now `get_menu(include_recommendations=...)`
* `get_menu(MenuRecommendationOptions.ONLY)` is replaced by `get_recommendation_folders()` instead
* The default cookie file is now per account, and a cookie file saved by another account is not loaded

#### StreamingService split

`StreamingService` has been split into `ContentService` (`client.content`) and `PlaybackService`
(`client.playback`):

* ContentService
    * `get_by_pid`: `stream_format` is now `stream_preferences`, a `StreamPreference`
    * `get_pid_container`, `get_container`, `get_category`, `get_collection`, `get_playlist_contents`, `search`
    * `get_podcasts`, `get_podcast`, `get_podcast_episodes`, `get_podcast_episode`, `get_radio_series`,
      `get_radio_show`
    * `get_show_segments`, which also takes `max_concurrent_images`
    * `get_heartbeat_details`
* PlaybackService
    * `get_live_stream`: `stream_format` is now `preferences`, a `StreamPreference`, and it takes `international`
    * `get_episode_stream`: `episode_id` is now `vpid`, and `stream_format` is now `preferences`
    * `get_live_streams` and `get_episode_streams` are new. They return every CDN's URL, best first
    * `get_stream_jwt_token` → `get_stream_token`
    * `update_play_status` → `update_episode_play_status` and `update_live_play_status`
    * `get_best_stream` has been removed

#### ContentService

* `get_podcast_episode()`, `get_radio_series()` and `get_radio_show()` raise `NotExpectedTypeError` when the pid or
  urn is a different type of item

#### StationService

* `get_stations_details()` → `get_networks()`
* `get_stations(include_local=...)` is now `get_stations(include_local_stations=...)`, and it also takes
  `include_national_stations` and `include_international_stations`
* `get_station(stream_format=...)` is now `get_station(stream_preferences=...)`
* `get_local_stations()` has been removed, use `get_stations(include_national_stations=False,
  include_local_stations=True)`
* `get_station_schedule()`, `get_station_menu()` and `get_station_schedule_menu()` have been removed. Use
  `ScheduleService.get_schedule()` and `auntie_sounds.schedule.station_folders()`, `schedule_dates()` and
  `catch_up_dates()`

#### ScheduleService

* `on_air()` takes the first programme of the station's on-air poll, and accepts `now`
* `get_station_schedules()` and `get_stations_schedules()` take no dates. They return today and the next 7 days
* `get_station_catch_up()` and `get_stations_catch_up()` are new. They return today and the previous 30 days

#### UserService and PersonalService

* `UserService.is_in_uk()` → `UserService.is_geolocated_in_uk()`
* `UserService.is_uk_listener()` → `UserService.is_uk_account_and_location()`
* `PersonalService.continue_listening()` → `PersonalService.get_continue_listening()`
* `PersonalService.get_uk_menu()` → `PersonalService.construct_uk_menu()`

#### Models

* An episode's `container` is now always its brand, whichever endpoint it came from. Its series is in `series_pid`
* `RadioSeries` and`Podcast` now have `seasons`
* `PlayableItem.fallback_streams` holds the other CDNs' stream URLs, after `stream`
* `PlayableItem.activities` is a list of `Activity` (`type`, `action`, `label`, `urn`) on the personalised endpoints
* `PlayableItem.has_already_aired` is now a property
* `Segment.offset` is a `SegmentOffset`, so `offset.get("start")` is now `offset.start`
* `image_from_recipe()` no longer takes `img_type`

#### Errors

* `APIResponseError` raised from an API error body now carries `status_code`

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
