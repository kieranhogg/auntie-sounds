from unittest.mock import Mock

import pytest

from sounds.client import SoundsClient
from sounds.exceptions import InvalidFormatError
from sounds.schedule import ScheduleService

pytestmark = pytest.mark.anyio


class TestScheduleService:
    """Tests for schedule service"""

    async def test_get_schedule_invalid_date_format(self):
        """Test get_schedule with invalid date format"""
        service = ScheduleService(timezone="UTC", requests=Mock())

        with pytest.raises(InvalidFormatError):
            await service.get_schedule("bbc_radio_one", date="2025/01/15")

    async def test_get_schedule_valid_date_format(self, mock_session):
        """Test get_schedule with valid date format"""
        client = SoundsClient(mock_session=True)
        try:
            await client.schedules.get_schedule("bbc_radio_one", date="2025-01-15")
        except InvalidFormatError:
            pytest.fail("Valid date format raised InvalidFormatError")
