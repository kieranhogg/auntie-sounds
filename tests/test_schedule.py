import datetime
from datetime import datetime as dt
from unittest.mock import AsyncMock, Mock

import pytest

from sounds.exceptions import (
    APIResponseError,
    DateOutOfRangeError,
    InvalidFormatError,
)
from sounds.schedule import ScheduleService, _get_date_range

pytestmark = pytest.mark.anyio

TIMEZONE = datetime.UTC


class TestDateRangeHelper:
    """Tests for the date range helper used to get schedule date ranges."""

    def test_get_7_day_schedule(self):
        """Test a date range 7 days into the future."""
        date_range = _get_date_range(
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
            dt(day=7, month=1, year=2000, tzinfo=TIMEZONE),
        )
        assert len(date_range) == 7

    def test_get_1_day_schedule_or_catchup(self):
        """Test when start and end date are the same a range of 1 is still returned."""
        date_range = _get_date_range(
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
        )
        assert len(date_range) == 1

    def test_more_than_7_day_schedule(self):
        """Test a date range over 7 days into the future gets truncated to 7 days."""
        date_range = _get_date_range(
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
            dt(day=17, month=1, year=2000, tzinfo=TIMEZONE),
        )
        assert len(date_range) == 7

    def test_7_day_catchup(self):
        """Test a date range 7 days into the past."""
        date_range = _get_date_range(
            dt(day=7, month=1, year=2000, tzinfo=TIMEZONE),
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
        )
        assert len(date_range) == 7

    def test_30_day_catchup(self):
        """Test a date range 30 days into the past."""
        date_range = _get_date_range(
            dt(day=30, month=1, year=2000, tzinfo=TIMEZONE),
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
        )
        assert len(date_range) == 30

    def test_over_30_day_catchup(self):
        """Test a date range over 30 days into the past gets truncated to 30 days."""
        date_range = _get_date_range(
            dt(day=30, month=3, year=2000, tzinfo=TIMEZONE),
            dt(day=1, month=1, year=2000, tzinfo=TIMEZONE),
        )
        assert len(date_range) == 30


class TestScheduleService:
    """Tests for schedule service"""

    async def test_get_schedule_invalid_date_format(self):
        """Test get_schedule with invalid date format"""
        service = ScheduleService(timezone=datetime.UTC, requests=Mock())

        with pytest.raises(InvalidFormatError):
            await service.get_schedule("bbc_radio_one", date="2025/01/15")

    async def test_get_schedule_valid_date_format(
        self, mock_api, real_anonymous_client
    ):
        """Test get_schedule with valid date format"""
        try:
            await real_anonymous_client.schedules.get_schedule(
                "bbc_radio_one", date="2025-01-15"
            )
        except InvalidFormatError:
            pytest.fail("Valid date format raised InvalidFormatError")


class TestScheduleDateOutOfRange:
    async def test_out_of_range_date_raises_specific_error(self):
        requests = Mock()
        requests.get_json_response = AsyncMock(
            side_effect=APIResponseError(
                "Acceptable date must be between 30 days in the past and 7 days in the future",
                status_code=400,
            )
        )
        service = ScheduleService(timezone=datetime.UTC, requests=requests)

        with pytest.raises(DateOutOfRangeError) as exc:
            await service.get_schedule("bbc_radio_one", date="2000-01-01")

        assert "2000-01-01" in str(exc.value)
        assert exc.value.status_code == 400
        # Existing handlers for APIResponseError still catch it
        assert isinstance(exc.value, APIResponseError)

    async def test_other_api_errors_pass_through(self):
        requests = Mock()
        requests.get_json_response = AsyncMock(side_effect=APIResponseError("nope"))
        service = ScheduleService(timezone=datetime.UTC, requests=requests)

        with pytest.raises(APIResponseError) as exc:
            await service.get_schedule("bbc_radio_one", date="2000-01-01")

        assert type(exc.value) is APIResponseError
