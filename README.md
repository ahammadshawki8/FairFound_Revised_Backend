# FairFound Backend

Django REST Framework backend for the FairFound AI-Powered Career Growth Platform.

## Tech Stack

- Django 4.2
- Django REST Framework
- PostgreSQL
- JWT Authentication (SimpleJWT)
- Google Gemini AI

## Setup

### 1. Create Virtual Environment

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment

```bash
cp .env.example .env
# Edit .env with your settings
```

### 4. Create PostgreSQL Database

```sql
CREATE DATABASE fairfound;
```

### 5. Run Migrations

```bash
python manage.py migrate
```

### 6. Create Superuser

```bash
python manage.py createsuperuser
```

### 7. Run Server

```bash
python manage.py runserver
```

## API Documentation

Visit `/api/docs/` for Swagger UI documentation.

## API Endpoints

### Authentication
- `POST /api/auth/login/` - Login
- `POST /api/auth/signup/` - Register
- `POST /api/auth/logout/` - Logout
- `POST /api/auth/refresh/` - Refresh token
- `GET /api/auth/me/` - Current user

### Profile
- `GET/PUT /api/profile/` - User profile
- `POST /api/profile/avatar/` - Upload avatar

### Analysis
- `POST /api/analysis/profile/` - Analyze profile
- `GET /api/analysis/history/` - Analysis history
- `POST /api/sentiment/analyze/` - Sentiment analysis
- `GET /api/sentiment/history/` - Sentiment history

### Roadmap
- `GET /api/roadmap/` - Get roadmap
- `POST /api/roadmap/steps/` - Create step
- `PUT/DELETE /api/roadmap/steps/:id/` - Update/delete step
- `POST /api/roadmap/generate/` - AI generate roadmap

### Tasks
- `GET/POST /api/tasks/` - List/create tasks
- `PUT/DELETE /api/tasks/:id/` - Update/delete task
- `PUT /api/tasks/:id/status/` - Update status

### Mentors
- `GET /api/mentors/` - List mentors
- `GET /api/mentors/:id/` - Mentor details
- `GET /api/mentors/:id/reviews/` - Mentor reviews
- `POST /api/mentors/:id/connect/` - Connect
- `DELETE /api/mentors/:id/disconnect/` - Disconnect

### Sessions
- `GET/POST /api/sessions/` - List/create sessions
- `PUT/DELETE /api/sessions/:id/` - Update/delete
- `PUT /api/sessions/:id/status/` - Update status

### Mentees (Mentor only)
- `GET /api/mentees/` - List mentees
- `GET /api/mentees/:id/` - Mentee details

### Portfolio
- `GET/PUT /api/portfolio/` - Portfolio
- `POST /api/portfolio/generate/` - AI generate

### Proposals
- `POST /api/proposals/generate/` - Generate proposal
- `GET /api/proposals/history/` - History

### Community
- `GET/POST /api/community/posts/` - Posts
- `POST /api/community/posts/:id/like/` - Like
- `POST /api/community/posts/:id/comment/` - Comment

### Chat
- `GET /api/chats/` - List chats
- `GET /api/chats/:id/messages/` - Messages
- `POST /api/chats/:id/messages/send/` - Send message

### Notifications
- `GET /api/notifications/` - List
- `PUT /api/notifications/read/` - Mark all read

### Payments
- `POST /api/payments/checkout/` - Checkout
- `GET /api/payments/history/` - History

### Agents (Junior Frontend Developer Analysis)

The agents system is focused on analyzing junior frontend developers (0-2 years experience).

**Main Endpoints:**
- `POST /api/agents/onboard/` - Submit profile for analysis
- `GET /api/agents/jobs/` - List analysis jobs
- `GET /api/agents/jobs/:id/` - Job status
- `GET /api/agents/jobs/:id/analysis/` - Detailed results
- `POST /api/agents/jobs/:id/regenerate/` - Re-run analysis
- `POST /api/agents/quick-analyze/` - Quick sync analysis
- `GET /api/agents/benchmarks/` - Benchmark data

**Admin Endpoints:**
- `POST /api/agents/admin/seed-benchmarks/` - Seed benchmark data
- `GET /api/agents/admin/review/queue/` - Review queue
- `POST /api/agents/admin/review/:id/action/` - Review action

**Scoring Weights:**
- Skills: 35% (most important for juniors)
- GitHub: 25% (shows initiative)
- Portfolio: 20% (practical ability)
- Experience: 15% (less weight for juniors)
- Momentum: 5% (growth trajectory)

## Quick Start for Agents

```bash
# 1. Run migrations
python manage.py migrate

# 2. Seed benchmark data (200 synthetic profiles)
python manage.py seed_benchmarks

# 3. Test quick analysis
curl -X POST /api/agents/quick-analyze/ \
  -H "Authorization: Bearer <token>" \
  -d '{"skills": ["react", "javascript"], "experience_years": 1}'
```

## Celery Setup (Optional)

For async processing:

```bash
redis-server
celery -A fairfound worker -l info
```

Without Celery, analysis runs synchronously.
