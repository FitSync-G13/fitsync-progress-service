# FitSync Progress Service

Progress tracking and analytics service for the FitSync application.

## Features

- Body metrics tracking (weight, BMI, body fat %)
- Workout logging and history
- Progress analytics and charts
- Goal setting and achievement tracking
- Performance metrics
- Historical data analysis

## Technology Stack

- Python 3.11+
- FastAPI web framework
- PostgreSQL database
- Redis for caching
- SQLAlchemy ORM

## Running the Full FitSync Application

This service is part of the FitSync multi-repository application. To run the complete application:

### Quick Start

1. **Clone all repositories:**

```bash
mkdir fitsync-app && cd fitsync-app

git clone https://github.com/FitSync-G13/fitsync-docker-compose.git
git clone https://github.com/FitSync-G13/fitsync-api-gateway.git
git clone https://github.com/FitSync-G13/fitsync-user-service.git
git clone https://github.com/FitSync-G13/fitsync-training-service.git
git clone https://github.com/FitSync-G13/fitsync-schedule-service.git
git clone https://github.com/FitSync-G13/fitsync-progress-service.git
git clone https://github.com/FitSync-G13/fitsync-notification-service.git
git clone https://github.com/FitSync-G13/fitsync-frontend.git
```

2. **Run setup:**

```bash
cd fitsync-docker-compose
./setup.sh    # Linux/Mac
setup.bat     # Windows
```

3. **Access:** http://localhost:3000

## Development - Run This Service Locally

1. **Start infrastructure:**
```bash
cd ../fitsync-docker-compose
docker compose up -d progressdb redis user-service
docker compose stop progress-service
```

2. **Install dependencies:**
```bash
cd ../fitsync-progress-service
pip install -r requirements.txt
```

3. **Configure environment (.env):**
```env
ENVIRONMENT=development
PORT=8004
DB_HOST=localhost
DB_PORT=5435
DB_NAME=progressdb
DB_USER=fitsync
DB_PASSWORD=fitsync123
REDIS_HOST=localhost
REDIS_PORT=6379
USER_SERVICE_URL=http://localhost:3001
JWT_SECRET=your-super-secret-jwt-key-change-in-production
```

4. **Run migrations:**
```bash
python -m alembic upgrade head
```

5. **Start development server:**
```bash
uvicorn app:app --reload --port 8004
```

Service runs on http://localhost:8004

## API Endpoints

- `GET /api/progress/metrics` - Get body metrics
- `POST /api/progress/metrics` - Log new metrics
- `GET /api/progress/workouts` - Get workout logs
- `POST /api/progress/workouts` - Log workout
- `GET /api/progress/analytics` - Get analytics data
- `GET /api/progress/goals` - Get goals

## Testing

**Current Status: 77 tests passing ✓**

### Prerequisites

Create and activate a virtual environment:
```bash
python3 -m venv test_venv
source test_venv/bin/activate  # Linux/Mac
# or
test_venv\Scripts\activate     # Windows
```

Install test dependencies:
```bash
pip install pytest pytest-asyncio pytest-cov httpx fastapi pydantic python-jose asyncpg redis
```

### Running Tests

Run all tests:
```bash
pytest tests/
```

Run tests with verbose output:
```bash
pytest tests/ -v
```

Run tests with coverage report:
```bash
pytest tests/ --cov=. --cov-report=term-missing
```

Generate HTML coverage report:
```bash
pytest tests/ --cov=. --cov-report=html
open htmlcov/index.html
```

Run specific test file:
```bash
pytest tests/test_bmi_calculations.py -v
pytest tests/test_analytics.py -v
pytest tests/test_event_handlers.py -v
pytest tests/test_http_client.py -v
```

Run tests matching a pattern:
```bash
pytest tests/ -k "bmi"
pytest tests/ -k "analytics"
pytest tests/ -k "event"
```

### Test Structure

```
tests/
├── conftest.py              # Shared fixtures and test configuration
├── test_bmi_calculations.py # BMI and body metrics logic (24 tests)
├── test_analytics.py        # Analytics aggregation (23 tests)
├── test_event_handlers.py   # Event handler logic (19 tests)
└── test_http_client.py      # Inter-service HTTP client (11 tests)
```

### Test Categories

1. **BMI Calculation Tests** (`test_bmi_calculations.py`) - 24 tests
   - BMI formula calculations (normal, overweight, underweight, obese)
   - BMI category classification
   - BodyMetricsCreate model validation
   - Weight progress calculations (loss, gain, trends)
   - Chart data preparation and filtering

2. **Analytics Tests** (`test_analytics.py`) - 23 tests
   - Workout analytics (count, duration, calories, mood)
   - Weekly analytics (streak tracking, averages)
   - Progress analytics (weight trend, body fat, goal progress)
   - Achievement counting and sorting
   - Pagination calculations

3. **Event Handler Tests** (`test_event_handlers.py`) - 19 tests
   - booking.completed handler (creates workout log, skips duplicates)
   - program.completed handler (creates achievement, publishes event)
   - Event data parsing and JSON handling
   - Event publishing (achievement.earned, milestone.reached, progress.updated)
   - Achievement trigger conditions (milestones, streaks, PRs)

4. **HTTP Client Tests** (`test_http_client.py`) - 11 tests
   - User validation (success, not found, connection error, timeout)
   - Booking details retrieval
   - Program details retrieval
   - Authorization header handling (Bearer prefix)

### Coverage Target

- Minimum coverage target: 70%
- Focus on business logic: BMI calculations, analytics aggregation, event handlers

## Database Schema

Main tables:
- `body_metrics` - Body measurements and metrics
- `workout_logs` - Workout completion logs
- `goals` - User fitness goals
- `achievements` - Milestone achievements

## More Information

See [fitsync-docker-compose](https://github.com/FitSync-G13/fitsync-docker-compose) for complete documentation.

## License

MIT
