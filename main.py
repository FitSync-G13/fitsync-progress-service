from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from datetime import datetime, date
from typing import List, Optional, Dict
from pydantic import BaseModel, Field
from enum import Enum
import asyncpg
import redis.asyncio as aioredis
import os
import json
import logging
from jose import JWTError, jwt
import asyncio
import sys
sys.path.append(os.path.dirname(__file__))
from utils.http_client import validate_user, get_booking_details
from utils.event_publisher import publish_achievement_earned, publish_milestone_reached, publish_progress_updated

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("progress-service")

# Configuration
# Database configuration using connection string
# For production: Set DATABASE_URL with sslmode=require for TLS
# For local dev: Set DATABASE_URL without sslmode for plain connection
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise ValueError("DATABASE_URL environment variable is required")
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
JWT_SECRET = os.getenv("JWT_SECRET", "your-super-secret-jwt-key")

db_pool = None
redis_client = None

# Enums
class RecordType(str, Enum):
    injury = "injury"
    illness = "illness"
    medication = "medication"
    allergy = "allergy"
    condition = "condition"

class Severity(str, Enum):
    low = "low"
    medium = "medium"
    high = "high"

class AchievementType(str, Enum):
    weight_milestone = "weight_milestone"
    attendance_streak = "attendance_streak"
    personal_record = "personal_record"
    program_completion = "program_completion"

# Models
class BodyMetricsCreate(BaseModel):
    recorded_date: date
    weight_kg: float
    height_cm: Optional[float] = None
    body_fat_percentage: Optional[float] = None
    measurements: Optional[Dict[str, float]] = None
    notes: Optional[str] = None

class WorkoutLogCreate(BaseModel):
    booking_id: Optional[str] = None
    workout_date: date
    exercises_completed: List[Dict]
    total_duration_minutes: int
    calories_burned: Optional[int] = None
    trainer_notes: Optional[str] = None
    client_notes: Optional[str] = None
    mood_rating: Optional[int] = Field(None, ge=1, le=5)

class HealthRecordCreate(BaseModel):
    record_type: RecordType
    description: str
    start_date: date
    end_date: Optional[date] = None
    severity: Severity
    notes: Optional[str] = None

# Database initialization
async def init_db():
    global db_pool
    # Use connection string - TLS enabled if sslmode in URL
    # DevOps will handle proper certificates in production
    db_pool = await asyncpg.create_pool(
        dsn=DATABASE_URL,
        min_size=5,
        max_size=20,
        ssl='prefer'  # Use SSL if available, allow self-signed certs
    )
    ssl_status = "with TLS" if "sslmode" in DATABASE_URL else "without TLS"
    logger.info(f"Database pool created {ssl_status}")
    await run_migrations()

async def close_db():
    global db_pool
    if db_pool:
        await db_pool.close()

async def run_migrations():
    async with db_pool.acquire() as conn:
        await conn.execute("""
            CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

            CREATE TABLE IF NOT EXISTS body_metrics (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                client_id UUID NOT NULL,
                recorded_date DATE NOT NULL,
                weight_kg NUMERIC(5,2),
                height_cm NUMERIC(5,2),
                bmi NUMERIC(4,2),
                body_fat_percentage NUMERIC(4,2),
                measurements JSONB,
                notes TEXT,
                recorded_by UUID,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_body_metrics_client ON body_metrics(client_id);
            CREATE INDEX IF NOT EXISTS idx_body_metrics_date ON body_metrics(recorded_date);

            CREATE TABLE IF NOT EXISTS workout_logs (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                client_id UUID NOT NULL,
                booking_id UUID,
                workout_date DATE NOT NULL,
                exercises_completed JSONB NOT NULL,
                total_duration_minutes INTEGER,
                calories_burned INTEGER,
                trainer_notes TEXT,
                client_notes TEXT,
                mood_rating INTEGER CHECK (mood_rating >= 1 AND mood_rating <= 5),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_workout_logs_client ON workout_logs(client_id);
            CREATE INDEX IF NOT EXISTS idx_workout_logs_date ON workout_logs(workout_date);

            CREATE TABLE IF NOT EXISTS health_records (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                client_id UUID NOT NULL,
                record_type VARCHAR(20) CHECK (record_type IN ('injury', 'illness', 'medication', 'allergy', 'condition')),
                description TEXT NOT NULL,
                start_date DATE NOT NULL,
                end_date DATE,
                severity VARCHAR(10) CHECK (severity IN ('low', 'medium', 'high')),
                is_active BOOLEAN DEFAULT true,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE INDEX IF NOT EXISTS idx_health_records_client ON health_records(client_id);
            CREATE INDEX IF NOT EXISTS idx_health_records_active ON health_records(is_active);

            CREATE TABLE IF NOT EXISTS achievements (
                id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
                client_id UUID NOT NULL,
                achievement_type VARCHAR(30) CHECK (achievement_type IN ('weight_milestone', 'attendance_streak', 'personal_record', 'program_completion')),
                title VARCHAR(255) NOT NULL,
                description TEXT,
                achieved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                badge_icon VARCHAR(255)
            );

            CREATE INDEX IF NOT EXISTS idx_achievements_client ON achievements(client_id);
        """)
        logger.info("Migrations completed")

# Redis
async def init_redis():
    global redis_client
    redis_client = await aioredis.from_url(
        REDIS_URL,
        decode_responses=True
    )
    logger.info("Redis connected")

async def close_redis():
    if redis_client:
        await redis_client.close()

async def publish_event(channel: str, data: dict):
    try:
        await redis_client.publish(channel, json.dumps(data))
    except Exception as e:
        logger.error(f"Failed to publish event: {e}")

# Event Handlers
async def handle_booking_completed(event_data: dict):
    """Auto-create workout log when booking is completed"""
    try:
        data = event_data.get("data", {})
        logger.info(f"Handling booking.completed event for booking {data.get('booking_id')}")

        async with db_pool.acquire() as conn:
            # Check if workout log already exists for this booking
            existing = await conn.fetchval(
                "SELECT id FROM workout_logs WHERE booking_id = $1",
                data.get("booking_id")
            )

            if existing:
                logger.info(f"Workout log already exists for booking {data.get('booking_id')}")
                return

            # Create workout log stub
            await conn.execute("""
                INSERT INTO workout_logs (client_id, booking_id, workout_date,
                                         exercises_completed, total_duration_minutes, trainer_notes)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, data.get("client_id"), data.get("booking_id"),
                 data.get("workout_date"), json.dumps([]),
                 data.get("duration_minutes", 60), data.get("trainer_notes", ""))

            logger.info(f"Auto-created workout log for booking {data.get('booking_id')}")
    except Exception as e:
        logger.error(f"Error handling booking.completed event: {e}")


async def handle_program_completed(event_data: dict):
    """Award achievement when program is completed"""
    try:
        data = event_data.get("data", {})
        logger.info(f"Handling program.completed event for program {data.get('program_id')}")

        async with db_pool.acquire() as conn:
            # Award program completion achievement
            result = await conn.fetchrow("""
                INSERT INTO achievements (client_id, achievement_type, title, description, badge_icon)
                VALUES ($1, 'program_completion', $2, $3, 'program_complete.png')
                RETURNING *
            """, data.get("client_id"),
                 "Completed Training Program",
                 "You've successfully completed your training program!")

            if result:
                # Publish achievement earned event
                await publish_achievement_earned(redis_client, dict(result))
                logger.info(f"Achievement awarded to client {data.get('client_id')}")
    except Exception as e:
        logger.error(f"Error handling program.completed event: {e}")


async def subscribe_to_events():
    """Subscribe to Redis events"""
    try:
        pubsub = redis_client.pubsub()
        await pubsub.subscribe('booking.completed', 'program.completed')
        logger.info("Subscribed to Redis events: booking.completed, program.completed")

        async for message in pubsub.listen():
            if message['type'] == 'message':
                try:
                    event_data = json.loads(message['data'])
                    channel = message['channel']

                    if channel == 'booking.completed':
                        await handle_booking_completed(event_data)
                    elif channel == 'program.completed':
                        await handle_program_completed(event_data)
                except Exception as e:
                    logger.error(f"Error processing event from {message.get('channel')}: {e}")
    except Exception as e:
        logger.error(f"Event subscription error: {e}")

# Auth
def get_current_user(authorization: Optional[str] = None):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = authorization.split(" ")[1]
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"],
                           issuer="fitsync-user-service", audience="fitsync-api")
        return payload
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# Lifespan
@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    await init_redis()

    # Start event subscription in background
    subscription_task = asyncio.create_task(subscribe_to_events())

    yield

    # Cancel subscription task on shutdown
    subscription_task.cancel()
    try:
        await subscription_task
    except asyncio.CancelledError:
        pass

    await close_db()
    await close_redis()

# App
app = FastAPI(
    title="FitSync Progress Tracking Service",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "progress-service",
        "timestamp": datetime.utcnow().isoformat()
    }

# BODY METRICS

@app.post("/api/metrics")
async def record_metrics(
    metrics: BodyMetricsCreate,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)
    client_id = user["id"]

    # Calculate BMI if both height and weight provided
    bmi = None
    if metrics.height_cm and metrics.weight_kg:
        height_m = metrics.height_cm / 100
        bmi = round(metrics.weight_kg / (height_m ** 2), 2)

    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            """INSERT INTO body_metrics (client_id, recorded_date, weight_kg, height_cm, bmi,
                                        body_fat_percentage, measurements, notes, recorded_by)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING *""",
            client_id, metrics.recorded_date, metrics.weight_kg, metrics.height_cm, bmi,
            metrics.body_fat_percentage, json.dumps(metrics.measurements) if metrics.measurements else None,
            metrics.notes, user["id"]
        )
        return {"success": True, "data": dict(result)}

@app.get("/api/metrics/client/{client_id}")
async def get_client_metrics(
    client_id: str,
    page: int = 1,
    limit: int = 50,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    # Clients can only see their own data
    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    async with db_pool.acquire() as conn:
        results = await conn.fetch(
            "SELECT * FROM body_metrics WHERE client_id = $1 ORDER BY recorded_date DESC LIMIT $2 OFFSET $3",
            client_id, limit, offset
        )
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM body_metrics WHERE client_id = $1",
            client_id
        )

        return {
            "success": True,
            "data": [dict(r) for r in results],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": count,
                "total_pages": (count + limit - 1) // limit
            }
        }

@app.get("/api/metrics/client/{client_id}/latest")
async def get_latest_metrics(
    client_id: str,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM body_metrics WHERE client_id = $1 ORDER BY recorded_date DESC LIMIT 1",
            client_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="No metrics found")
        return {"success": True, "data": dict(result)}

@app.get("/api/metrics/client/{client_id}/chart")
async def get_metrics_chart_data(
    client_id: str,
    metric: str = "weight_kg",
    days: int = 90,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    async with db_pool.acquire() as conn:
        results = await conn.fetch(
            f"""SELECT recorded_date, {metric}
                FROM body_metrics
                WHERE client_id = $1 AND recorded_date >= CURRENT_DATE - $2
                ORDER BY recorded_date ASC""",
            client_id, days
        )

        data = [{"date": r["recorded_date"].isoformat(), "value": float(r[metric]) if r[metric] else None}
                for r in results]

        return {"success": True, "data": data}

# WORKOUT LOGS

@app.post("/api/workout-logs")
async def log_workout(
    log: WorkoutLogCreate,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)
    client_id = user["id"]

    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            """INSERT INTO workout_logs (client_id, booking_id, workout_date, exercises_completed,
                                        total_duration_minutes, calories_burned, trainer_notes,
                                        client_notes, mood_rating)
               VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
               RETURNING *""",
            client_id, log.booking_id, log.workout_date, json.dumps(log.exercises_completed),
            log.total_duration_minutes, log.calories_burned, log.trainer_notes,
            log.client_notes, log.mood_rating
        )
        return {"success": True, "data": dict(result)}

@app.get("/api/workout-logs/client/{client_id}")
async def get_workout_logs(
    client_id: str,
    page: int = 1,
    limit: int = 20,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    offset = (page - 1) * limit

    async with db_pool.acquire() as conn:
        results = await conn.fetch(
            "SELECT * FROM workout_logs WHERE client_id = $1 ORDER BY workout_date DESC LIMIT $2 OFFSET $3",
            client_id, limit, offset
        )
        count = await conn.fetchval(
            "SELECT COUNT(*) FROM workout_logs WHERE client_id = $1",
            client_id
        )

        return {
            "success": True,
            "data": [dict(r) for r in results],
            "pagination": {
                "page": page,
                "limit": limit,
                "total_count": count,
                "total_pages": (count + limit - 1) // limit
            }
        }

@app.get("/api/workout-logs/{log_id}")
async def get_workout_log(
    log_id: str,
    authorization: str = Header(None, alias="Authorization")
):
    get_current_user(authorization)

    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            "SELECT * FROM workout_logs WHERE id = $1",
            log_id
        )
        if not result:
            raise HTTPException(status_code=404, detail="Workout log not found")
        return {"success": True, "data": dict(result)}

# HEALTH RECORDS

@app.post("/api/health-records")
async def add_health_record(
    record: HealthRecordCreate,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)
    client_id = user["id"]

    async with db_pool.acquire() as conn:
        result = await conn.fetchrow(
            """INSERT INTO health_records (client_id, record_type, description, start_date,
                                          end_date, severity, notes)
               VALUES ($1, $2, $3, $4, $5, $6, $7)
               RETURNING *""",
            client_id, record.record_type.value, record.description, record.start_date,
            record.end_date, record.severity.value, record.notes
        )
        return {"success": True, "data": dict(result)}

@app.get("/api/health-records/client/{client_id}")
async def get_health_records(
    client_id: str,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    async with db_pool.acquire() as conn:
        results = await conn.fetch(
            "SELECT * FROM health_records WHERE client_id = $1 ORDER BY start_date DESC",
            client_id
        )
        return {"success": True, "data": [dict(r) for r in results]}

# ANALYTICS

@app.get("/api/analytics/client/{client_id}")
async def get_client_analytics(
    client_id: str,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    async with db_pool.acquire() as conn:
        # Get latest metrics
        latest_metrics = await conn.fetchrow(
            "SELECT * FROM body_metrics WHERE client_id = $1 ORDER BY recorded_date DESC LIMIT 1",
            client_id
        )

        # Get workout count
        workout_count = await conn.fetchval(
            "SELECT COUNT(*) FROM workout_logs WHERE client_id = $1",
            client_id
        )

        # Get total workout time
        total_workout_time = await conn.fetchval(
            "SELECT COALESCE(SUM(total_duration_minutes), 0) FROM workout_logs WHERE client_id = $1",
            client_id
        ) or 0

        # Get achievements count
        achievements_count = await conn.fetchval(
            "SELECT COUNT(*) FROM achievements WHERE client_id = $1",
            client_id
        )

        return {
            "success": True,
            "data": {
                "latest_metrics": dict(latest_metrics) if latest_metrics else None,
                "total_workouts": workout_count,
                "total_workout_minutes": int(total_workout_time),
                "total_achievements": achievements_count
            }
        }

# ACHIEVEMENTS

@app.get("/api/achievements/client/{client_id}")
async def get_achievements(
    client_id: str,
    authorization: str = Header(None, alias="Authorization")
):
    user = get_current_user(authorization)

    if user["role"] == "client" and user["id"] != client_id:
        raise HTTPException(status_code=403, detail="Insufficient permissions")

    async with db_pool.acquire() as conn:
        results = await conn.fetch(
            "SELECT * FROM achievements WHERE client_id = $1 ORDER BY achieved_at DESC",
            client_id
        )
        return {"success": True, "data": [dict(r) for r in results]}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8004))
    uvicorn.run(app, host="0.0.0.0", port=port)
