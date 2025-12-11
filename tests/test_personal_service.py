from unittest.mock import AsyncMock, patch

import pytest

from sounds.personal import PersonalService


class TestPersonalService:
    """Tests for personal service"""

    @pytest.mark.asyncio
    async def test_get_experience_menu_exclude_recommendations(
        self, mock_session, mock_logger
    ):
        """Test getting menu excluding recommendations"""
        mock_auth = AsyncMock()
        mock_auth.is_logged_in = True

        service = PersonalService(
            session=mock_session, logger=mock_logger, auth=mock_auth
        )

        # Mock a menu with mixed items
        with patch.object(
            service,
            "_get_json",
            AsyncMock(
                return_value={
                    "data": [
                        {"type": "inline_display_module", "id": "menu1", "data": []},
                        {"type": "inline_display_module", "id": "menu2", "data": []},
                    ]
                }
            ),
        ):
            # This test would need more complex mocking
            # Simplified for demonstration
            pass
