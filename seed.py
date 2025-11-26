import asyncio
import asyncpg
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

load_dotenv()

# Test user IDs from user service
TRAINER_ID = '4420f58b-f7b9-415c-afcb-60d23ae6c17f'  # trainer@fitsync.com
CLIENT_ID = 'ae34ea3f-fea2-42bb-b7bc-8337e4f187f5'   # client@fitsync.com

async def seed_data():
    """Seed progress service with test data"""
    conn = await asyncpg.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5435)),
        user=os.getenv('DB_USER', 'fitsync'),
        password=os.getenv('DB_PASSWORD', 'fitsync123'),
        database=os.getenv('DB_NAME', 'progressdb')
    )

    try:
        # Create body metrics history (last 30 days)
        print("Creating body metrics...")
        metrics_count = 0

        start_weight = 80.0
        for day_offset in range(0, 31, 3):  # Every 3 days
            date = datetime.now().date() - timedelta(days=30 - day_offset)
            weight = start_weight - (day_offset * 0.2)  # Gradual weight loss

            try:
                await conn.execute("""
                    INSERT INTO body_metrics
                    (client_id, weight_kg, height_cm, body_fat_percentage, muscle_mass_kg, recorded_date, notes)
                    VALUES ($1, $2, $3, $4, $5, $6, $7)
                """, CLIENT_ID, round(weight, 1), 175, round(22 - (day_offset * 0.1), 1),
                     round(60 + (day_offset * 0.1), 1), date, f"Week {day_offset // 7 + 1} progress check")
                metrics_count += 1
            except Exception as e:
                print(f"Metric already exists for {date}")

        print(f"Created {metrics_count} body metrics entries")

        # Create workout logs
        print("Creating workout logs...")
        logs_count = 0

        exercises_completed = [
            {
                "exercise_name": "Bench Press",
                "sets": [
                    {"set_number": 1, "reps": 12, "weight_kg": 60},
                    {"set_number": 2, "reps": 10, "weight_kg": 65},
                    {"set_number": 3, "reps": 8, "weight_kg": 70}
                ]
            },
            {
                "exercise_name": "Squats",
                "sets": [
                    {"set_number": 1, "reps": 12, "weight_kg": 80},
                    {"set_number": 2, "reps": 10, "weight_kg": 90},
                    {"set_number": 3, "reps": 8, "weight_kg": 95}
                ]
            },
            {
                "exercise_name": "Pull-ups",
                "sets": [
                    {"set_number": 1, "reps": 10, "weight_kg": 0},
                    {"set_number": 2, "reps": 8, "weight_kg": 0},
                    {"set_number": 3, "reps": 6, "weight_kg": 0}
                ]
            }
        ]

        # Create logs for the past 3 weeks (3 workouts per week)
        for week in range(3):
            for session in range(3):
                date = datetime.now().date() - timedelta(days=(2 - week) * 7 + session * 2)

                try:
                    await conn.execute("""
                        INSERT INTO workout_logs
                        (client_id, workout_date, exercises_completed, total_duration_minutes,
                         calories_burned, perceived_exertion, trainer_notes)
                        VALUES ($1, $2, $3, $4, $5, $6, $7)
                    """, CLIENT_ID, date, json.dumps(exercises_completed), 60,
                         450, 7, "Excellent form and intensity!")
                    logs_count += 1
                except Exception as e:
                    print(f"Workout log already exists for {date}")

        print(f"Created {logs_count} workout logs")

        # Create health records
        print("Creating health records...")
        try:
            await conn.execute("""
                INSERT INTO health_records
                (client_id, record_type, record_date, details, notes)
                VALUES ($1, $2, $3, $4, $5)
            """, CLIENT_ID, "medical_clearance", datetime.now().date() - timedelta(days=60),
                 json.dumps({
                     "cleared_by": "Dr. Smith",
                     "conditions": [],
                     "restrictions": "None",
                     "medications": []
                 }), "Cleared for all activities")
            print("Created 1 health record")
        except Exception as e:
            print(f"Health record already exists: {e}")

        # Create achievements
        print("Creating achievements...")
        achievements_count = 0

        achievement_data = [
            {
                "type": "workout_streak",
                "title": "7-Day Streak",
                "description": "Completed workouts for 7 consecutive days"
            },
            {
                "type": "weight_milestone",
                "title": "5kg Weight Loss",
                "description": "Successfully lost 5kg"
            },
            {
                "type": "strength_gain",
                "title": "First 100kg Squat",
                "description": "Achieved 100kg squat"
            }
        ]

        for achievement in achievement_data:
            try:
                await conn.execute("""
                    INSERT INTO achievements
                    (client_id, achievement_type, title, description, achieved_date)
                    VALUES ($1, $2, $3, $4, $5)
                """, CLIENT_ID, achievement["type"], achievement["title"],
                     achievement["description"], datetime.now().date() - timedelta(days=10))
                achievements_count += 1
            except Exception as e:
                print(f"Achievement already exists: {achievement['title']}")

        print(f"Created {achievements_count} achievements")

        print("✅ Progress service seed completed successfully!")

    except Exception as e:
        print(f"❌ Seed failed: {e}")
        raise
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(seed_data())
