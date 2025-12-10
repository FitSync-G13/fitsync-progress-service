"""
Pytest configuration and fixtures for progress-service tests.
"""
import pytest
from datetime import date, time, datetime
from unittest.mock import AsyncMock, MagicMock
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def mock_db_pool():
    """Mock database pool for testing."""
    pool = AsyncMock()
    conn = AsyncMock()
    pool.acquire.return_value.__aenter__.return_value = conn
    pool.acquire.return_value.__aexit__.return_value = None
    return pool, conn


@pytest.fixture
def mock_redis():
    """Mock Redis client for testing."""
    redis = AsyncMock()
    redis.publish = AsyncMock(return_value=1)
    return redis


@pytest.fixture
def sample_user_client():
    """Sample client user payload from JWT."""
    return {
        "id": "client-123-uuid",
        "email": "client@example.com",
        "role": "client",
        "gym_id": "gym-123-uuid"
    }


@pytest.fixture
def sample_user_trainer():
    """Sample trainer user payload from JWT."""
    return {
        "id": "trainer-456-uuid",
        "email": "trainer@example.com",
        "role": "trainer",
        "gym_id": "gym-123-uuid"
    }


@pytest.fixture
def sample_user_admin():
    """Sample admin user payload from JWT."""
    return {
        "id": "admin-789-uuid",
        "email": "admin@example.com",
        "role": "admin",
        "gym_id": None
    }


@pytest.fixture
def sample_body_metrics_data():
    """Sample body metrics creation data."""
    return {
        "recorded_date": date(2025, 1, 15),
        "weight_kg": 75.5,
        "height_cm": 175.0,
        "body_fat_percentage": 18.5,
        "measurements": {"chest": 100, "waist": 85, "hips": 95},
        "notes": "Weekly measurement"
    }


@pytest.fixture
def sample_body_metrics_record():
    """Sample body metrics database record."""
    return {
        "id": "metrics-001-uuid",
        "client_id": "client-123-uuid",
        "recorded_date": date(2025, 1, 15),
        "weight_kg": 75.5,
        "height_cm": 175.0,
        "bmi": 24.65,
        "body_fat_percentage": 18.5,
        "measurements": '{"chest": 100, "waist": 85, "hips": 95}',
        "notes": "Weekly measurement",
        "recorded_by": "client-123-uuid",
        "created_at": datetime(2025, 1, 15, 10, 0, 0)
    }


@pytest.fixture
def sample_workout_log_data():
    """Sample workout log creation data."""
    return {
        "booking_id": "booking-001-uuid",
        "workout_date": date(2025, 1, 15),
        "exercises_completed": [
            {"name": "Bench Press", "sets": 3, "reps": 10, "weight_kg": 60},
            {"name": "Squats", "sets": 3, "reps": 12, "weight_kg": 80}
        ],
        "total_duration_minutes": 60,
        "calories_burned": 450,
        "trainer_notes": "Good form on squats",
        "client_notes": "Felt strong today",
        "mood_rating": 4
    }


@pytest.fixture
def sample_workout_log_record():
    """Sample workout log database record."""
    return {
        "id": "workout-001-uuid",
        "client_id": "client-123-uuid",
        "booking_id": "booking-001-uuid",
        "workout_date": date(2025, 1, 15),
        "exercises_completed": '[{"name": "Bench Press", "sets": 3, "reps": 10}]',
        "total_duration_minutes": 60,
        "calories_burned": 450,
        "trainer_notes": "Good session",
        "client_notes": "Felt good",
        "mood_rating": 4,
        "created_at": datetime(2025, 1, 15, 12, 0, 0)
    }


@pytest.fixture
def sample_health_record_data():
    """Sample health record creation data."""
    return {
        "record_type": "injury",
        "description": "Lower back strain",
        "start_date": date(2025, 1, 10),
        "end_date": None,
        "severity": "medium",
        "notes": "Avoid heavy deadlifts"
    }


@pytest.fixture
def sample_health_record():
    """Sample health record database record."""
    return {
        "id": "health-001-uuid",
        "client_id": "client-123-uuid",
        "record_type": "injury",
        "description": "Lower back strain",
        "start_date": date(2025, 1, 10),
        "end_date": None,
        "severity": "medium",
        "is_active": True,
        "notes": "Avoid heavy deadlifts",
        "created_at": datetime(2025, 1, 10, 9, 0, 0)
    }


@pytest.fixture
def sample_achievement_record():
    """Sample achievement database record."""
    return {
        "id": "achievement-001-uuid",
        "client_id": "client-123-uuid",
        "achievement_type": "attendance_streak",
        "title": "7-Day Streak",
        "description": "Completed 7 consecutive days of training",
        "achieved_at": datetime(2025, 1, 15, 10, 0, 0),
        "badge_icon": "streak_7.png"
    }


@pytest.fixture
def sample_booking_completed_event():
    """Sample booking.completed event data."""
    return {
        "event": "booking.completed",
        "timestamp": "2025-01-15T12:00:00",
        "correlation_id": "corr-123",
        "data": {
            "booking_id": "booking-001-uuid",
            "client_id": "client-123-uuid",
            "trainer_id": "trainer-456-uuid",
            "workout_date": "2025-01-15",
            "duration_minutes": 60,
            "trainer_notes": "Great session"
        }
    }


@pytest.fixture
def sample_program_completed_event():
    """Sample program.completed event data."""
    return {
        "event": "program.completed",
        "timestamp": "2025-01-15T12:00:00",
        "correlation_id": "corr-456",
        "data": {
            "program_id": "program-001-uuid",
            "client_id": "client-123-uuid",
            "program_name": "12-Week Strength Program",
            "completed_at": "2025-01-15T12:00:00"
        }
    }
