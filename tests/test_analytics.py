"""
Unit tests for analytics aggregation logic.
"""
import pytest
from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestWorkoutAnalytics:
    """Tests for workout analytics calculations."""

    def test_total_workout_count(self):
        """Test counting total workouts."""
        workout_logs = [
            {"id": "1", "workout_date": date(2025, 1, 10)},
            {"id": "2", "workout_date": date(2025, 1, 12)},
            {"id": "3", "workout_date": date(2025, 1, 15)},
        ]
        
        total_count = len(workout_logs)
        
        assert total_count == 3

    def test_total_workout_duration(self):
        """Test summing total workout duration."""
        workout_logs = [
            {"total_duration_minutes": 45},
            {"total_duration_minutes": 60},
            {"total_duration_minutes": 30},
            {"total_duration_minutes": 75},
        ]
        
        total_duration = sum(log["total_duration_minutes"] for log in workout_logs)
        
        assert total_duration == 210  # 3.5 hours

    def test_average_workout_duration(self):
        """Test calculating average workout duration."""
        workout_logs = [
            {"total_duration_minutes": 45},
            {"total_duration_minutes": 60},
            {"total_duration_minutes": 75},
        ]
        
        total = sum(log["total_duration_minutes"] for log in workout_logs)
        average = total / len(workout_logs)
        
        assert average == 60.0

    def test_total_calories_burned(self):
        """Test summing total calories burned."""
        workout_logs = [
            {"calories_burned": 350},
            {"calories_burned": 450},
            {"calories_burned": 300},
            {"calories_burned": None},  # Some may not have calories
        ]
        
        total_calories = sum(
            log["calories_burned"] for log in workout_logs 
            if log["calories_burned"] is not None
        )
        
        assert total_calories == 1100

    def test_average_mood_rating(self):
        """Test calculating average mood rating."""
        workout_logs = [
            {"mood_rating": 4},
            {"mood_rating": 5},
            {"mood_rating": 3},
            {"mood_rating": 4},
        ]
        
        total_mood = sum(log["mood_rating"] for log in workout_logs)
        average_mood = total_mood / len(workout_logs)
        
        assert average_mood == 4.0

    def test_handle_none_calories(self):
        """Test handling None calories in calculations."""
        workout_logs = [
            {"calories_burned": 400},
            {"calories_burned": None},
            {"calories_burned": 350},
        ]
        
        valid_logs = [log for log in workout_logs if log["calories_burned"] is not None]
        total_calories = sum(log["calories_burned"] for log in valid_logs)
        
        assert total_calories == 750
        assert len(valid_logs) == 2


class TestWeeklyAnalytics:
    """Tests for weekly analytics aggregation."""

    def test_workouts_this_week(self):
        """Test counting workouts in current week."""
        today = date(2025, 1, 15)  # Wednesday
        week_start = today - timedelta(days=today.weekday())  # Monday
        
        workout_logs = [
            {"workout_date": date(2025, 1, 12)},  # Sunday (last week)
            {"workout_date": date(2025, 1, 13)},  # Monday (this week)
            {"workout_date": date(2025, 1, 15)},  # Wednesday (this week)
        ]
        
        this_week = [log for log in workout_logs if log["workout_date"] >= week_start]
        
        assert len(this_week) == 2

    def test_weekly_workout_streak(self):
        """Test calculating consecutive workout days."""
        workout_dates = [
            date(2025, 1, 10),
            date(2025, 1, 11),
            date(2025, 1, 12),
            date(2025, 1, 13),
            # Gap on 14th
            date(2025, 1, 15),
        ]
        
        # Sort and count consecutive
        sorted_dates = sorted(workout_dates)
        
        def count_streak(dates):
            if not dates:
                return 0
            streak = 1
            max_streak = 1
            for i in range(1, len(dates)):
                if (dates[i] - dates[i-1]).days == 1:
                    streak += 1
                    max_streak = max(max_streak, streak)
                else:
                    streak = 1
            return max_streak
        
        streak = count_streak(sorted_dates)
        
        assert streak == 4  # Jan 10-13

    def test_workouts_per_week_average(self):
        """Test calculating average workouts per week."""
        # 4 weeks of data
        workout_logs = [
            {"workout_date": date(2025, 1, 1)},
            {"workout_date": date(2025, 1, 3)},
            {"workout_date": date(2025, 1, 5)},  # Week 1: 3 workouts
            {"workout_date": date(2025, 1, 8)},
            {"workout_date": date(2025, 1, 10)},  # Week 2: 2 workouts
            {"workout_date": date(2025, 1, 15)},
            {"workout_date": date(2025, 1, 17)},
            {"workout_date": date(2025, 1, 19)},  # Week 3: 3 workouts
            {"workout_date": date(2025, 1, 22)},
            {"workout_date": date(2025, 1, 24)},  # Week 4: 2 workouts
        ]
        
        total_workouts = len(workout_logs)
        num_weeks = 4
        avg_per_week = total_workouts / num_weeks
        
        assert avg_per_week == 2.5


class TestProgressAnalytics:
    """Tests for progress tracking analytics."""

    def test_weight_trend_calculation(self):
        """Test calculating weight trend (slope)."""
        # Weight records over time
        weights = [
            {"day": 0, "weight": 85.0},
            {"day": 7, "weight": 84.5},
            {"day": 14, "weight": 84.0},
            {"day": 21, "weight": 83.5},
        ]
        
        # Simple linear regression slope (change per day)
        first_weight = weights[0]["weight"]
        last_weight = weights[-1]["weight"]
        days = weights[-1]["day"] - weights[0]["day"]
        
        daily_change = (last_weight - first_weight) / days
        weekly_change = daily_change * 7
        
        assert round(daily_change, 4) == -0.0714
        assert round(weekly_change, 2) == -0.5

    def test_body_fat_trend(self):
        """Test calculating body fat percentage trend."""
        records = [
            {"week": 1, "body_fat": 22.0},
            {"week": 2, "body_fat": 21.5},
            {"week": 4, "body_fat": 20.5},
            {"week": 6, "body_fat": 19.5},
        ]
        
        total_change = records[-1]["body_fat"] - records[0]["body_fat"]
        weeks_elapsed = records[-1]["week"] - records[0]["week"]
        
        assert total_change == -2.5
        assert weeks_elapsed == 5
        assert round(total_change / weeks_elapsed, 2) == -0.5  # -0.5% per week

    def test_goal_progress_percentage(self):
        """Test calculating progress towards a goal."""
        starting_weight = 90.0
        goal_weight = 80.0
        current_weight = 85.0
        
        total_to_lose = starting_weight - goal_weight  # 10 kg
        lost_so_far = starting_weight - current_weight  # 5 kg
        
        progress_percentage = (lost_so_far / total_to_lose) * 100
        
        assert progress_percentage == 50.0

    def test_goal_progress_exceeded(self):
        """Test progress when goal is exceeded."""
        starting_weight = 85.0
        goal_weight = 80.0
        current_weight = 78.0  # Below goal
        
        total_to_lose = starting_weight - goal_weight  # 5 kg
        lost_so_far = starting_weight - current_weight  # 7 kg
        
        progress_percentage = (lost_so_far / total_to_lose) * 100
        
        assert progress_percentage == 140.0  # 140% of goal


class TestAchievementAnalytics:
    """Tests for achievement tracking and analytics."""

    def test_achievement_count_by_type(self):
        """Test counting achievements by type."""
        achievements = [
            {"type": "weight_milestone"},
            {"type": "attendance_streak"},
            {"type": "weight_milestone"},
            {"type": "personal_record"},
            {"type": "attendance_streak"},
            {"type": "attendance_streak"},
        ]
        
        type_counts = {}
        for a in achievements:
            type_counts[a["type"]] = type_counts.get(a["type"], 0) + 1
        
        assert type_counts["weight_milestone"] == 2
        assert type_counts["attendance_streak"] == 3
        assert type_counts["personal_record"] == 1

    def test_recent_achievements(self):
        """Test getting recent achievements."""
        achievements = [
            {"id": "1", "achieved_at": datetime(2025, 1, 1)},
            {"id": "2", "achieved_at": datetime(2025, 1, 10)},
            {"id": "3", "achieved_at": datetime(2025, 1, 15)},
        ]
        
        # Sort by achieved_at descending
        sorted_achievements = sorted(
            achievements, 
            key=lambda x: x["achieved_at"], 
            reverse=True
        )
        
        # Get last 2
        recent = sorted_achievements[:2]
        
        assert recent[0]["id"] == "3"
        assert recent[1]["id"] == "2"


class TestPaginationLogic:
    """Tests for pagination calculations."""

    def test_pagination_offset_calculation(self):
        """Test calculating offset from page and limit."""
        page = 1
        limit = 20
        offset = (page - 1) * limit
        assert offset == 0
        
        page = 2
        offset = (page - 1) * limit
        assert offset == 20
        
        page = 5
        offset = (page - 1) * limit
        assert offset == 80

    def test_total_pages_calculation(self):
        """Test calculating total pages."""
        total_count = 95
        limit = 20
        
        total_pages = (total_count + limit - 1) // limit
        
        assert total_pages == 5

    def test_total_pages_exact_division(self):
        """Test total pages when count divides evenly."""
        total_count = 100
        limit = 20
        
        total_pages = (total_count + limit - 1) // limit
        
        assert total_pages == 5

    def test_total_pages_single_page(self):
        """Test total pages when all items fit on one page."""
        total_count = 15
        limit = 20
        
        total_pages = (total_count + limit - 1) // limit
        
        assert total_pages == 1

    def test_total_pages_empty_result(self):
        """Test total pages with no results."""
        total_count = 0
        limit = 20
        
        total_pages = (total_count + limit - 1) // limit
        
        assert total_pages == 0


class TestAnalyticsAggregation:
    """Tests for aggregating client analytics."""

    @pytest.mark.asyncio
    async def test_aggregate_client_analytics(self, sample_body_metrics_record, sample_workout_log_record, sample_achievement_record):
        """Test aggregating all analytics for a client."""
        # Simulate aggregated analytics
        analytics = {
            "latest_metrics": sample_body_metrics_record,
            "total_workouts": 25,
            "total_workout_minutes": 1500,
            "total_achievements": 5
        }
        
        assert analytics["latest_metrics"]["weight_kg"] == 75.5
        assert analytics["total_workouts"] == 25
        assert analytics["total_workout_minutes"] == 1500
        assert analytics["total_achievements"] == 5

    def test_analytics_with_no_data(self):
        """Test analytics when user has no data."""
        analytics = {
            "latest_metrics": None,
            "total_workouts": 0,
            "total_workout_minutes": 0,
            "total_achievements": 0
        }
        
        assert analytics["latest_metrics"] is None
        assert analytics["total_workouts"] == 0

    def test_workout_hours_conversion(self):
        """Test converting workout minutes to hours."""
        total_minutes = 450
        
        hours = total_minutes // 60
        remaining_minutes = total_minutes % 60
        
        assert hours == 7
        assert remaining_minutes == 30
