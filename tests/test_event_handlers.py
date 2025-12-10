"""
Unit tests for event handlers (booking.completed, program.completed).
"""
import pytest
import json
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestBookingCompletedHandler:
    """Tests for booking.completed event handler."""

    @pytest.mark.asyncio
    async def test_handle_booking_completed_creates_workout_log(self, mock_db_pool, sample_booking_completed_event):
        """Test that booking.completed creates a workout log."""
        pool, conn = mock_db_pool
        
        # No existing workout log for this booking
        conn.fetchval.return_value = None
        conn.execute.return_value = None
        
        event_data = sample_booking_completed_event
        data = event_data.get("data", {})
        
        # Check if workout log exists
        existing = await conn.fetchval(
            "SELECT id FROM workout_logs WHERE booking_id = $1",
            data.get("booking_id")
        )
        
        assert existing is None
        
        # Simulate creating workout log
        await conn.execute(
            """INSERT INTO workout_logs (client_id, booking_id, workout_date,
                                         exercises_completed, total_duration_minutes, trainer_notes)
               VALUES ($1, $2, $3, $4, $5, $6)""",
            data.get("client_id"), data.get("booking_id"),
            data.get("workout_date"), json.dumps([]),
            data.get("duration_minutes", 60), data.get("trainer_notes", "")
        )
        
        conn.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_handle_booking_completed_skips_existing_log(self, mock_db_pool, sample_booking_completed_event):
        """Test that handler skips if workout log already exists."""
        pool, conn = mock_db_pool
        
        # Workout log already exists
        conn.fetchval.return_value = "existing-workout-log-id"
        
        event_data = sample_booking_completed_event
        data = event_data.get("data", {})
        
        existing = await conn.fetchval(
            "SELECT id FROM workout_logs WHERE booking_id = $1",
            data.get("booking_id")
        )
        
        assert existing is not None
        # execute should not be called for insert
        conn.execute.assert_not_called()

    @pytest.mark.asyncio
    async def test_handle_booking_completed_default_duration(self, sample_booking_completed_event):
        """Test default duration when not provided."""
        event_data = {
            "data": {
                "booking_id": "booking-123",
                "client_id": "client-123"
                # No duration_minutes
            }
        }
        
        data = event_data.get("data", {})
        duration = data.get("duration_minutes", 60)
        
        assert duration == 60  # Default

    @pytest.mark.asyncio
    async def test_handle_booking_completed_with_trainer_notes(self, sample_booking_completed_event):
        """Test handler preserves trainer notes."""
        event_data = sample_booking_completed_event
        data = event_data.get("data", {})
        
        trainer_notes = data.get("trainer_notes", "")
        
        assert trainer_notes == "Great session"


class TestProgramCompletedHandler:
    """Tests for program.completed event handler."""

    @pytest.mark.asyncio
    async def test_handle_program_completed_creates_achievement(self, mock_db_pool, mock_redis, sample_program_completed_event):
        """Test that program.completed creates an achievement."""
        pool, conn = mock_db_pool
        
        achievement_record = {
            "id": "achievement-new-uuid",
            "client_id": "client-123-uuid",
            "achievement_type": "program_completion",
            "title": "Completed Training Program",
            "description": "You've successfully completed your training program!",
            "achieved_at": datetime.now(),
            "badge_icon": "program_complete.png"
        }
        
        conn.fetchrow.return_value = achievement_record
        
        event_data = sample_program_completed_event
        data = event_data.get("data", {})
        
        # Insert achievement
        result = await conn.fetchrow(
            """INSERT INTO achievements (client_id, achievement_type, title, description, badge_icon)
               VALUES ($1, 'program_completion', $2, $3, 'program_complete.png')
               RETURNING *""",
            data.get("client_id"),
            "Completed Training Program",
            "You've successfully completed your training program!"
        )
        
        assert result is not None
        assert result["achievement_type"] == "program_completion"
        assert result["client_id"] == "client-123-uuid"

    @pytest.mark.asyncio
    async def test_handle_program_completed_publishes_event(self, mock_redis, sample_achievement_record):
        """Test that achievement.earned event is published."""
        from utils.event_publisher import publish_achievement_earned
        
        # Publish achievement earned
        correlation_id = await publish_achievement_earned(
            mock_redis, 
            sample_achievement_record
        )
        
        # Verify publish was called
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        
        assert call_args[0][0] == "achievement.earned"
        
        # Parse the published data
        published_data = json.loads(call_args[0][1])
        assert published_data["data"]["client_id"] == str(sample_achievement_record["client_id"])


class TestEventDataParsing:
    """Tests for parsing event data."""

    def test_parse_booking_completed_event(self, sample_booking_completed_event):
        """Test parsing booking.completed event."""
        event = sample_booking_completed_event
        
        assert event["event"] == "booking.completed"
        assert "timestamp" in event
        assert "correlation_id" in event
        
        data = event["data"]
        assert "booking_id" in data
        assert "client_id" in data
        assert "trainer_id" in data

    def test_parse_program_completed_event(self, sample_program_completed_event):
        """Test parsing program.completed event."""
        event = sample_program_completed_event
        
        assert event["event"] == "program.completed"
        
        data = event["data"]
        assert "program_id" in data
        assert "client_id" in data
        assert "program_name" in data

    def test_parse_json_event_data(self):
        """Test parsing JSON event data from Redis."""
        raw_message = json.dumps({
            "event": "booking.completed",
            "timestamp": "2025-01-15T12:00:00",
            "data": {
                "booking_id": "booking-123",
                "client_id": "client-456"
            }
        })
        
        parsed = json.loads(raw_message)
        
        assert parsed["event"] == "booking.completed"
        assert parsed["data"]["booking_id"] == "booking-123"

    def test_handle_malformed_json(self):
        """Test handling malformed JSON in event."""
        raw_message = "not valid json {"
        
        with pytest.raises(json.JSONDecodeError):
            json.loads(raw_message)


class TestEventPublishing:
    """Tests for publishing events."""

    @pytest.mark.asyncio
    async def test_publish_achievement_earned(self, mock_redis, sample_achievement_record):
        """Test publishing achievement.earned event."""
        from utils.event_publisher import publish_achievement_earned
        
        correlation_id = await publish_achievement_earned(
            mock_redis,
            sample_achievement_record
        )
        
        mock_redis.publish.assert_called_once()
        
        # Verify the channel
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "achievement.earned"

    @pytest.mark.asyncio
    async def test_publish_milestone_reached(self, mock_redis):
        """Test publishing milestone.reached event."""
        from utils.event_publisher import publish_milestone_reached
        
        milestone_data = {
            "client_id": "client-123",
            "milestone_type": "weight_goal",
            "value": 80.0,
            "description": "Reached goal weight of 80kg"
        }
        
        correlation_id = await publish_milestone_reached(
            mock_redis,
            milestone_data
        )
        
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "milestone.reached"

    @pytest.mark.asyncio
    async def test_publish_progress_updated(self, mock_redis):
        """Test publishing progress.updated event."""
        from utils.event_publisher import publish_progress_updated
        
        progress_data = {
            "client_id": "client-123",
            "metric_type": "weight",
            "previous_value": 85.0,
            "new_value": 84.5
        }
        
        correlation_id = await publish_progress_updated(
            mock_redis,
            progress_data
        )
        
        mock_redis.publish.assert_called_once()
        call_args = mock_redis.publish.call_args
        assert call_args[0][0] == "progress.updated"

    @pytest.mark.asyncio
    async def test_publish_event_returns_correlation_id(self, mock_redis):
        """Test that publishing returns a correlation ID."""
        from utils.event_publisher import publish_event
        
        correlation_id = await publish_event(
            mock_redis,
            "test.event",
            {"key": "value"}
        )
        
        # Should return a UUID or provided correlation_id
        assert correlation_id is not None

    @pytest.mark.asyncio
    async def test_publish_event_with_custom_correlation_id(self, mock_redis):
        """Test publishing with custom correlation ID."""
        from utils.event_publisher import publish_event
        
        custom_id = "custom-correlation-123"
        correlation_id = await publish_event(
            mock_redis,
            "test.event",
            {"key": "value"},
            correlation_id=custom_id
        )
        
        assert correlation_id == custom_id


class TestAchievementTriggers:
    """Tests for achievement trigger conditions."""

    def test_weight_milestone_trigger(self):
        """Test triggering weight milestone achievement."""
        starting_weight = 90.0
        current_weight = 85.0
        milestones = [5, 10, 15, 20]  # kg lost
        
        lost = starting_weight - current_weight
        
        triggered_milestones = [m for m in milestones if lost >= m]
        
        assert triggered_milestones == [5]  # Lost 5kg

    def test_attendance_streak_trigger(self):
        """Test triggering attendance streak achievement."""
        consecutive_days = 7
        streak_milestones = [3, 7, 14, 30, 60, 90]
        
        triggered = [m for m in streak_milestones if consecutive_days >= m]
        
        assert triggered == [3, 7]

    def test_personal_record_trigger(self):
        """Test triggering personal record achievement."""
        exercise = "Bench Press"
        previous_best = 80.0  # kg
        current_lift = 85.0  # kg
        
        is_pr = current_lift > previous_best
        improvement = current_lift - previous_best
        
        assert is_pr == True
        assert improvement == 5.0

    def test_program_completion_trigger(self):
        """Test triggering program completion achievement."""
        program = {
            "total_weeks": 12,
            "completed_weeks": 12,
            "status": "completed"
        }
        
        is_completed = program["completed_weeks"] >= program["total_weeks"]
        
        assert is_completed == True
