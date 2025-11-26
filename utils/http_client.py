import httpx
import os
import logging

logger = logging.getLogger("progress-service")

USER_SERVICE_URL = os.getenv("USER_SERVICE_URL", "http://localhost:3001")
SCHEDULE_SERVICE_URL = os.getenv("SCHEDULE_SERVICE_URL", "http://localhost:8003")
TRAINING_SERVICE_URL = os.getenv("TRAINING_SERVICE_URL", "http://localhost:3002")


async def validate_user(user_id: str, token: str):
    """Validate if a user exists"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{USER_SERVICE_URL}/api/users/{user_id}",
                headers={"Authorization": token if token.startswith("Bearer ") else f"Bearer {token}"},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            raise ValueError(f"User {user_id} not found")
        raise
    except (httpx.ConnectError, httpx.TimeoutException):
        logger.error("User service unavailable")
        raise ConnectionError("User service unavailable")


async def get_booking_details(booking_id: str, token: str):
    """Get booking details from Schedule Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{SCHEDULE_SERVICE_URL}/api/bookings/{booking_id}",
                headers={"Authorization": token if token.startswith("Bearer ") else f"Bearer {token}"},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching booking details: {e}")
        return None


async def get_program_details(program_id: str, token: str):
    """Get program details from Training Service"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{TRAINING_SERVICE_URL}/api/programs/{program_id}",
                headers={"Authorization": token if token.startswith("Bearer ") else f"Bearer {token}"},
                timeout=5.0
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"Error fetching program details: {e}")
        return None
