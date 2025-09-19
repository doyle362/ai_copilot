import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException
from services.analyst.analyst.deps.auth import get_current_user, require_zone_access, require_role
from services.analyst.analyst.config import settings


class TestAuth:
    """Test authentication and authorization functionality."""

    @pytest.mark.asyncio
    async def test_get_current_user_valid_token(self):
        """Test successful JWT token validation."""
        from fastapi.security import HTTPAuthorizationCredentials

        # Mock JWT decode to return valid payload
        mock_payload = {
            "sub": "test-user",
            "org_id": "org-test",
            "roles": ["viewer", "approver"],
            "zone_ids": ["z-110", "z-221"],
            "iss": "test.lvlparking.com",
            "exp": 9999999999
        }

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-jwt-token"
        )

        with patch('services.analyst.analyst.deps.auth.jwt.decode', return_value=mock_payload):
            user_context = await get_current_user(credentials)

            assert user_context.sub == "test-user"
            assert user_context.org_id == "org-test"
            assert "viewer" in user_context.roles
            assert "approver" in user_context.roles
            assert "z-110" in user_context.zone_ids
            assert "z-221" in user_context.zone_ids

    @pytest.mark.asyncio
    async def test_get_current_user_invalid_token(self):
        """Test JWT token validation failure."""
        from fastapi.security import HTTPAuthorizationCredentials
        from jose import JWTError

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="invalid-jwt-token"
        )

        with patch('services.analyst.analyst.deps.auth.jwt.decode', side_effect=JWTError("Invalid token")):
            with pytest.raises(HTTPException) as exc_info:
                await get_current_user(credentials)

            assert exc_info.value.status_code == 401
            assert "Invalid authentication credentials" in str(exc_info.value.detail)

    def test_require_zone_access_valid(self, mock_user_context):
        """Test zone access check with valid zone."""
        from services.analyst.analyst.deps.auth import UserContext

        user = UserContext(**mock_user_context)
        checker = require_zone_access("z-110")

        # Should not raise exception for valid zone
        result = checker(user)
        assert result == user

    def test_require_zone_access_invalid(self, mock_user_context):
        """Test zone access check with invalid zone."""
        from services.analyst.analyst.deps.auth import UserContext

        user = UserContext(**mock_user_context)
        checker = require_zone_access("z-999")

        with pytest.raises(HTTPException) as exc_info:
            checker(user)

        assert exc_info.value.status_code == 403
        assert "Access denied to zone z-999" in str(exc_info.value.detail)

    def test_require_role_valid(self, mock_user_context):
        """Test role check with valid role."""
        from services.analyst.analyst.deps.auth import UserContext

        user = UserContext(**mock_user_context)
        checker = require_role("viewer")

        # Should not raise exception for valid role
        result = checker(user)
        assert result == user

    def test_require_role_invalid(self, mock_user_context):
        """Test role check with invalid role."""
        from services.analyst.analyst.deps.auth import UserContext

        user = UserContext(**mock_user_context)
        checker = require_role("admin")

        with pytest.raises(HTTPException) as exc_info:
            checker(user)

        assert exc_info.value.status_code == 403
        assert "Role admin required" in str(exc_info.value.detail)

    def test_user_context_validation(self):
        """Test UserContext model validation."""
        from services.analyst.analyst.deps.auth import UserContext

        # Valid context
        valid_data = {
            "sub": "test-user",
            "org_id": "org-test",
            "roles": ["viewer"],
            "zone_ids": ["z-110"],
            "iss": "test.lvlparking.com",
            "exp": 9999999999
        }

        user = UserContext(**valid_data)
        assert user.sub == "test-user"
        assert user.roles == ["viewer"]
        assert user.zone_ids == ["z-110"]

    @pytest.mark.asyncio
    async def test_get_current_user_does_not_touch_db(self):
        """get_current_user should not attempt database access in HS256 mode."""
        from fastapi.security import HTTPAuthorizationCredentials

        mock_payload = {
            "sub": "test-user",
            "org_id": "org-test",
            "roles": ["viewer"],
            "zone_ids": ["z-110"],
            "iss": "test.lvlparking.com",
            "exp": 9999999999
        }

        credentials = HTTPAuthorizationCredentials(
            scheme="Bearer",
            credentials="valid-jwt-token"
        )

        with patch('services.analyst.analyst.deps.auth.jwt.decode', return_value=mock_payload), \
             patch('services.analyst.analyst.deps.auth.get_db') as mock_get_db:
            user_context = await get_current_user(credentials)

            assert user_context.sub == "test-user"
            mock_get_db.assert_not_called()
