# SwingShift Survey System

**Last Updated: January 13, 2026**

A complete online survey platform for Shiftwork Solutions LLC, replacing Remark and SurveyMonkey with a custom solution that includes:

- **Question Bank**: 97+ proven survey questions developed over 30+ years
- **Survey Builder**: Select questions from the bank, add custom questions
- **Online Survey Application**: Employees take surveys on phone/computer
- **Processing & Reports**: Excel crosstabs, PowerPoint updates, benchmark comparisons

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        SWINGSHIFT.COM                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Frontend (React)          Backend (Flask)         Database          │
│  ├─ Admin Panel            ├─ REST API            PostgreSQL         │
│  ├─ Survey Builder         ├─ Report Generation   (Render)           │
│  └─ Survey Taking          └─ Benchmark Engine                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Project Structure

```
swingshift-survey/
├── backend/
│   ├── app.py              # Main Flask application (733 lines)
│   ├── models.py           # Database models (407 lines)
│   ├── requirements.txt    # Python dependencies
│   └── import_questions.py # Master question importer (735 lines)
├── frontend/               # React application (Phase 2)
├── scripts/                # Utility scripts
├── render.yaml             # Render deployment config
└── README.md
```

## Quick Start

### 1. Deploy Backend on Render

1. Go to [render.com](https://render.com) and sign in
2. Click **"New +"** → **"Web Service"**
3. Connect this GitHub repository
4. Configure:
   - **Name**: `swingshift-api`
   - **Root Directory**: `backend`
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app`
5. Add Environment Variables:
   - `SECRET_KEY`: (generate a random string)
   - `ADMIN_API_KEY`: (generate a random string - save this!)
   - `DATABASE_URL`: (from your PostgreSQL database)

### 2. Create PostgreSQL Database on Render

1. In Render, click **"New +"** → **"PostgreSQL"**
2. Name it `swingshift-db`
3. Copy the **Internal Database URL**
4. Add it as `DATABASE_URL` in your web service

### 3. Initialize Database

After first deployment, open the Render **Shell** and run:

```bash
cd backend
python -c "from app import app, db; app.app_context().push(); db.create_all(); print('Tables created!')"
python import_questions.py
```

## API Reference

### Health Check
```
GET /api/health
```

### Public Endpoints (Survey Taking)

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/survey/{access_code}` | Get survey questions for taking |
| `POST` | `/api/survey/{access_code}/start` | Start a new response session |
| `POST` | `/api/survey/{access_code}/answer` | Submit an answer |
| `POST` | `/api/survey/{access_code}/complete` | Mark survey as complete |

### Admin Endpoints (Require `X-API-Key` header)

**Questions**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/questions` | List all master questions |
| `GET` | `/api/questions?category=Demographics` | Filter by category |
| `GET` | `/api/questions/categories` | List all categories |
| `POST` | `/api/questions` | Create a new question |

**Projects**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/projects` | List all projects |
| `POST` | `/api/projects` | Create a new project |
| `GET` | `/api/projects/{id}` | Get project details |
| `PUT` | `/api/projects/{id}` | Update project |
| `GET` | `/api/projects/{id}/questions` | Get project questions |
| `POST` | `/api/projects/{id}/questions` | Add question to project |
| `POST` | `/api/projects/{id}/questions/bulk` | Add multiple questions |

**Results**
| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/projects/{id}/results` | Get survey results summary |
| `GET` | `/api/projects/{id}/export/csv` | Export responses to CSV |

## Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `DATABASE_URL` | PostgreSQL connection string | Yes |
| `SECRET_KEY` | Flask secret key | Yes |
| `ADMIN_API_KEY` | API key for admin endpoints | Yes |

## Database Schema

### Core Tables

- **master_questions**: The question bank (97+ questions)
- **response_options**: Answer choices for each question
- **projects**: Client survey projects
- **project_questions**: Questions selected for a project
- **custom_questions**: Client-specific custom questions
- **survey_responses**: Individual employee responses
- **response_answers**: Individual answers
- **normative_data**: Benchmark data from 200+ past surveys

## Development Phases

### Phase 1: Backend API ✅ (Current)
- Database models
- REST API endpoints
- Question bank import
- Basic authentication

### Phase 2: Admin Frontend (Next)
- Survey builder interface
- Project management
- Results dashboard

### Phase 3: Survey Taking Frontend
- Mobile-responsive survey UI
- Progress tracking
- Offline support

### Phase 4: Reports & Exports
- Excel crosstab generation
- PowerPoint template updates
- Benchmark comparisons

## Testing the API

```bash
# Health check
curl https://your-app.onrender.com/api/health

# Get all questions (admin)
curl https://your-app.onrender.com/api/questions \
  -H "X-API-Key: your-admin-key"

# Create a project (admin)
curl -X POST https://your-app.onrender.com/api/projects \
  -H "X-API-Key: your-admin-key" \
  -H "Content-Type: application/json" \
  -d '{"project_name": "Test Company", "company_name": "Test Company"}'
```

## Support

For questions about this system, contact Shiftwork Solutions LLC.

---

**Built for Shiftwork Solutions LLC** | Hundreds of companies helped over 30+ years


# I did no harm and this file is not truncated
