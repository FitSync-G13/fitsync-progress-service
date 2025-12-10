"""
Unit tests for HTTP client utility functions.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import httpx
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestValidateUser:
    """Tests for validate_user function."""

    @pytest.mark.asyncio
    async def test_validate_user_success(self):
        """Test successful user validation."""
        from utils.http_client import validate_user
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "id": "user-123-uuid",
            "email": "test@example.com",
            "role": "client"
        }
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            result = await validate_user("user-123-uuid", "valid-token")
        
        assert result is not None
        assert result["id"] == "user-123-uuid"
        assert result["role"] == "client"

    @pytest.mark.asyncio
    async def test_validate_user_not_found(self):
        """Test validation when user is not found."""
        from utils.http_client import validate_user
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response
        )
        mock_response.raise_for_status = MagicMock(side_effect=http_error)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            with pytest.raises(ValueError) as exc_info:
                await validate_user("nonexistent-user", "valid-token")
            
            assert "not found" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_user_connection_error(self):
        """Test validation when user service is unavailable."""
        from utils.http_client import validate_user
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.ConnectError("Connection failed"))
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            with pytest.raises(ConnectionError) as exc_info:
                await validate_user("user-123", "token")
            
            assert "User service unavailable" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_validate_user_timeout(self):
        """Test validation when request times out."""
        from utils.http_client import validate_user
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            with pytest.raises(ConnectionError) as exc_info:
                await validate_user("user-123", "token")
            
            assert "User service unavailable" in str(exc_info.value)


class TestGetBookingDetails:
    """Tests for get_booking_details function."""

    @pytest.mark.asyncio
    async def test_get_booking_details_success(self):
        """Test successful booking details retrieval."""
        from utils.http_client import get_booking_details
        
        booking_data = {
            "id": "booking-123",
            "client_id": "client-456",
            "trainer_id": "trainer-789",
            "booking_date": "2025-01-15",
            "status": "completed"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = booking_data
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            result = await get_booking_details("booking-123", "valid-token")
        
        assert result is not None
        assert result["id"] == "booking-123"
        assert result["status"] == "completed"

    @pytest.mark.asyncio
    async def test_get_booking_details_not_found(self):
        """Test booking details when not found."""
        from utils.http_client import get_booking_details
        
        mock_response = MagicMock()
        mock_response.status_code = 404
        http_error = httpx.HTTPStatusError(
            "Not found",
            request=MagicMock(),
            response=mock_response
        )
        mock_response.raise_for_status = MagicMock(side_effect=http_error)
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            result = await get_booking_details("nonexistent-booking", "valid-token")
        
        # Returns None on error
        assert result is None

    @pytest.mark.asyncio
    async def test_get_booking_details_service_error(self):
        """Test booking details when service has error."""
        from utils.http_client import get_booking_details
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Service error"))
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            result = await get_booking_details("booking-123", "valid-token")
        
        # Returns None on any error
        assert result is None


class TestGetProgramDetails:
    """Tests for get_program_details function."""

    @pytest.mark.asyncio
    async def test_get_program_details_success(self):
        """Test successful program details retrieval."""
        from utils.http_client import get_program_details
        
        program_data = {
            "id": "program-123",
            "name": "12-Week Strength",
            "duration_weeks": 12,
            "client_id": "client-456"
        }
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = program_data
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            result = await get_program_details("program-123", "valid-token")
        
        assert result is not None
        assert result["id"] == "program-123"
        assert result["name"] == "12-Week Strength"

    @pytest.mark.asyncio
    async def test_get_program_details_error(self):
        """Test program details when error occurs."""
        from utils.http_client import get_program_details
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(side_effect=Exception("Service error"))
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            result = await get_program_details("program-123", "valid-token")
        
        # Returns None on error
        assert result is None


class TestAuthorizationHeaderHandling:
    """Tests for authorization header handling."""

    @pytest.mark.asyncio
    async def test_token_without_bearer_prefix(self):
        """Test that tokens without Bearer prefix get it added."""
        from utils.http_client import validate_user
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user-123"}
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            await validate_user("user-123", "my-token")
        
        # Check headers contain Bearer prefix
        call_kwargs = mock_instance.get.call_args
        auth_header = call_kwargs.kwargs["headers"]["Authorization"]
        assert auth_header == "Bearer my-token"

    @pytest.mark.asyncio
    async def test_token_with_bearer_prefix_not_doubled(self):
        """Test that tokens with Bearer prefix don't get doubled."""
        from utils.http_client import validate_user
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"id": "user-123"}
        mock_response.raise_for_status = MagicMock()
        
        with patch('httpx.AsyncClient') as mock_client:
            mock_instance = AsyncMock()
            mock_instance.get = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value = mock_instance
            mock_client.return_value.__aexit__.return_value = None
            
            await validate_user("user-123", "Bearer my-token")
        
        call_kwargs = mock_instance.get.call_args
        auth_header = call_kwargs.kwargs["headers"]["Authorization"]
        assert auth_header == "Bearer my-token"
        assert "Bearer Bearer" not in auth_header
