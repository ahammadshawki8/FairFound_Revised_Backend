# FairFound Backend

A comprehensive Django REST Framework backend for the FairFound AI-Powered Career Growth Platform for freelancers.

## Table of Contents

- [Overview](#overview)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Server](#running-the-server)
- [API Documentation](#api-documentation)
- [Apps Overview](#apps-overview)
- [API Endpoints](#api-endpoints)
- [AI Features](#ai-features)
- [Celery & Background Tasks](#celery--background-tasks)
- [Testing](#testing)
- [Deployment](#deployment)

---

## Overview

FairFound is an AI-powered platform designed to help freelancers grow their careers through:

- **AI Profile Analysis** - Comprehensive skill assessment and market positioning
- **Personalized Roadmaps** - AI-generated learning paths based on skill gaps
- **Mentorship System** - Connect with experienced mentors for guidance
- **AI Chatbot** - Gemini-powered assistant for real-time help
- **Community Features** - Posts, discussions, and networking
- **Portfolio & Proposal Tools** - AI-assisted content generation
- **Sentiment Analysis** - Analyze client feedback for insights

---

## Tech Stack

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.10+ | Runtime |
| Django | 4.2.x | Web Framework |
| Django REST Framework | 3.14+ | API Framework |
| PostgreSQL | 14+ | Database |
| Redis | 7+ | Caching & Celery Broker |
| Celery | 5.3+ | Background Tasks |
| Google Gemini AI | 1.5 Flash | AI/ML Features |
| SimpleJWT | 5.3+ | Authentication |
| drf-spectacular | 0.27+ | API Documentation |

---

## Project Structure

```
FairFound_Revised_Backend/
├── apps/
│   ├── agents/          # AI-powered profile analysis system
│   ├── analysis/        # Profile & sentiment analysis
│   ├── chat/            # User-to-user & AI chatbot
│   ├── community/       # Posts, comments, likes
│   ├── mentorship/      # Mentors, mentees, sessions
│   ├── notifications/   # User notifications
│   ├── payments/        # Payment processing
│   ├── portfolio/       # Portfolio & proposal generation
│   ├── roadmap/         # Learning roadmaps & tasks
│   └── users/           # Authentication & profiles
├── fairfound/
│   ├── settings.py      # Django settings
│   ├── urls.py          # Root URL configuration
│   ├── celery.py        # Celery configuration
│   └── wsgi.py          # WSGI entry point
├── media/               # User uploads
├── manage.py
├── requirements.txt
├── .env.example
└── README.md
```

---

## Installation

### Prerequisites

- Python 3.10 or higher
- PostgreSQL 14 or higher
- Redis (optional, for Celery)
- Git

### Step 1: Clone & Setup Virtual Environment

```bash
# Clone the repository
git clone <repository-url>
cd FairFound_Revised_Backend

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate
# Linux/Mac:
source .venv/bin/activate
```

### Step 2: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 3: Create PostgreSQL Database

```sql
-- Connect to PostgreSQL
psql -U postgres

-- Create database
CREATE DATABASE fairfound;

-- Create user (optional)
CREATE USER fairfound_user WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE fairfound TO fairfound_user;
```

### Step 4: Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your settings
```

### Step 5: Run Migrations

```bash
python manage.py migrate
```

### Step 6: Create Superuser

```bash
python manage.py createsuperuser
```

### Step 7: Seed Initial Data (Optional)

```bash
# Seed benchmark data for agents
python manage.py seed_benchmarks

# Seed sample mentors
python manage.py seed_mentors
```

---

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Django Settings
SECRET_KEY=your-super-secret-key-change-in-production
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=fairfound
DB_USER=postgres
DB_PASSWORD=your_password
DB_HOST=localhost
DB_PORT=5432

# CORS (Frontend URLs)
CORS_ALLOWED_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# AI APIs
GEMINI_API_KEY=your-google-gemini-api-key
GITHUB_TOKEN=your-github-personal-access-token

# Celery/Redis (Optional)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Getting API Keys

1. **Gemini API Key**: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
2. **GitHub Token**: Create at [GitHub Settings > Developer Settings > Personal Access Tokens](https://github.com/settings/tokens)

---

## Running the Server

### Development Server

```bash
python manage.py runserver
```

The API will be available at `http://localhost:8000/api/`

### With Celery (Background Tasks)

```bash
# Terminal 1: Start Redis
redis-server

# Terminal 2: Start Celery Worker
celery -A fairfound worker -l info

# Terminal 3: Start Django
python manage.py runserver
```

---

## API Documentation

### Swagger UI
Visit `http://localhost:8000/api/docs/` for interactive API documentation.

### OpenAPI Schema
Available at `http://localhost:8000/api/schema/`

### Admin Panel
Visit `http://localhost:8000/admin/` (requires superuser)

---

## Apps Overview

### 1. Users (`apps.users`)
Handles authentication, user management, and profiles.
- JWT-based authentication (access + refresh tokens)
- User registration and login
- Freelancer and Mentor profiles
- Avatar uploads

### 2. Agents (`apps.agents`)
AI-powered profile analysis system for junior frontend developers.
- Multi-factor scoring (skills, GitHub, portfolio, experience)
- Benchmark comparisons with synthetic data
- LLM-based evaluation using Gemini
- Tier classification (Rising Star → Elite)

### 3. Analysis (`apps.analysis`)
Profile and sentiment analysis services.
- SWOT analysis generation
- Skill gap identification
- Client feedback sentiment analysis

### 4. Chat (`apps.chat`)
Real-time messaging and AI chatbot.
- User-to-user messaging
- Thread replies
- File attachments
- **AI Chatbot** powered by Gemini 1.5 Flash

### 5. Community (`apps.community`)
Social features for freelancer networking.
- Posts with rich content
- Comments and replies
- Like/unlike functionality
- User following

### 6. Mentorship (`apps.mentorship`)
Mentor-mentee relationship management.
- Mentor profiles and availability
- Mentee connections
- Session scheduling
- Reviews and ratings

### 7. Notifications (`apps.notifications`)
User notification system.
- In-app notifications
- Read/unread status
- Bulk operations

### 8. Payments (`apps.payments`)
Payment processing for premium features.
- Checkout flow
- Payment history
- Subscription management

### 9. Portfolio (`apps.portfolio`)
Portfolio and proposal management.
- AI-generated portfolio content
- Proposal generation
- Template management

### 10. Roadmap (`apps.roadmap`)
Learning path and task management.
- AI-generated roadmaps
- Task tracking
- Progress monitoring

---

## API Endpoints

### Authentication
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/signup/` | Register new user |
| POST | `/api/auth/login/` | Login and get tokens |
| POST | `/api/auth/logout/` | Logout (blacklist token) |
| POST | `/api/auth/refresh/` | Refresh access token |
| GET | `/api/auth/me/` | Get current user |

### Profile
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/auth/profile/` | Get user profile |
| PUT | `/api/auth/profile/` | Update profile |
| PATCH | `/api/auth/profile/` | Partial update |
| POST | `/api/auth/avatar/` | Upload avatar |
| GET | `/api/auth/mentor-profile/` | Get mentor profile |
| PUT | `/api/auth/mentor-profile/` | Update mentor profile |

### Agents (AI Analysis)
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/agents/onboard/` | Submit profile for analysis |
| GET | `/api/agents/latest-analysis/` | Get latest analysis |
| GET | `/api/agents/jobs/` | List all analysis jobs |
| GET | `/api/agents/jobs/:id/` | Get job status |
| GET | `/api/agents/jobs/:id/analysis/` | Get detailed results |
| POST | `/api/agents/jobs/:id/regenerate/` | Re-run analysis |
| POST | `/api/agents/quick-analyze/` | Quick sync analysis |
| GET | `/api/agents/benchmarks/` | Get benchmark data |
| GET | `/api/agents/insights/` | Get AI insights |
| POST | `/api/agents/insights/` | Generate new insights |

### AI Chatbot
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chats/ai/` | List AI conversations |
| POST | `/api/chats/ai/` | Create new conversation |
| GET | `/api/chats/ai/:id/` | Get conversation with messages |
| PATCH | `/api/chats/ai/:id/` | Update conversation title |
| DELETE | `/api/chats/ai/:id/` | Delete conversation |
| POST | `/api/chats/ai/:id/chat/` | Send message to conversation |
| POST | `/api/chats/ai/chat/` | Send message (new conversation) |
| POST | `/api/chats/ai/quick/` | Quick chat (no history saved) |
| POST | `/api/chats/ai/:id/clear/` | Clear conversation history |

### User-to-User Chat
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/chats/` | List all chats |
| POST | `/api/chats/with/:user_id/` | Get/create chat with user |
| GET | `/api/chats/:id/messages/` | Get chat messages |
| POST | `/api/chats/:id/messages/send/` | Send message |
| GET | `/api/chats/:id/messages/:msg_id/replies/` | Get thread replies |
| POST | `/api/chats/:id/attachments/` | Upload attachment |
| PUT | `/api/chats/:id/read/` | Mark chat as read |

### Mentorship
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/mentors/` | List all mentors |
| GET | `/api/mentors/:id/` | Get mentor details |
| GET | `/api/mentors/:id/reviews/` | Get mentor reviews |
| POST | `/api/mentors/:id/connect/` | Connect with mentor |
| DELETE | `/api/mentors/:id/disconnect/` | Disconnect from mentor |
| GET | `/api/mentees/` | List mentees (mentor only) |
| GET | `/api/mentees/:id/` | Get mentee details |

### Sessions
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/sessions/` | List sessions |
| POST | `/api/sessions/` | Create session |
| GET | `/api/sessions/:id/` | Get session details |
| PUT | `/api/sessions/:id/` | Update session |
| DELETE | `/api/sessions/:id/` | Delete session |
| PUT | `/api/sessions/:id/status/` | Update session status |

### Roadmap & Tasks
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/roadmap/` | Get user's roadmap |
| POST | `/api/roadmap/steps/` | Create roadmap step |
| PUT | `/api/roadmap/steps/:id/` | Update step |
| DELETE | `/api/roadmap/steps/:id/` | Delete step |
| POST | `/api/roadmap/generate/` | AI generate roadmap |
| GET | `/api/tasks/` | List tasks |
| POST | `/api/tasks/` | Create task |
| PUT | `/api/tasks/:id/` | Update task |
| DELETE | `/api/tasks/:id/` | Delete task |
| PUT | `/api/tasks/:id/status/` | Update task status |

### Portfolio & Proposals
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/portfolio/` | Get portfolio |
| PUT | `/api/portfolio/` | Update portfolio |
| POST | `/api/portfolio/generate/` | AI generate portfolio |
| POST | `/api/proposals/generate/` | Generate proposal |
| GET | `/api/proposals/history/` | Proposal history |

### Community
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/community/posts/` | List posts |
| POST | `/api/community/posts/` | Create post |
| GET | `/api/community/posts/:id/` | Get post details |
| PUT | `/api/community/posts/:id/` | Update post |
| DELETE | `/api/community/posts/:id/` | Delete post |
| POST | `/api/community/posts/:id/like/` | Like/unlike post |
| POST | `/api/community/posts/:id/comment/` | Add comment |

### Notifications
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/notifications/` | List notifications |
| PATCH | `/api/notifications/:id/read/` | Mark as read |
| PUT | `/api/notifications/read-all/` | Mark all as read |
| DELETE | `/api/notifications/:id/` | Delete notification |
| DELETE | `/api/notifications/clear-all/` | Clear all |

### Payments
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/payments/checkout/` | Process checkout |
| GET | `/api/payments/history/` | Payment history |

### Analysis
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/analysis/profile/` | Analyze profile |
| GET | `/api/analysis/history/` | Analysis history |
| POST | `/api/sentiment/analyze/` | Sentiment analysis |
| GET | `/api/sentiment/history/` | Sentiment history |

---

## AI Features

### 1. AI Chatbot (Gemini 2.0 Flash)

The AI chatbot provides context-aware assistance:

```python
# Quick chat example
POST /api/chats/ai/quick/
{
    "message": "How can I improve my portfolio?",
    "page_context": "Portfolio page",
    "history": [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi! How can I help?"}
    ]
}
```

Features:
- Context-aware responses based on current page
- User profile integration (skills, experience)
- Conversation history support
- Fallback responses when API unavailable

### 2. Profile Analysis (Agents System)

Multi-factor scoring for junior developers:

| Factor | Weight | Description |
|--------|--------|-------------|
| Skills | 35% | Technical skill assessment |
| GitHub | 25% | Repository activity & quality |
| Portfolio | 20% | Project showcase quality |
| Experience | 15% | Years and depth |
| Momentum | 5% | Learning trajectory |

Tier Classification:
- **Rising Star** (0-40): Just starting out
- **Emerging** (40-55): Building foundation
- **Developing** (55-70): Gaining traction
- **Proficient** (70-85): Solid performer
- **Elite** (85-100): Top tier

### 3. AI-Generated Content

- **Roadmaps**: Personalized learning paths
- **Portfolios**: Professional content generation
- **Proposals**: Client proposal templates
- **Insights**: Market trends and recommendations

---

## Celery & Background Tasks

### Setup

```bash
# Install Redis
# Windows: Use WSL or Docker
# Mac: brew install redis
# Linux: sudo apt install redis-server

# Start Redis
redis-server

# Start Celery worker
celery -A fairfound worker -l info
```

### Available Tasks

```python
# apps/agents/tasks.py
- run_analysis_pipeline(job_id)  # Full analysis pipeline
- collect_github_data(username)  # GitHub data collection
- generate_llm_evaluation(job_id)  # LLM evaluation
```

### Without Celery

Analysis runs synchronously if Celery is not configured.

---

## Testing

### Run Tests

```bash
# Run all tests
python manage.py test

# Run specific app tests
python manage.py test apps.agents

# Run with coverage
coverage run manage.py test
coverage report
```

### Test Agents System

```bash
# Management command for testing
python manage.py test_agents
```

---

## Deployment on Render (Free Web Service)

### Step 1: Create PostgreSQL Database

1. Go to [Render Dashboard](https://dashboard.render.com)
2. Click **"New"** → **"PostgreSQL"**
3. Configure:
   - **Name**: `fairfound-db`
   - **Database**: `fairfound`
   - **User**: `fairfound_user`
   - **Region**: Oregon (or closest to you)
   - **Plan**: **Free**
4. Click **"Create Database"**
5. Wait for it to be created, then copy the **"External Database URL"**

### Step 2: Push Code to GitHub

```bash
# Make sure you're in the backend directory
cd FairFound_Revised_Backend

# Initialize git if not already
git init

# Add all files
git add .

# Commit
git commit -m "Prepare for Render deployment"

# Add your GitHub repo as remote
git remote add origin https://github.com/YOUR_USERNAME/YOUR_REPO.git

# Push
git push -u origin main
```

### Step 3: Create Web Service

1. Go to Render Dashboard → **"New"** → **"Web Service"**
2. Connect your GitHub account and select your repository
3. Configure the service:

| Setting | Value |
|---------|-------|
| **Name** | `fairfound-api` |
| **Region** | Oregon (same as database) |
| **Branch** | `main` |
| **Root Directory** | (leave empty or set if backend is in subfolder) |
| **Runtime** | `Python 3` |
| **Build Command** | `./build.sh` |
| **Start Command** | `gunicorn fairfound.wsgi:application` |
| **Plan** | **Free** |

### Step 4: Add Environment Variables

In the Web Service settings, go to **"Environment"** and add these variables:

| Key | Value |
|-----|-------|
| `DATABASE_URL` | `postgres://fairfound_user:PASSWORD@HOST/fairfound` (from Step 1) |
| `SECRET_KEY` | `your-super-secret-random-key-here` |
| `DEBUG` | `False` |
| `ALLOWED_HOSTS` | `.onrender.com` |
| `CORS_ALLOWED_ORIGINS` | `https://your-frontend.vercel.app` |
| `GEMINI_API_KEY` | `your-gemini-api-key` |
| `GITHUB_TOKEN` | `your-github-token` |
| `PYTHON_VERSION` | `3.10.12` |
| `DJANGO_SUPERUSER_USERNAME` | `admin` |
| `DJANGO_SUPERUSER_EMAIL` | `admin@yoursite.com` |
| `DJANGO_SUPERUSER_PASSWORD` | `your-secure-admin-password` |

**To generate a SECRET_KEY**, run this in Python:
```python
import secrets
print(secrets.token_urlsafe(50))
```

### Step 5: Deploy

1. Click **"Create Web Service"**
2. Render will automatically:
   - Clone your repo
   - Run `build.sh` (install deps, migrate, collect static, **create superuser**)
   - Start the server with gunicorn
3. Wait 5-10 minutes for the first deploy

### Step 6: Verify Deployment

Once deployed, your API will be at:
```
https://fairfound-api.onrender.com
```

Test these URLs:
- `https://fairfound-api.onrender.com/api/docs/` - Swagger UI
- `https://fairfound-api.onrender.com/api/auth/login/` - Login endpoint
- `https://fairfound-api.onrender.com/admin/` - Admin panel (login with superuser credentials)

### Step 7: Seed Data (Optional)

In the Shell tab:
```bash
python manage.py seed_mentors
python manage.py seed_benchmarks
```

---

## Troubleshooting

### Build Fails

1. Check the build logs in Render dashboard
2. Common issues:
   - Missing `build.sh` execute permission: Add `chmod +x build.sh` or check file exists
   - Wrong Python version: Ensure `.python-version` file exists

### Database Connection Error

1. Verify `DATABASE_URL` is correct
2. Make sure you're using the **External** URL (not Internal)
3. Check the database is running in Render dashboard

### CORS Errors

1. Update `CORS_ALLOWED_ORIGINS` with your exact frontend URL
2. Include both `http://` and `https://` versions if needed
3. No trailing slash in the URL

### Static Files Not Loading

1. Ensure `whitenoise` is in requirements.txt
2. Check `STATICFILES_STORAGE` is set in settings.py
3. Verify `collectstatic` runs in build.sh

---

## Free Tier Limitations

| Resource | Limit |
|----------|-------|
| Web Service | Spins down after 15 min inactivity |
| Cold Start | ~30 seconds after spin-down |
| PostgreSQL | 1GB storage, expires after 90 days |
| Bandwidth | 100 GB/month |

**Tip**: The free tier is great for development/demo. For production, consider upgrading.

---

## Update Frontend API URL

After deployment, update your frontend to use the Render URL:

```typescript
// In your frontend .env or constants
VITE_API_URL=https://fairfound-api.onrender.com/api
```

---

## Files Required for Render

| File | Purpose |
|------|---------|
| `build.sh` | Build script (runs on every deploy) |
| `requirements.txt` | Python dependencies |
| `.python-version` | Python version (3.10.12) |
| `fairfound/settings.py` | Django settings with Render support |

---

## License

This project is proprietary software. All rights reserved.

---

## Support

For issues or questions, please contact the development team.
