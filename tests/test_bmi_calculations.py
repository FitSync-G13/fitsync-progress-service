"""
Unit tests for BMI calculations and body metrics logic.
"""
import pytest
from datetime import date, datetime
from unittest.mock import AsyncMock, MagicMock, patch
from pydantic import ValidationError
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main import BodyMetricsCreate


class TestBMICalculation:
    """Tests for BMI calculation logic."""

    def test_bmi_calculation_normal_weight(self):
        """Test BMI calculation for normal weight person."""
        weight_kg = 70.0
        height_cm = 175.0
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi == 22.86
        assert 18.5 <= bmi < 25  # Normal range

    def test_bmi_calculation_overweight(self):
        """Test BMI calculation for overweight person."""
        weight_kg = 85.0
        height_cm = 170.0
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi == 29.41
        assert 25 <= bmi < 30  # Overweight range

    def test_bmi_calculation_underweight(self):
        """Test BMI calculation for underweight person."""
        weight_kg = 50.0
        height_cm = 175.0
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi == 16.33
        assert bmi < 18.5  # Underweight

    def test_bmi_calculation_obese(self):
        """Test BMI calculation for obese person."""
        weight_kg = 120.0
        height_cm = 180.0
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi == 37.04
        assert bmi >= 30  # Obese

    def test_bmi_calculation_tall_person(self):
        """Test BMI calculation for tall person."""
        weight_kg = 90.0
        height_cm = 195.0
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi == 23.67

    def test_bmi_calculation_short_person(self):
        """Test BMI calculation for short person."""
        weight_kg = 55.0
        height_cm = 155.0
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi == 22.89

    def test_bmi_rounding_precision(self):
        """Test that BMI is rounded to 2 decimal places."""
        weight_kg = 72.3
        height_cm = 178.5
        
        height_m = height_cm / 100
        bmi = round(weight_kg / (height_m ** 2), 2)
        
        # Should be exactly 2 decimal places
        assert len(str(bmi).split('.')[1]) <= 2

    def test_bmi_none_when_height_missing(self):
        """Test BMI is None when height is not provided."""
        weight_kg = 70.0
        height_cm = None
        
        bmi = None
        if height_cm and weight_kg:
            height_m = height_cm / 100
            bmi = round(weight_kg / (height_m ** 2), 2)
        
        assert bmi is None


class TestBMICategories:
    """Tests for BMI category classification."""

    def classify_bmi(self, bmi):
        """Classify BMI into categories."""
        if bmi < 18.5:
            return "underweight"
        elif 18.5 <= bmi < 25:
            return "normal"
        elif 25 <= bmi < 30:
            return "overweight"
        else:
            return "obese"

    def test_classify_underweight(self):
        """Test underweight classification."""
        assert self.classify_bmi(16.0) == "underweight"
        assert self.classify_bmi(18.4) == "underweight"

    def test_classify_normal(self):
        """Test normal weight classification."""
        assert self.classify_bmi(18.5) == "normal"
        assert self.classify_bmi(22.0) == "normal"
        assert self.classify_bmi(24.9) == "normal"

    def test_classify_overweight(self):
        """Test overweight classification."""
        assert self.classify_bmi(25.0) == "overweight"
        assert self.classify_bmi(27.5) == "overweight"
        assert self.classify_bmi(29.9) == "overweight"

    def test_classify_obese(self):
        """Test obese classification."""
        assert self.classify_bmi(30.0) == "obese"
        assert self.classify_bmi(35.0) == "obese"
        assert self.classify_bmi(40.0) == "obese"


class TestBodyMetricsModel:
    """Tests for BodyMetricsCreate Pydantic model."""

    def test_create_metrics_with_all_fields(self, sample_body_metrics_data):
        """Test creating metrics with all fields."""
        metrics = BodyMetricsCreate(**sample_body_metrics_data)
        
        assert metrics.recorded_date == date(2025, 1, 15)
        assert metrics.weight_kg == 75.5
        assert metrics.height_cm == 175.0
        assert metrics.body_fat_percentage == 18.5
        assert metrics.measurements == {"chest": 100, "waist": 85, "hips": 95}
        assert metrics.notes == "Weekly measurement"

    def test_create_metrics_minimal(self):
        """Test creating metrics with only required fields."""
        metrics = BodyMetricsCreate(
            recorded_date=date(2025, 1, 15),
            weight_kg=70.0
        )
        
        assert metrics.weight_kg == 70.0
        assert metrics.height_cm is None
        assert metrics.body_fat_percentage is None
        assert metrics.measurements is None

    def test_create_metrics_without_height(self):
        """Test creating metrics without height - BMI won't be calculated."""
        metrics = BodyMetricsCreate(
            recorded_date=date(2025, 1, 15),
            weight_kg=80.0
        )
        
        assert metrics.weight_kg == 80.0
        assert metrics.height_cm is None

    def test_metrics_with_measurements_dict(self):
        """Test metrics with measurements dictionary."""
        measurements = {
            "chest": 105.5,
            "waist": 88.0,
            "hips": 100.0,
            "bicep_left": 35.5,
            "bicep_right": 36.0,
            "thigh_left": 58.0,
            "thigh_right": 58.5
        }
        
        metrics = BodyMetricsCreate(
            recorded_date=date(2025, 1, 15),
            weight_kg=85.0,
            measurements=measurements
        )
        
        assert len(metrics.measurements) == 7
        assert metrics.measurements["chest"] == 105.5


class TestWeightProgressCalculation:
    """Tests for weight progress calculations."""

    def test_weight_change_loss(self):
        """Test calculating weight loss."""
        initial_weight = 85.0
        current_weight = 80.0
        
        change = current_weight - initial_weight
        percentage_change = (change / initial_weight) * 100
        
        assert change == -5.0
        assert round(percentage_change, 2) == -5.88

    def test_weight_change_gain(self):
        """Test calculating weight gain."""
        initial_weight = 70.0
        current_weight = 75.0
        
        change = current_weight - initial_weight
        percentage_change = (change / initial_weight) * 100
        
        assert change == 5.0
        assert round(percentage_change, 2) == 7.14

    def test_weight_change_no_change(self):
        """Test when weight hasn't changed."""
        initial_weight = 75.0
        current_weight = 75.0
        
        change = current_weight - initial_weight
        
        assert change == 0.0

    def test_weekly_weight_trend(self):
        """Test calculating weekly weight trend."""
        weekly_weights = [85.0, 84.5, 84.2, 83.8, 83.5]
        
        total_change = weekly_weights[-1] - weekly_weights[0]
        avg_weekly_change = total_change / (len(weekly_weights) - 1)
        
        assert total_change == -1.5
        assert round(avg_weekly_change, 2) == -0.38

    def test_body_fat_change(self):
        """Test body fat percentage change calculation."""
        initial_bf = 22.5
        current_bf = 18.5
        
        change = current_bf - initial_bf
        
        assert change == -4.0


class TestMetricsChartDataPreparation:
    """Tests for preparing metrics data for charts."""

    def test_prepare_weight_chart_data(self, sample_body_metrics_record):
        """Test preparing weight data for chart."""
        records = [
            {"recorded_date": date(2025, 1, 10), "weight_kg": 76.0},
            {"recorded_date": date(2025, 1, 15), "weight_kg": 75.5},
            {"recorded_date": date(2025, 1, 20), "weight_kg": 75.0}
        ]
        
        chart_data = [
            {"date": r["recorded_date"].isoformat(), "value": float(r["weight_kg"])}
            for r in records
        ]
        
        assert len(chart_data) == 3
        assert chart_data[0]["date"] == "2025-01-10"
        assert chart_data[0]["value"] == 76.0

    def test_handle_none_values_in_chart(self):
        """Test handling None values in chart data."""
        records = [
            {"recorded_date": date(2025, 1, 10), "body_fat_percentage": 20.0},
            {"recorded_date": date(2025, 1, 15), "body_fat_percentage": None},
            {"recorded_date": date(2025, 1, 20), "body_fat_percentage": 19.5}
        ]
        
        chart_data = [
            {"date": r["recorded_date"].isoformat(), 
             "value": float(r["body_fat_percentage"]) if r["body_fat_percentage"] else None}
            for r in records
        ]
        
        assert chart_data[1]["value"] is None

    def test_date_range_filtering(self):
        """Test filtering metrics by date range."""
        today = date(2025, 1, 30)
        days = 30
        
        cutoff_date = date(2025, 1, 1)  # 30 days before
        
        records = [
            {"recorded_date": date(2024, 12, 15), "weight_kg": 78.0},  # Too old
            {"recorded_date": date(2025, 1, 5), "weight_kg": 77.0},   # Within range
            {"recorded_date": date(2025, 1, 25), "weight_kg": 75.5},  # Within range
        ]
        
        filtered = [r for r in records if r["recorded_date"] >= cutoff_date]
        
        assert len(filtered) == 2
        assert filtered[0]["weight_kg"] == 77.0
