sounds_types = {
    "DisplayItem": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["display_item"]},
            "id": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,}|[a-zA-Z0-9_]{1,})$",
                "example": "b08vxtj4",
            },
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:[a-zA-Z0-9:_]{1,}$",
                "example": "urn:bbc:radio:episode|network|segment:b08vxv2w",
            },
            "network": {"$ref": "#/components/schemas/DisplayItemNetwork"},
            "titles": {"$ref": "#/components/schemas/DisplayItemTitles"},
            "synopses": {
                "oneOf": [
                    {"$ref": "#/components/schemas/DisplayItemSynopses"},
                    {"$ref": "#/components/schemas/NullValue"},
                ]
            },
            "image_url": {
                "type": "string",
                "example": "https://ichef.bbci.co.uk/images/ic/{recipe}/p054zzwj.jpg",
            },
        },
        "required": [
            "type",
            "id",
            "urn",
            "network",
            "titles",
            "synopses",
            "image_url",
        ],
    },
    "DisplayItemNetwork": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "example": "bbc_radio_four"},
            "key": {"type": "string", "nullable": True, "example": "radio4"},
            "short_title": {"type": "string", "example": "Radio 4"},
            "logo_url": {
                "type": "string",
                "example": "https://sounds.files.bbci.co.uk/v2/networks/bbc_radio_four/{type}_{size}.{format}",
            },
        },
        "required": ["id", "key", "short_title", "logo_url"],
    },
    "DisplayItemsResponse": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/DisplayItem"},
            }
        },
        "required": ["data"],
    },
    "DisplayItemSynopses": {
        "type": "object",
        "properties": {
            "short": {
                "type": "string",
                "example": "A discussion on the different ways of understanding the world around us.",
            },
            "medium": {
                "type": "string",
                "nullable": True,
                "example": "Discussion programme in which guests from different faith and non-faith",
            },
            "long": {
                "type": "string",
                "nullable": True,
                "example": "debate the challenges of today's world.",
            },
        },
        "required": ["short", "medium", "long"],
    },
    "DisplayItemTitles": {
        "type": "object",
        "properties": {
            "primary": {"type": "string", "example": "Beyond Belief"},
            "secondary": {
                "type": "string",
                "nullable": True,
                "example": "Public Grief",
            },
            "tertiary": {
                "type": "string",
                "nullable": True,
                "example": "Lorem ipsum",
            },
        },
        "required": ["primary", "secondary", "tertiary"],
    },
    "PlayableItem": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["playable_item"]},
            "id": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,}|[a-zA-Z0-9_]{1,})$",
                "example": "b08vxtj4",
            },
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:[a-zA-Z0-9:_]{1,}$",
                "example": "urn:bbc:radio:episode|network|segment:b08vxv2w",
            },
            "network": {"$ref": "#/components/schemas/PlayableItemNetwork"},
            "titles": {"$ref": "#/components/schemas/PlayableItemTitles"},
            "synopses": {
                "oneOf": [
                    {"$ref": "#/components/schemas/PlayableItemSynopses"},
                    {"$ref": "#/components/schemas/NullValue"},
                ]
            },
            "image_url": {
                "type": "string",
                "example": "https://ichef.bbci.co.uk/images/ic/{recipe}/p054zzwj.jpg",
            },
            "duration": {"$ref": "#/components/schemas/PlayableItemDuration"},
            "progress": {"$ref": "#/components/schemas/PlayableItemProgress"},
            "container": {"$ref": "#/components/schemas/PlayableItemContainer"},
            "download": {"$ref": "#/components/schemas/PlayableItemDownload"},
            "availability": {
                "oneOf": [
                    {"$ref": "#/components/schemas/PlayableItemAvailability"},
                    {"$ref": "#/components/schemas/NullValue"},
                ]
            },
            "release": {"$ref": "#/components/schemas/PlayableItemReleaseDate"},
            "guidance": {"$ref": "#/components/schemas/PlayableItemGuidance"},
            "activities": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/PlayableItemActivity"},
            },
            "uris": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/PlayableItemUri"},
            },
            "play_context": {"type": "string"},
            "recommendation": {
                "oneOf": [
                    {"$ref": "#/components/schemas/Recommendation"},
                    {"$ref": "#/components/schemas/NullValue"},
                ]
            },
        },
        "required": [
            "type",
            "id",
            "urn",
            "network",
            "titles",
            "synopses",
            "image_url",
            "duration",
            "progress",
            "container",
            "download",
            "availability",
            "guidance",
            "activities",
            "uris",
            "recommendation",
        ],
    },
    "PlayableItemsResponse": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/PlayableItem"},
            }
        },
        "required": ["data"],
    },
    "PlayableItemsPaginatedResponse": {
        "type": "object",
        "properties": {
            "total": {"type": "integer", "minimum": 0, "example": 287365},
            "limit": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "example": 30,
            },
            "offset": {"type": "integer", "minimum": 0, "example": 0},
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/PlayableItem"},
            },
        },
        "required": ["total", "limit", "offset", "data"],
    },
    "PlayableItemActivity": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "example": "favourite_activity"},
            "action": {"type": "string", "example": "favourited"},
        },
        "required": ["type", "action"],
    },
    "PlayableItemAvailability": {
        "type": "object",
        "properties": {
            "from": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT[0-2]\\d:[0-5]\\d:[0-5]\\dZ|)$",
                "example": "2017-06-26T16:00:28Z",
            },
            "to": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT[0-2]\\d:[0-5]\\d:[0-5]\\dZ|)$",
                "example": "2021-06-26T16:00:28Z",
            },
            "label": {"type": "string", "example": "Available for over a year"},
        },
        "required": ["from", "to", "label"],
    },
    "PlayableItemDuration": {
        "type": "object",
        "properties": {
            "value": {"type": "integer", "minimum": 0, "example": 1800},
            "label": {"type": "string", "example": "30 mins"},
        },
        "required": ["value", "label"],
    },
    "PlayableItemNetwork": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "example": "bbc_radio_four"},
            "key": {"type": "string", "nullable": True, "example": "radio4"},
            "short_title": {"type": "string", "example": "Radio 4"},
            "logo_url": {
                "type": "string",
                "example": "https://sounds.files.bbci.co.uk/v2/networks/bbc_radio_four/{type}_{size}.{format}",
            },
        },
        "required": ["id", "key", "short_title", "logo_url"],
    },
    "PlayableItemProgress": {
        "type": "object",
        "properties": {
            "value": {"type": "integer", "minimum": 0},
            "label": {"type": "string"},
        },
        "required": ["value", "label"],
    },
    "PlayableItemReleaseDate": {
        "type": "object",
        "properties": {
            "date": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT[0-2]\\d:[0-5]\\d:[0-5]\\dZ|)$",
                "example": "2017-06-26T16:00:28Z",
            },
            "label": {"type": "string", "nullable": True, "example": "26 Jun 2017"},
        },
    },
    "PlayableItemSynopses": {
        "type": "object",
        "properties": {
            "short": {
                "type": "string",
                "example": "A discussion on the different ways of understanding the world around us.",
            },
            "medium": {
                "type": "string",
                "nullable": True,
                "example": "Discussion programme in which guests from different faith and non-faith",
            },
            "long": {
                "type": "string",
                "nullable": True,
                "example": "debate the challenges of today's world.",
            },
        },
        "required": ["short", "medium", "long"],
    },
    "PlayableItemTitles": {
        "type": "object",
        "properties": {
            "primary": {"type": "string", "example": "Beyond Belief"},
            "secondary": {
                "type": "string",
                "nullable": True,
                "example": "Public Grief",
            },
            "tertiary": {
                "type": "string",
                "nullable": True,
                "example": "Lorem ipsum",
            },
        },
        "required": ["primary", "secondary", "tertiary"],
    },
    "PlayableItemUri": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "example": "latest"},
            "label": {"type": "string", "example": "Latest"},
            "uri": {
                "type": "string",
                "example": "/v2/programmes/playable?container=b006s6p6&sort=-available_from_date&type=episode",
            },
        },
        "required": ["type", "label", "uri"],
    },
    "PlayableItemContainer": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "example": "brand"},
            "id": {"type": "string", "example": "b006s6p6"},
            "urn": {"type": "string", "example": "urn:bbc:radio:brand:b006s6p6"},
            "title": {"type": "string", "example": "Beyond Belief"},
            "synopses": {
                "oneOf": [
                    {"$ref": "#/components/schemas/PlayableItemSynopses"},
                    {"$ref": "#/components/schemas/NullValue"},
                ]
            },
            "activities": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/ContainerItemActivity"},
            },
        },
        "required": ["type", "id", "urn", "title", "synopses", "activities"],
    },
    "PlayableItemDownload": {
        "type": "object",
        "nullable": True,
        "properties": {
            "type": {"type": "string", "example": "drm"},
            "quality_variants": {
                "$ref": "#/components/schemas/PlayableItemDownloadQualityVariants"
            },
        },
        "required": ["type", "quality_variants"],
    },
    "PlayableItemDownloadQualityVariants": {
        "type": "object",
        "properties": {
            "low": {
                "$ref": "#/components/schemas/PlayableItemDownloadQualityVariantsValues"
            },
            "medium": {
                "$ref": "#/components/schemas/PlayableItemDownloadQualityVariantsValues"
            },
            "high": {
                "$ref": "#/components/schemas/PlayableItemDownloadQualityVariantsValues"
            },
        },
        "required": ["low", "medium", "high"],
    },
    "PlayableItemDownloadQualityVariantsValues": {
        "type": "object",
        "properties": {
            "bitrate": {"type": "integer", "example": 96},
            "file_url": {
                "type": "string",
                "example": "https://open.live.bbc.co.uk/mediaselector/5/redir/version/2.0/mediaset/audio-nondrm-download/proto/http/vpid/p03t19g4.mp3",
                "nullable": True,
            },
            "label": {"type": "string", "example": "144 MB"},
        },
        "required": ["bitrate", "file_url", "label"],
    },
    "PlayableItemGuidance": {
        "type": "object",
        "properties": {
            "competition_warning": {"type": "boolean"},
            "warnings": {"$ref": "#/components/schemas/PlayableItemGuidanceWarnings"},
        },
        "required": ["competition_warning", "warnings"],
    },
    "PlayableItemGuidanceWarnings": {
        "type": "object",
        "properties": {
            "short": {
                "type": "string",
                "example": "Contains language that may offend.",
            },
            "long": {
                "type": "string",
                "example": "Contains language which some may find offensive.",
            },
        },
        "required": ["short", "long"],
    },
    "Recommendation": {
        "type": "object",
        "properties": {"algorithm": {"type": "string", "nullable": False}},
        "required": ["algorithm"],
    },
    "NullValue": {
        "type": "object",
        "required": ["string"],
        "properties": {"null": {"type": "object"}},
    },
    "ErrorResponse": {
        "type": "object",
        "properties": {
            "$schema": {
                "type": "string",
                "example": "https://rms.api.bbc.co.uk/docs/swagger.json#/definitions/ErrorResponse",
            },
            "errors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/Error"},
            },
        },
        "required": ["$schema", "errors"],
    },
    "Error": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "example": "6ec7045c-2148-40e2-8a92-f3ad57302a69",
            },
            "href": {
                "type": "string",
                "example": "http://confluence.dev.bbc.co.uk/display/RMServices",
            },
            "status": {"type": "integer", "example": 500},
            "message": {"type": "string"},
            "replied_at": {"type": "string", "example": "2018-08-01T15:34:09Z"},
        },
        "required": ["id", "href", "status", "message", "replied_at"],
    },
    "Titles": {
        "type": "object",
        "properties": {
            "primary": {"type": "string"},
            "secondary": {"type": "string"},
            "tertiary": {"type": "string"},
        },
        "required": ["primary", "secondary", "tertiary"],
    },
    "TitlesHierarchy": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["title"]},
            "entity_type": {
                "type": "string",
                "enum": ["brand", "series", "clip", "episode"],
            },
            "pid": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,})$",
            },
            "title": {"type": "string"},
        },
        "required": ["type", "entity_type", "pid", "title"],
    },
    "Position": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["programme_position"]},
            "position": {"type": "integer", "nullable": True, "minimum": 0},
            "total": {"type": "integer", "nullable": True, "minimum": 0},
        },
        "required": ["type", "position", "total"],
    },
    "V2ProgrammeNetwork": {
        "type": "object",
        "properties": {
            "id": {"type": "string", "example": "bbc_world_service"},
            "key": {
                "type": "string",
                "nullable": True,
                "example": "worldserviceradio",
            },
            "short_title": {"type": "string", "example": "World Service"},
            "long_title": {"type": "string", "example": "BBC World Service"},
            "group": {"type": "string", "example": "radio"},
            "active": {"type": "boolean"},
        },
        "required": ["id", "key", "short_title", "long_title", "group", "active"],
    },
    "V2ProgrammeImage": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["standard"]},
            "id": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,})$",
                "example": "p06gcjdb",
            },
            "url": {
                "type": "string",
                "example": "https://ichef.bbci.co.uk/images/ic/{recipe}/p06gcjdb.jpg",
            },
        },
        "required": ["type", "id", "url"],
    },
    "V2ProgrammeCategory": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["genre", "format"]},
            "id": {"type": "string", "example": "factual-scienceandnature"},
            "key": {"type": "string", "example": "scienceandnature"},
            "title": {"type": "string", "example": "Science & Nature"},
        },
        "required": ["type", "id", "key", "title"],
    },
    "V2ProgrammeAncestors": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["brand", "series", "episode"]},
            "id": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,})$",
                "example": "p002w557",
            },
            "title": {"type": "string", "example": "Discovery"},
        },
        "required": ["type", "id", "title"],
    },
    "V2ProgrammeAvailability": {
        "type": "object",
        "properties": {
            "type": {
                "type": "string",
                "enum": ["original", "podcast", "editorial", "legal", "technical"],
            },
            "id": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,})$",
                "example": "w4hqry66",
            },
            "duration": {"type": "integer", "minimum": 0, "example": 1590},
            "guidance": {"$ref": "#/components/schemas/PlayableItemGuidance"},
            "has_guidance": {"type": "boolean"},
            "available_from_date": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT[0-2]\\d:[0-5]\\d:[0-5]\\dZ|)$",
                "example": "2018-08-06T20:00:48Z",
            },
            "available_to_date": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT[0-2]\\d:[0-5]\\d:[0-5]\\dZ|)$",
                "example": "2019-08-06T20:00:48Z",
            },
            "status": {
                "type": "string",
                "enum": ["available", "pending", "future"],
            },
            "download": {"$ref": "#/components/schemas/PlayableItemDownload"},
        },
        "required": [
            "type",
            "id",
            "duration",
            "guidance",
            "has_guidance",
            "available_from_date",
            "available_to_date",
            "status",
            "download",
        ],
    },
    "Programme": {
        "type": "object",
        "properties": {
            "id": {
                "type": "string",
                "pattern": "^([0-9|b-d|f-h|j-n|p-t|v-z]{8,})$",
                "example": "w3csxh9f",
            },
            "network": {"$ref": "#/components/schemas/V2ProgrammeNetwork"},
            "titles": {"$ref": "#/components/schemas/PlayableItemTitles"},
            "synopses": {
                "oneOf": [
                    {"$ref": "#/components/schemas/PlayableItemSynopses"},
                    {"$ref": "#/components/schemas/NullValue"},
                ]
            },
            "images": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/V2ProgrammeImage"},
            },
            "categories": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/V2ProgrammeCategory"},
            },
        },
        "required": ["id", "network", "titles", "synopses", "images", "categories"],
        "oneOf": [
            {"$ref": "#/components/schemas/V2Episode"},
            {"$ref": "#/components/schemas/V2Clip"},
            {"$ref": "#/components/schemas/V2Brand"},
            {"$ref": "#/components/schemas/V2Series"},
        ],
    },
    "Programmes": {
        "type": "object",
        "properties": {
            "total": {"type": "integer", "minimum": 0, "example": 305812},
            "limit": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "example": 30,
            },
            "offset": {"type": "integer", "minimum": 0, "example": 0},
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/Programme"},
            },
        },
        "required": ["total", "limit", "offset", "data"],
    },
    "SingleItemPromosResponse": {
        "type": "object",
        "properties": {
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/SingleItemPromo"},
            }
        },
        "required": ["data"],
    },
    "SingleItemPromo": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["single_item_promo"]},
            "id": {
                "type": "string",
                "format": "uuid",
                "pattern": "^[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}$",
                "example": "d3157051-ac4c-43bc-9977-dc5b77cf7453",
            },
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:single_item_promo:[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12}$",
                "example": "urn:bbc:radio:single_item_promo:d3157051-ac4c-43bc-9977-dc5b77cf7453",
            },
            "title": {"type": "string"},
            "description": {"type": "string"},
            "image_pid": {"type": "string"},
            "label": {"type": "string"},
            "start_time": {"type": "string"},
            "end_time": {"type": "string"},
            "item": {
                "oneOf": [
                    {"$ref": "#/components/schemas/PlayableItem"},
                    {"$ref": "#/components/schemas/ContainerItem"},
                ]
            },
        },
        "required": ["type", "id", "urn", "title", "item"],
    },
    "V2Episode": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["episode"]},
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:episode:[0-9|b-d|f-h|j-n|p-t|v-z]{8,}$",
                "example": "urn:bbc:radio:episode:w3csxh9f",
            },
            "media_type": {
                "type": "string",
                "enum": ["audio", "video", "audio_video", "null"],
            },
            "release_date": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT00:00:00Z|)$",
                "example": "2018-08-06T00:00:00Z",
            },
            "siblings_count": {"type": "integer", "minimum": 0, "example": 2},
            "position": {"$ref": "#/components/schemas/V2Position"},
            "ancestors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/V2ProgrammeAncestors"},
            },
            "availability": {"$ref": "#/components/schemas/V2ProgrammeAvailability"},
        },
        "required": [
            "type",
            "urn",
            "media_type",
            "release_date",
            "siblings_count",
            "position",
            "ancestors",
            "availability",
        ],
    },
    "V2Clip": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["clip"]},
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:clip:[0-9|b-d|f-h|j-n|p-t|v-z]{8,}$",
                "example": "urn:bbc:radio:clip:w3csxh9f",
            },
            "media_type": {
                "type": "string",
                "enum": ["audio", "video", "audio_video", "null"],
            },
            "release_date": {
                "type": "string",
                "nullable": True,
                "pattern": "^(\\d{4}-[0-1]\\d-[0-3]\\dT00:00:00Z|)$",
                "example": "2018-08-06T00:00:00Z",
            },
            "siblings_count": {"type": "integer", "minimum": 0, "example": 2},
            "position": {"$ref": "#/components/schemas/V2Position"},
            "ancestors": {
                "items": {"$ref": "#/components/schemas/V2ProgrammeAncestors"}
            },
            "availability": {"$ref": "#/components/schemas/V2ProgrammeAvailability"},
        },
        "required": [
            "type",
            "urn",
            "media_type",
            "release_date",
            "siblings_count",
            "position",
            "ancestors",
            "availability",
        ],
    },
    "V2Brand": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["brand"]},
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:brand:[0-9|b-d|f-h|j-n|p-t|v-z]{8,}$",
                "example": "urn:bbc:radio:brand:p002w557",
            },
        },
        "required": ["type", "urn"],
    },
    "V2Series": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["series"]},
            "urn": {
                "type": "string",
                "pattern": "^urn:bbc:radio:series:[0-9|b-d|f-h|j-n|p-t|v-z]{8,}$",
                "example": "urn:bbc:radio:brand:w27vq14h",
            },
            "ancestors": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/V2ProgrammeAncestors"},
            },
        },
        "required": ["type", "urn", "ancestors"],
    },
    "V2Position": {
        "type": "object",
        "properties": {
            "position": {
                "type": "integer",
                "nullable": True,
                "minimum": 0,
                "example": 2,
            },
            "total": {
                "type": "integer",
                "nullable": True,
                "minimum": 0,
                "example": 5,
            },
        },
        "required": ["position", "total"],
    },
    "V2CategoriesResponse": {
        "type": "object",
        "properties": {
            "$schema": {
                "type": "string",
                "example": "https://rms.api.bbc.co.uk/docs/swagger.json#/definitions/V2CategoriesResponse",
            },
            "total": {"type": "integer", "minimum": 0, "example": 27},
            "offset": {"type": "integer", "minimum": 0, "example": 0},
            "limit": {
                "type": "integer",
                "minimum": 0,
                "maximum": 100,
                "example": 30,
            },
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/Category"},
            },
        },
        "required": ["total", "offset", "limit", "data"],
    },
    "V2NetworksResponse": {
        "type": "object",
        "properties": {
            "$schema": {"type": "string"},
            "total": {"type": "integer", "minimum": 0},
            "offset": {"type": "integer", "minimum": 0},
            "limit": {"type": "integer", "minimum": 0, "maximum": 100},
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/V2Network"},
            },
        },
        "required": ["total", "offset", "limit", "data"],
    },
    "V2Network": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["network"]},
            "id": {
                "type": "string",
                "pattern": "^[a-z0-9_]+$",
                "example": "bbc_radio_one",
            },
            "coverage": {
                "type": "string",
                "enum": ["national", "regional", "local"],
            },
            "key": {
                "type": "string",
                "pattern": "^[a-z0-9]+$",
                "example": "radio1",
            },
            "short_title": {"type": "string", "example": "Radio 1"},
            "long_title": {"type": "string", "example": "BBC Radio 1"},
            "services": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/V2Service"},
            },
        },
        "required": [
            "type",
            "id",
            "coverage",
            "key",
            "short_title",
            "long_title",
            "services",
        ],
    },
    "V2Service": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["service"]},
            "id": {
                "type": "string",
                "pattern": "^[a-z0-9_]+$",
                "example": "bbc_radio_one",
            },
        },
        "required": ["type", "id"],
    },
    "ExperienceContainerResponse": {
        "type": "object",
        "properties": {
            "$schema": {"type": "string"},
            "data": {
                "type": "array",
                "items": {
                    "allOf": [
                        {"$ref": "#/components/schemas/HeaderModule"},
                        {"$ref": "#/components/schemas/DisplayModule"},
                    ]
                },
            },
        },
        "required": ["$schema", "data"],
    },
    "HeaderModule": {
        "type": "object",
        "properties": {
            "type": {"type": "string", "enum": ["header_module"]},
            "id": {"type": "string", "enum": ["container"]},
            "style": {"type": "string", "nullable": True},
            "title": {"type": "string", "example": "Composer of the Week"},
            "description": {
                "type": "string",
                "example": "Radio 3's Composer of the Week series",
            },
            "data": {"$ref": "#/components/schemas/ContainerItem"},
        },
        "required": ["type", "id", "style", "title", "description", "data"],
    },
    "PlayableItemNext": {
        "type": "object",
        "properties": {
            "current": {"$ref": "#/components/schemas/PlayableItem"},
            "next": {"$ref": "#/components/schemas/PlayableItem"},
        },
        "required": ["current"],
    },
    "PlayableItemsNextResponse": {
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "offset": {"type": "integer"},
            "limit": {"type": "integer"},
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/PlayableItemNext"},
            },
        },
        "required": ["data"],
    },
    "ExperienceNameResponse": {
        "type": "object",
        "properties": {"experience": {"type": "string", "example": "domestic"}},
        "required": ["experience"],
    },
    "ExperienceViewResponse": {
        "type": "object",
        "properties": {
            "$schema": {"type": "string"},
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/View"},
            },
        },
        "required": ["$schema", "data"],
    },
    "ExperienceExperimentsAttributesResponse": {
        "type": "object",
        "properties": {"au35": {"type": "boolean"}},
        "required": ["au35"],
    },
    "View": {
        "type": "object",
        "properties": {
            "type": {"type": "string"},
            "id": {"type": "string"},
            "title": {"type": "string"},
            "uri": {"type": "string"},
        },
        "required": ["type", "id", "title"],
    },
    "ServicesResponse": {
        "type": "object",
        "properties": {
            "total": {"type": "integer"},
            "limit": {"type": "integer"},
            "offset": {"type": "integer"},
            "data": {
                "type": "array",
                "items": {"$ref": "#/components/schemas/ServiceGreenDay"},
            },
        },
        "required": ["total", "limit", "offset", "data"],
    },
}
responses = {
    "InternalServiceError": {
        "description": "There is an internal service error",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    },
    "Unauthorized": {
        "description": "Authorization token is invalid or Expired",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    },
    "Notfound": {
        "description": "Not found",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    },
    "BadRequest": {
        "description": "Invalid value provided",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    },
    "GatewayTimeout": {
        "description": "server error response code indicates that the server, while acting as a gateway or proxy, did not get a response in time from the upstream server that it needed in order to complete the request.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    },
    "BadGateway": {
        "description": "server error response code indicates that the server, while acting as a gateway or proxy, received an invalid response from the upstream server.",
        "content": {
            "application/json": {
                "schema": {"$ref": "#/components/schemas/ErrorResponse"}
            }
        },
    },
    "TextResponse": {
        "description": "Request successfully sent to UAS.",
        "content": {
            "text:plain": {
                "schema": {
                    "type": "string",
                    "example": "The request has been accepted for processing, but the processing has not been completed.",
                }
            }
        },
    },
    "v1ErrorStates": {
        "description": "Error",
        "content": {
            "application/json": {
                "schema": {
                    "type": "object",
                    "properties": {"error": {"type": "string", "example": "Not found"}},
                }
            }
        },
    },
    "RadioErrorMessage": {
        "description": "Unexpected error",
        "content": {
            "application/json": {
                "schema": {
                    "$ref": "#/components/schemas/PersonalisedRadioErrorResponse"
                }
            }
        },
    },
}


urls = {
    "/v2/experience/player/{pid}": {
        "get": {
            "summary": "On Demand Page Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Non inline On Demand Experince which consist of display modules of Player and Playqueue. <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/categories": {
        "get": {
            "summary": "Categories Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience categories index page <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/container/{urn}": {
        "get": {
            "summary": "Container Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/urn"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/hero-enabled"},
                {"$ref": "#/components/parameters/tag-enabled"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {
                    "name": "sort",
                    "in": "query",
                    "description": "Apply sort to Container programmes (for category urns only)",
                    "schema": {
                        "type": "string",
                        "enum": ["latest", "popular", "title"],
                    },
                    "required": False,
                },
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/hero_enabled"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience Container page. Brand, Series or Category <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/stations": {
        "get": {
            "summary": "All stations Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline All stations Page Experience <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/search": {
        "get": {
            "summary": "Search Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience search results container and playable items as display modules <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/sounds/sign-in": {
        "get": {
            "summary": "Sign in Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/X-Experiments"},
            ],
            "tags": ["Experience"],
            "description": "Inline Sign in Experience page with Upsell <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/listen/sign-in": {
        "get": {
            "summary": "Sign-in Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": ["priority_brands", "music_mixes", "collections"],
                    },
                    "required": False,
                },
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience sign in page with Upsell at top <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/play/{service_id}": {
        "get": {
            "summary": "Play Live Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/hide"},
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": [
                            "play (broadcast summary)",
                            "recent_tracks",
                            "network_promos",
                        ],
                    },
                    "required": False,
                },
            ],
            "tags": ["Experience"],
            "description": "Inline Experience Play Live page used for https://www.bbc.co.uk/sounds/play/live:<network_id> <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/play/{programme_id}": {
        "get": {
            "summary": "Play On Demand Experience",
            "parameters": [
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/hide"},
                {"$ref": "#/components/parameters/programme_id"},
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {"$ref": "#/components/parameters/play_context"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": ["play (programme)", "recent_tracks", "play_queue"],
                    },
                    "required": False,
                },
            ],
            "tags": ["Experience"],
            "description": "Inline Experience Play On Demand page used for https://www.bbc.co.uk/sounds/play/live:<programme_id> <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/play/{container_urn}": {
        "get": {
            "summary": "Play On Demand Experience Container",
            "parameters": [
                {"$ref": "#/components/parameters/hide"},
                {"$ref": "#/components/parameters/container_urn"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience Play On Demand response for container URNs which returns the first item of the specified container to play <span>🎶</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "400": {
                    "description": "Bad Request",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/responses/BadRequest"}
                        }
                    },
                },
                "404": {
                    "description": "Not Found (or Container empty)",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/responses/Notfound"}
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/schedules/{service_id}": {
        "get": {
            "summary": "Schedules Inline Experience API by service id",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience for a service's broadcasts schedule <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/schedules/{service_id}/{date}": {
        "get": {
            "summary": "Schedules Inline Experience API of a service by date",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/date"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience for selected date's & service broadcasts schedule <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/music": {
        "get": {
            "summary": "Inline Music Page",
            "parameters": [
                {"$ref": "#/components/parameters/X-international-experience-name"}
            ],
            "tags": ["Experience"],
            "description": "Inline Experience for the music page <span>🎶</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineMusicResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/inline/speech": {
        "get": {
            "summary": "Inline Speech Page (Podcasts)",
            "parameters": [
                {"$ref": "#/components/parameters/X-international-experience-name"}
            ],
            "tags": ["Experience"],
            "description": "Inline Experience for the Speech page <span>🎶</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineSpeechResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/listen/sign-in": {
        "get": {
            "summary": "Provides a typical landing page with sign in upsell",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Provides a typical landing page with sign in upsell. <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/stations": {
        "get": {
            "summary": "Provides a list promoted and local stations",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Provides promoted and local station display items <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/categories": {
        "get": {
            "summary": "List of categories",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CategoryKind"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Categories"],
            "description": "Retrieve Categories <span>🎶</span> M83\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CategoriesResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/categories/{id}": {
        "get": {
            "summary": "Category by ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CategoryId"},
            ],
            "tags": ["Categories"],
            "description": "Retrieve Categories by ID <span>🎶</span> M83\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/CategoriesResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/categories": {
        "get": {
            "summary": "List of categories",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CategoryKind"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Categories"],
            "description": "Retrieve Categories <span>🎶</span> M83\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/V2CategoriesResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/categories/{id}": {
        "get": {
            "summary": "Category by ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CategoryId"},
            ],
            "tags": ["Categories"],
            "description": "Retrieve category <span>🎶</span> M83\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/Category"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/categories/container": {
        "get": {
            "summary": "List of container categories",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CategoryKind"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Categories"],
            "description": "Retrieve Sounds supported categories in container item form <span>🎶</span> M83\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/categories/{id}/container": {
        "get": {
            "summary": "Container category by ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CategoryId"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Categories"],
            "description": "Retrieve category container <span>🎶</span> M83\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/radio/networks.json": {
        "get": {
            "summary": "Networks",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {
                    "name": "preset",
                    "in": "query",
                    "description": "Returns all networks needed for iPlayer Radio responsive web navigation",
                    "schema": {"type": "boolean"},
                    "required": False,
                },
                {
                    "name": "international",
                    "in": "query",
                    "description": "Returns all networks available internationally",
                    "schema": {"type": "boolean"},
                    "required": False,
                },
            ],
            "tags": ["Networks"],
            "description": "All iPlayer Radio networks - contains business logic for masterbrand and service relationships <span>🎶</span> Half Japanese\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/NetworksResponse"}
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks": {
        "get": {
            "summary": "List of networks",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/coverage"},
                {"$ref": "#/components/parameters/promoted"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Networks"],
            "description": "Provides the list of all the v2 networks <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/V2NetworksResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/playable": {
        "get": {
            "summary": "List of playable networks",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/coverage"},
                {"$ref": "#/components/parameters/promoted"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Networks"],
            "description": "Provides the list of all the playable networks <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/{id}": {
        "get": {
            "summary": "Network by ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/NetworkId"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/offset"},
            ],
            "tags": ["Networks"],
            "description": "Provides the V2 network by network ID. <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/V2Network"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/{id}/playable": {
        "get": {
            "summary": "Playable network by ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/NetworkId"},
            ],
            "tags": ["Networks"],
            "description": "Provides the network playable item by network ID. <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PlayableItem"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/{id}/promos/display": {
        "get": {
            "summary": "Display promos by network ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/NetworkId"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Networks"],
            "description": "Provides diplay promos items for a network ID. <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/DisplayItemsResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/{id}/promos/display/container": {
        "get": {
            "summary": "Display promos container by network ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/NetworkId"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Networks"],
            "description": "Provides a container item for the display promos. <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/{id}/promos/playable": {
        "get": {
            "summary": "Playable promos by network ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/NetworkId"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Networks"],
            "description": "Provides playable items by promos for a network ID. <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/{id}/promos/playable/container": {
        "get": {
            "summary": "Playable promos container by network ID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/NetworkId"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Networks"],
            "description": "Provides a container item for the playable promos. <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/networks/services": {
        "get": {
            "summary": "List of services",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/supported"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Networks"],
            "description": "Provides the list of all the v2 services from networks <span>🎶</span> Green Day\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ServicesResponse"}
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/services/{sid}/tracks/latest/playable": {
        "get": {
            "summary": "List of recently playable tracks",
            "parameters": [
                {"$ref": "#/components/parameters/sid"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Tracks"],
            "description": "Retrieve list of tracks as playable items for a service <span>🎶</span> Deftones\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/versions/{vpid}/tracks/display": {
        "get": {
            "summary": "List of on demand tracks",
            "parameters": [{"$ref": "#/components/parameters/vpid"}],
            "tags": ["Tracks"],
            "description": "Retrieve list of on demand tracks as display items for a version id <span>🎶</span> Deftones\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/DisplayItemsResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/services/{sid}/segments/latest": {
        "get": {
            "summary": "List of latest segments",
            "parameters": [
                {"$ref": "#/components/parameters/sid"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Tracks"],
            "description": "Retrieve list of Music and Classical segments for a service <span>🎶</span> Deftones\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/SegmentsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/versions/{vpid}/segments": {
        "get": {
            "summary": "List of on demand tracks",
            "parameters": [{"$ref": "#/components/parameters/vpid"}],
            "tags": ["Tracks"],
            "description": "Retrieve list of on demand tracks as segments for a version id <span>🎶</span> Deftones\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/SegmentsResponse"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/broadcasts": {
        "get": {
            "summary": "Broadcasts",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {
                    "name": "service",
                    "in": "query",
                    "description": "Filter by Service ID. E.g. bbc_radio_fourfm",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "date",
                    "in": "query",
                    "description": "Filter by date. E.g. 2016-06-17",
                    "required": False,
                    "schema": {"type": "string"},
                },
                {
                    "name": "sort",
                    "in": "query",
                    "description": "Sort by provided query. E.g. 'start_at' sorts in ascending order, and '-start_at' sorts in descending order",
                    "required": False,
                    "schema": {
                        "type": "string",
                        "enum": ["start_at", "-start_at", "end_at", "-end_at"],
                    },
                },
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Broadcasts"],
            "description": "All broadcasts <span>🎶</span> Guns & Roses\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/BroadcastsResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/broadcasts/{pid}": {
        "get": {
            "summary": "Broadcasts by PID",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {
                    "name": "pid",
                    "in": "path",
                    "description": "Broadcast id",
                    "schema": {"type": "string"},
                    "example": "p01lhbfm",
                    "required": True,
                },
            ],
            "tags": ["Broadcasts"],
            "description": "Find broadcast by PID <span>🎶</span> Guns & Roses\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/BroadcastsResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/broadcasts/latest": {
        "get": {
            "summary": "Latest Broadcasts",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/BroadcastService"},
                {
                    "name": "on_air",
                    "in": "query",
                    "description": "Filter what is on air. E.g. 'now' returns current programme being broadcasted.",
                    "schema": {"type": "string", "enum": ["now", "previous", "next"]},
                },
                {
                    "name": "next",
                    "in": "query",
                    "description": "Filter what will be on air next in minutes. E.g. '240' returns programmes broadcasted in the next four hours",
                    "schema": {"type": "string"},
                },
                {
                    "name": "previous",
                    "in": "query",
                    "description": "Filter what was on air previously in minutes. E.g. '240' returns programmes broadcasted in the previous four hours",
                    "schema": {"type": "string"},
                },
                {"$ref": "#/components/parameters/BroadcastSort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Broadcasts"],
            "description": "Broadcasts for the current day <span>🎶</span> Guns & Roses\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/BroadcastsResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/broadcasts/poll/{service_id}": {
        "get": {
            "summary": "Polled Broadcasts by serviceId",
            "parameters": [
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Broadcasts"],
            "description": "Provide 5 upcoming broadcasts for a network service <span>🎶</span> Guns & Roses\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PollBroadcastsSummaryResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/broadcasts/schedules/{service_id}/{date}": {
        "get": {
            "summary": "Broadcasts'schedule for a given date and service",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/date"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Broadcasts"],
            "description": "Broadcasts schedule for a given service and date which is in next 7 or 30 previous days <span>🎶</span> Guns & Roses\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/BroadcastsSummaryResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/broadcasts/poll/{service_id}": {
        "get": {
            "summary": "Personalised Polled Broadcasts by serviceId",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Broadcasts"],
            "description": "Provide 5 upcoming broadcasts for a network service with personalised data <span>🎶</span> Guns & Roses\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/BroadcastSummary"}
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/container": {
        "get": {
            "summary": "Container Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/network"},
                {"$ref": "#/components/parameters/networkUrlKey"},
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/parent"},
                {"$ref": "#/components/parameters/container"},
                {"$ref": "#/components/parameters/type"},
                {"$ref": "#/components/parameters/withAvailableType"},
                {"$ref": "#/components/parameters/experience"},
                {
                    "name": "type",
                    "in": "query",
                    "description": "Filter by programme type. Accepts comma separated values",
                    "schema": {"type": "string", "enum": ["brand", "series"]},
                    "required": False,
                },
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Programmes"],
            "description": "Provides a paginated list of container programmes (brand and series).\nAccepts various filters and sorting methods. When sorting by popularity, this parameter only works with the category filter<span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/container/pids": {
        "get": {
            "summary": "Batch Programme Containers By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns requested container items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/playable": {
        "get": {
            "summary": "Playable Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/network"},
                {"$ref": "#/components/parameters/networkUrlKey"},
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/allCategories"},
                {"$ref": "#/components/parameters/parent"},
                {"$ref": "#/components/parameters/container"},
                {"$ref": "#/components/parameters/experience"},
                {
                    "name": "type",
                    "in": "query",
                    "description": "Filter by programme type. Accepts comma separated values",
                    "schema": {"type": "string", "enum": ["episode", "clip"]},
                    "required": False,
                },
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Programmes"],
            "description": "Provides a paginated list of playable programmes (episodes and clips).\nAccepts various filters and sorting methods. When sorting by popularity, this parameter only works with the category filter<span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/{pid}/playable": {
        "get": {
            "summary": "Single Playable Programme By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns single playable item by a programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/playqueue/{pid}": {
        "get": {
            "summary": "Play Queue",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/context"},
                {"$ref": "#/components/parameters/play_context"},
            ],
            "tags": ["Programmes"],
            "description": "provides the list of playable items as play queue based on the programme id <span>🎶</span> Boyzone\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/search/playable": {
        "get": {
            "summary": "Search Playable Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Provides search keywords results as list of playable items <span>🔎</span> The Seekers <span>🔎</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/search/container": {
        "get": {
            "summary": "Search Container Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Provides search keywords results as list of container items <span>🔎</span> The Seekers <span>🔎</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/collections/{pid}/container": {
        "get": {
            "summary": "Single Container Collection By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Collection container item for a collection pid <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/collections/{pid}/members": {
        "get": {
            "summary": "Collection Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "All member items from Collection <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/collections/{pid}/members/playable": {
        "get": {
            "summary": "Collection Playable Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Playable Items from Collection <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/collections/{pid}/members/container": {
        "get": {
            "summary": "Collection Container Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Container Items from Collection <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/collections/{pid}/members/latest/playable": {
        "get": {
            "summary": "Collection Latest Playable Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Latest Playable Items from Collection <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/curations/{pid}/container": {
        "get": {
            "summary": "Single Container Curation By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CurationPid"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Curations"],
            "description": "Curation container item for a curation pid <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/curations/{pid}/members/container": {
        "get": {
            "summary": "Curation Container Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CurationPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Curations"],
            "description": "Container Items from Curation <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/curations/{pid}/members/playable": {
        "get": {
            "summary": "Curation Playable Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CurationPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Curations"],
            "description": "Playable Items from Curation <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience/car": {
        "get": {
            "summary": "Index In-car Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Index In-car Experience <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceViewResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/podcasts": {
        "get": {
            "summary": "All Podcasts",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/podcastsort"},
                {
                    "name": "network",
                    "in": "query",
                    "description": "Network Master Brand ID (mid)",
                    "schema": {"type": "string", "example": "bbc_radio_one"},
                    "required": False,
                },
                {
                    "name": "network_url_key",
                    "in": "query",
                    "description": "Network URL key",
                    "schema": {"type": "string", "example": "radio1"},
                    "required": False,
                },
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/coverage"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Podcasts"],
            "description": "Retrieve all Podcasts <span>🎶</span> Cast\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PodcastsResponse"}
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/podcasts/featured": {
        "get": {
            "summary": "Featured Podcasts",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Podcasts"],
            "description": "Retrieve featured podcasts <span>🎶</span> Cast\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PodcastsFeaturedResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/podcasts/{pid}": {
        "get": {
            "summary": "Podcast",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/PodcastPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Podcasts"],
            "description": "Retrieve data about the podcast with the supplied PID <span>🎶</span> Cast\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/PodcastsResponse"}
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/podcasts/{pid}/episodes": {
        "get": {
            "summary": "Podcast Episodes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/PodcastPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Podcasts"],
            "description": "Retrieve all episodes for a specific podcast <span>🎶</span> Cast\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PodcastEpisodesResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/podcasts/{pid}/episodes/playable": {
        "get": {
            "summary": "Podcast Episodes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/PodcastPid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Podcasts"],
            "description": "Retrieve all episodes for a specific podcast as Playable items <span>🎶</span> Cast\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/radio/programmes": {
        "get": {
            "deprecated": True,
            "summary": "Radio programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/network"},
                {"$ref": "#/components/parameters/networkUrlKey"},
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/container"},
                {
                    "name": "kind",
                    "in": "query",
                    "description": "Filter by provided query. E.g. 'tleo' returns top level objects, ie. brands, orphaned series, and orphaned episodes",
                    "schema": {"type": "string", "enum": ["tleo"]},
                    "required": False,
                },
                {
                    "name": "sort",
                    "in": "query",
                    "description": "Sort by provided query. E.g. 'title' sorts in ascending order, and -title sorts in descending order",
                    "schema": {
                        "type": "string",
                        "enum": [
                            "available_from_date",
                            "-available_from_date",
                            "title",
                            "-title",
                        ],
                    },
                    "required": False,
                },
                {
                    "name": "type",
                    "in": "query",
                    "description": "Filter by programme type. Accepts comma separated values",
                    "schema": {
                        "type": "string",
                        "enum": [
                            "brand",
                            "series",
                            "episode",
                            "clip",
                            "episode,clip",
                            "brand,series",
                        ],
                    },
                    "required": False,
                },
                {
                    "name": "media_type",
                    "in": "query",
                    "description": "Filter by media type (audio_video will return video values)",
                    "schema": {
                        "type": "string",
                        "enum": ["audio", "video", "audio_video"],
                    },
                    "required": False,
                },
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Programmes"],
            "description": "Provides a paginated list of programmes by PID (brand, series, episode and clip). Accepts various filters and sorting methods. <span>🎶</span> Blur\n",
            "operationId": "getRadioProgrammes",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ProgrammesResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/radio/programmes/{pid}": {
        "get": {
            "deprecated": True,
            "summary": "Available radio programme by Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
            ],
            "tags": ["Programmes"],
            "description": "Find programmes by PID (brand, series, episode and clip) <span>🎶</span> Blur\n",
            "operationId": "getRadioProgrammesByPid",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ProgrammesResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/activities": {
        "post": {
            "summary": "Write Activity",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "requestBody": {
                "description": "Body for the activities follow or favourites",
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "urn": {
                                    "type": "string",
                                    "example": "urn:bbc:radio:episode:b08vxv2w",
                                }
                            },
                            "required": ["urn"],
                        }
                    }
                },
            },
            "tags": ["Personalised Activities"],
            "description": "Accepts the URN as body and start process write activity to UAS <span>🎶</span> Stereophonics\n",
            "responses": {
                "202": {"$ref": "#/components/responses/TextResponse"},
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/activities/{urn}": {
        "delete": {
            "summary": "Delete Activity",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/urn"},
            ],
            "tags": ["Personalised Activities"],
            "description": "Accepts the URN and start process delete activity from UAS <span>🎶</span> Stereophonics\n",
            "responses": {
                "202": {"$ref": "#/components/responses/TextResponse"},
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/collections/{pid}/members/playable": {
        "get": {
            "summary": "Personalised Collection Playable Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Personalised Playable Items from Collection <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/collections/{pid}/members/container": {
        "get": {
            "summary": "Personalised Collection Containers",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Personalised collection container item for a collection pid <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/collections/{pid}/members/latest/playable": {
        "get": {
            "summary": "Personalised Collection Latest Playable Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CollectionPid"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Collections"],
            "description": "Personalised Latest Playable Items from Collection <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/curations/{pid}/members/container": {
        "get": {
            "summary": "Personalised Curation Containers",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CurationPid"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Curations"],
            "description": "Personalised curations container item for a curation pid <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContainerItem"}
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/curations/{pid}/members/playable": {
        "get": {
            "summary": "Personalised Curation Playable Members",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/CurationPid"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Curations"],
            "description": "Personalised Playable Items from Curation <span>🎶</span> Depeche Mode\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/categories": {
        "get": {
            "summary": "Personalised Categories Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Personalised Inline Experience categories index page <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/container/{urn}": {
        "get": {
            "summary": "Personalised Container Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/urn"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {
                    "name": "sort",
                    "in": "query",
                    "description": "Apply sort to Container programmes (for category urns only)",
                    "schema": {
                        "type": "string",
                        "enum": ["latest", "popular", "title"],
                    },
                    "required": False,
                },
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/hero_enabled"},
            ],
            "tags": ["Experience"],
            "description": "Personalised Inline Experience Container page. Brand, Series or Category <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/listen": {
        "get": {
            "summary": "Listen Page Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": [
                            "priority_brands",
                            "music_mixes",
                            "collections",
                            "recommendations",
                            "listen_later",
                        ],
                    },
                    "required": False,
                },
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {"$ref": "#/components/parameters/X-forwarded-for"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience listen page API <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/play/{service_id}": {
        "get": {
            "summary": "Personalised Live Play Experience",
            "parameters": [
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/PollService_id"},
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": [
                            "play (broadcast summary)",
                            "recent_tracks",
                            "network_promos",
                            "recommendations",
                        ],
                    },
                    "required": False,
                },
            ],
            "tags": ["Experience"],
            "description": "Personalised Inline Experience Live Play page used for https://www.bbc.co.uk/sounds/play/live:<network_id> <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/play/{programme_id}": {
        "get": {
            "summary": "Personalised On Demand Play Experience",
            "parameters": [
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/hide"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/programme_id"},
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {"$ref": "#/components/parameters/context"},
                {"$ref": "#/components/parameters/play_context"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": [
                            "play (programme)",
                            "recent_tracks",
                            "play_queue",
                            "recommendations",
                        ],
                    },
                    "required": False,
                },
            ],
            "tags": ["Experience"],
            "description": "Personalised Inline Experience On Demand page used for https://www.bbc.co.uk/sounds/play/live:<programme_id> <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/play/{container_urn}": {
        "get": {
            "summary": "Personalised Play On Demand Experience Container",
            "parameters": [
                {"$ref": "#/components/parameters/hide"},
                {"$ref": "#/components/parameters/container_urn"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Personalised Inline Experience Play On Demand response for container URNs which returns the first item of the specified container to play <span>🎶</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/sounds": {
        "get": {
            "summary": "My Sounds Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {
                    "name": "module",
                    "in": "query",
                    "description": "Apply pagination for module",
                    "schema": {
                        "type": "string",
                        "enum": ["favourites", "follows", "latest"],
                    },
                    "required": False,
                },
                {"$ref": "#/components/parameters/fallback"},
                {"$ref": "#/components/parameters/X-Experiments"},
            ],
            "tags": ["Experience"],
            "description": "Inline My Sounds Experience API <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/search": {
        "get": {
            "summary": "Personalised Search Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Personalised Inline Experience search results container and playable items as display modules <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/music": {
        "get": {
            "summary": "Inline Personalised Music Page",
            "parameters": [
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {"$ref": "#/components/parameters/X-Experiments"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience for the music page <span>🎶</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineMusicResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/inline/speech": {
        "get": {
            "summary": "Inline Personalised Speech Page (Podcasts)",
            "parameters": [
                {"$ref": "#/components/parameters/X-international-experience-name"}
            ],
            "tags": ["Experience"],
            "description": "Inline Experience for the Speech page <span>🎶</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineSpeechResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/listen": {
        "get": {
            "summary": "Provides a signed in landing page",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Provides a signed in landing page with listen live, priority brands, continue listening, music mixes, daily pics, recommendations etc. <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/sounds": {
        "get": {
            "summary": "Provides a personalised latest list of playables",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Provides a latest list of favourite shows, music mixes and podcasts <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/player/{pid}": {
        "get": {
            "summary": "Personalised On Demand Page Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Non inline personalised On Demand Experince which consist of display modules of Player, Playqueue and Recommendations. <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/container/{urn}": {
        "get": {
            "summary": "Personalised Containers Page Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/urn"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Display the container details along with the personalised playable items of the container <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceContainerResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/playable/{episode_urn}": {
        "get": {
            "summary": "Personalised episode details",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/episode_urn"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
                {"$ref": "#/components/parameters/X-forwarded-for"},
                {"$ref": "#/components/parameters/show_tracklist"},
            ],
            "tags": ["Experience"],
            "description": "Personalised episode details feed which consist of Episode Details and Track List <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/car/browse": {
        "get": {
            "summary": "Browse page Inline Experience",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/X-international-experience-name"},
            ],
            "tags": ["Experience"],
            "description": "Inline Experience in-car browse page API <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceInlineResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/experience/experiment-attributes": {
        "get": {
            "summary": "<Temporary> User attributes per experiments",
            "parameters": [
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/X-API-Key"},
            ],
            "tags": ["Experience", "Experiments"],
            "description": "Temporary experiment attributes per user Experience <span>🎶</span> Jimi Hendrix\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceExperimentsAttributesResponse"
                            }
                        }
                    },
                },
                "401": {
                    "404": {"$ref": "#/components/responses/Notfound"},
                    "$ref": "#/components/responses/Unauthorized",
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/container": {
        "get": {
            "summary": "Container Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/network"},
                {"$ref": "#/components/parameters/networkUrlKey"},
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/parent"},
                {"$ref": "#/components/parameters/container"},
                {"$ref": "#/components/parameters/type"},
                {"$ref": "#/components/parameters/withAvailableType"},
                {"$ref": "#/components/parameters/experience"},
                {
                    "name": "type",
                    "in": "query",
                    "description": "Filter by programme type. Accepts comma separated values",
                    "schema": {"type": "string", "enum": ["brand", "series"]},
                    "required": False,
                },
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Provides a paginated list of personalised container programmes (brand and series).\nAccepts various filters and sorting methods. When sorting by popularity, this parameter only works with the category filter\n<span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/container/pids": {
        "get": {
            "summary": "Batch Programme Containers By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns requested personalised container items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/plays": {
        "post": {
            "summary": "Write Play Event",
            "parameters": [{"$ref": "#/components/parameters/Authorization"}],
            "requestBody": {
                "description": "Body for the play data event",
                "required": True,
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {
                                "action": {
                                    "type": "string",
                                    "enum": ["started", "ended", "paused", "heartbeat"],
                                },
                                "resource_type": {
                                    "type": "string",
                                    "enum": ["episode", "clip"],
                                },
                                "play_mode": {"type": "string", "enum": ["live"]},
                                "pid": {"type": "string", "example": "b08vxv2w"},
                                "version_pid": {
                                    "type": "string",
                                    "example": "b08vxtj4",
                                },
                                "elapsed_time": {"type": "integer", "example": 80},
                            },
                            "required": [
                                "action",
                                "resource_type",
                                "pid",
                                "version_pid",
                                "elapsed_time",
                            ],
                        }
                    }
                },
            },
            "tags": ["Personalised Programmes"],
            "description": "Accepts the play data & start processing write action to UAS <span>🎶</span> Pendulum\n",
            "responses": {
                "202": {"$ref": "#/components/responses/TextResponse"},
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/plays/playable": {
        "get": {
            "summary": "List of played programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "provides list of play history in playable items for a user <span>🎶</span> Oasis\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/favourites/playable": {
        "get": {
            "summary": "List of favourite programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns list of personalised programmes favourited by user <span>🎶</span> Oasis\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/follows": {
        "get": {
            "summary": "List of favourite programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
                {
                    "name": "sort",
                    "in": "query",
                    "description": "Sort by provided query. E.g. 'title' sorts in ascending order",
                    "schema": {"type": "string", "enum": ["title"]},
                    "required": False,
                },
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns list of personalised programmes followed by user <span>🎶</span> Oasis\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/follows/playable": {
        "get": {
            "summary": "Programmes from followed brands & series",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns list of latest personalised playable programmes from followed brands and series <span>🎶</span> Oasis\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/recommendations/playable": {
        "get": {
            "summary": "List of recommended programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/X-Experiments"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Recommended Programmes from the Audience Platforms' Recommendations Chassis <span>🎶</span> AC/DC\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/recommendations/baseline/playable": {
        "get": {
            "summary": "List of random recommended programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Alternative and experimental Recommended Programmes from the Audience Platforms' Recomendations Service\n<span>🎶</span> AC/DC returning a random set of programmes\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/recommendations/{container-name}/playable": {
        "get": {
            "summary": "List of recommended music mix programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/activitiesEnabled"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/X-Experiments"},
                {"$ref": "#/components/parameters/container-name"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Recommended playable items within a given container provided by the Audience Platforms' Recommendations Chassis.\n\nThe default playable endpoint returns `for-you` items.\n\nExact supported feeds are based on configuration within ACDC, and so are subject to change.\n\nSupported values currently include\n<dl>\n  <dt>for-you</dt><dd>The default set of playable content, returned also when accessing the /v2/my/programmes/playable endpoint.</dd>\n  <dt>music-mixes</dt><dd>Recommended music mixes for you</dd>\n  <dt>thought-provoking</dt><dd>Recommended content in the thought provoking container for you</dd>\n  <dt>gripping-stories</dt><dd>Recommended content in the gripping stories container for you</dd>\n</dl>\n<span>🎶</span> AC/DC returning a set of playable items that are within the specified named container\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/search/container": {
        "get": {
            "summary": "Search Personalised Container Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Provides personalised search keywords results as list of container items <span>🔎</span> The Seekers <span>🔎</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/search/playable": {
        "get": {
            "summary": "Search Personalised Playable Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/q"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Provides personalised search keywords results as list of playable items <span>🔎</span> The Seekers <span>🔎</span>\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsResponse"
                            }
                        }
                    },
                },
                "400": {"$ref": "#/components/responses/BadRequest"},
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/playqueue/{pid}": {
        "get": {
            "summary": "Play Queue",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/context"},
                {"$ref": "#/components/parameters/play_context"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "provides the list of playable items as play queue based on the programme id <span>🎶</span> Boyzone\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/playable": {
        "get": {
            "summary": "Playable Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/network"},
                {"$ref": "#/components/parameters/networkUrlKey"},
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/allCategories"},
                {"$ref": "#/components/parameters/parent"},
                {"$ref": "#/components/parameters/container"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
                {
                    "name": "type",
                    "in": "query",
                    "description": "Filter by programme type. Accepts comma separated values",
                    "schema": {"type": "string", "enum": ["episode", "clip"]},
                    "required": False,
                },
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Provides a paginated list of personalised playable programmes (episodes and clips).\nAccepts various filters and sorting methods. When sorting by popularity, this parameter only works with the category filter<span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/{pid}/playable": {
        "get": {
            "summary": "Single Playable Programme By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns personalised single playable item by a programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experiments/context": {
        "get": {
            "summary": "Experiment configurations",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/experiment-scope"},
                {"$ref": "#/components/parameters/experiment-platform"},
            ],
            "tags": ["Experiments"],
            "description": "Experiment configurations and datafile with optional platform and scope filters. <span>🎶</span> Chemical Brothers\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {"$ref": "#/components/schemas/ContextResponse"}
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/tagged/{mood}/playable": {
        "get": {
            "summary": "List of playable music mixes for mood",
            "parameters": [
                {"$ref": "#/components/parameters/experience"},
                {
                    "name": "mood",
                    "in": "path",
                    "description": "A mood representing a collection of playable items, some examples are chill, feel_good and focus.",
                    "schema": {"type": "string"},
                    "required": True,
                },
            ],
            "tags": ["Mixes"],
            "description": "For a given mood, provides a list of items curated by an external team to match that mood. <span>🎶</span> Tyga\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/promos/single-item": {
        "get": {
            "summary": "List of Single Item Promos",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Single Item Promo"],
            "description": "Provides a list of the active single item promos <span>🌟</span> rms-promo-service\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/SingleItemPromosResponse"
                            }
                        }
                    },
                },
                "502": {"$ref": "#/components/responses/GatewayTimeout"},
                "504": {"$ref": "#/components/responses/BadGateway"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/promos/single-item": {
        "get": {
            "summary": "List of Personalised Single Item Promos",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/Authorization"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Single Item Promo"],
            "description": "Provides a personalised list of the active single item promos <span>🌟</span> rms-promo-service\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/SingleItemPromosResponse"
                            }
                        }
                    },
                },
                "502": {"$ref": "#/components/responses/GatewayTimeout"},
                "504": {"$ref": "#/components/responses/BadGateway"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/experience-name": {
        "get": {
            "summary": "Experience Name",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/X-forwarded-for"},
            ],
            "tags": ["Experience Name"],
            "description": "An experience name depending on the IP address\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ExperienceNameResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/{pids}": {
        "get": {
            "summary": "Batch Programmes By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns requested programme items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ProgrammesResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/playable/{pids}": {
        "get": {
            "summary": "Batch Programme Playables By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns requested playable items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/tleo/playable": {
        "get": {
            "summary": "Playable Programmes By Tleo",
            "parameters": [
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/allCategories"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Programmes"],
            "description": "Provides a paginated list of playable programmes by tleo id (episodes and clips). <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/random/playable": {
        "get": {
            "summary": "Random Playable Programmes",
            "parameters": [
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
            ],
            "tags": ["Programmes"],
            "description": "Provides a paginated list of random playable programmes (episodes and clips). <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/playable/next/{pids}": {
        "get": {
            "summary": "Batch Playables And Their Next Playable By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns requested playable items and their playable item to follow by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/container/{pids}": {
        "get": {
            "summary": "Batch Programme Containers By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns requested container items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/programmes/{pid}/container": {
        "get": {
            "summary": "Single Playable Programme By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/experience"},
            ],
            "tags": ["Programmes"],
            "description": "Returns single container item by a programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/playable/{pids}": {
        "get": {
            "summary": "Batch Programme Playables By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns requested personalised playable items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/tleo/playable": {
        "get": {
            "summary": "Playable Programmes By Tleo",
            "parameters": [
                {"$ref": "#/components/parameters/category"},
                {"$ref": "#/components/parameters/allCategories"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/sort"},
                {"$ref": "#/components/parameters/offset"},
                {"$ref": "#/components/parameters/limit"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Programmes"],
            "description": "Provides a paginated list of playable programmes by tleo id (episodes and clips). <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/playable/next/{pids}": {
        "get": {
            "summary": "Batch Playables And Their Next Playable By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns requested personalised playable items and their playable item to follow by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/PlayableItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/container/{pids}": {
        "get": {
            "summary": "Batch Programme Containers By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pids"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns requested personalised container items by programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
    "/v2/my/programmes/{pid}/container": {
        "get": {
            "summary": "Single Playable Programme By Pid",
            "parameters": [
                {"$ref": "#/components/parameters/X-API-Key"},
                {"$ref": "#/components/parameters/pid"},
                {"$ref": "#/components/parameters/experience"},
                {"$ref": "#/components/parameters/Authorization"},
            ],
            "tags": ["Personalised Programmes"],
            "description": "Returns personalised single container item by a programme id <span>🎶</span> Beatles\n",
            "responses": {
                "200": {
                    "description": "OK",
                    "content": {
                        "application/json": {
                            "schema": {
                                "$ref": "#/components/schemas/ContainerItemsPaginatedResponse"
                            }
                        }
                    },
                },
                "401": {"$ref": "#/components/responses/Unauthorized"},
                "404": {"$ref": "#/components/responses/Notfound"},
                "default": {"$ref": "#/components/responses/InternalServiceError"},
            },
        }
    },
}
