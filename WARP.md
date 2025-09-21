# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Development Commands

### Environment Setup
```bash
# Create and activate virtual environment (Linux/macOS)
python3 -m venv venv
source venv/bin/activate

# Windows
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Database Operations
```bash
# Initialize database with sample data
python db.py

# This creates engagement_hackathon.db with all required tables and generates random sample data
```

### Running the Application
```bash
# Development server
python app.py
# App runs on http://localhost:5000

# Using the automated setup script (Linux/macOS)
chmod +x start.sh
./start.sh
# This script handles environment setup, dependency installation, database initialization, and app startup

# Build script for deployment
chmod +x build.sh
./build.sh
```

### Machine Learning Model Operations
```bash
# The ML model is automatically initialized when the app starts
# To manually retrain the model, use the API endpoint:
# POST /api/retrain-model

# To update all predictions:
# POST /api/update-predictions
```

## High-Level Architecture

### Core Components

**Flask Web Application (`app.py`)**
- Main application entry point (34,000+ lines)
- RESTful API endpoints for all features
- Session management and authentication
- Integrates ML model for real-time predictions
- Key endpoints: `/dashboard`, `/learners`, `/analytics`, `/interventions`, `/tickets`

**Machine Learning Engine (`engagement_predictor.py`)**
- `EngagementPredictor` class using ensemble learning
- Combines RandomForestRegressor and GradientBoostingRegressor in a VotingRegressor
- Features extracted from: login activity, assignments, quizzes, live sessions, support tickets
- Automatic model persistence with joblib
- Real-time engagement scoring and status prediction (On Track/At Risk/Will Drop Off)

**Database Layer (`db.py`)**
- SQLite database with 9+ normalized tables
- Sample data generation for development
- Schema includes: Users, Courses, Cohorts, Learners, Login_Activity, Assignment_Details, Quiz_Details, Live_Session, Ticket_Details, Nudge_Logs

### Data Flow Architecture

1. **User Authentication**: Role-based access (Super Admin, Program Coordinator)
2. **Data Collection**: Student activities tracked across multiple touchpoints
3. **Feature Engineering**: ML pipeline extracts 20+ behavioral features per learner
4. **Prediction Engine**: Ensemble model predicts engagement scores (0-100)
5. **Intervention System**: Automated nudging based on risk classification
6. **Analytics Dashboard**: Real-time visualization with Chart.js

### Key Design Patterns

**Model-View-Controller**: Flask routes (Controller) + Jinja2 templates (View) + SQLite (Model)
**Service Layer**: `EngagementPredictor` encapsulates all ML operations
**Repository Pattern**: Database connection helper functions abstract data access
**Factory Pattern**: Model initialization with fallback mechanisms

### Feature Engineering Strategy

The ML model extracts comprehensive behavioral patterns:
- **Temporal Features**: Login frequency, session duration patterns, days since last activity
- **Performance Metrics**: Assignment scores, quiz performance, submission rates
- **Engagement Indicators**: Attendance rates, ticket resolution, satisfaction scores
- **Consistency Measures**: Score variance, activity regularity, participation trends

### File Structure Context

- `templates/`: 7 HTML files with embedded JavaScript for interactive dashboards
- `engagement_model.joblib`: Pre-trained model for immediate deployment
- `engagement_hackathon.db`: SQLite database (500KB+, populated with sample data)
- `start.sh`: Production-ready startup script with environment validation
- `railway.json`: Deployment configuration for Railway platform

## Technology Stack

- **Backend**: Flask 3.0.0, Python 3.9+
- **ML Stack**: scikit-learn 1.3.0, pandas 2.1.0, numpy 1.24.0, joblib 1.3.2
- **Database**: SQLite with normalized schema
- **Frontend**: HTML5, CSS3, Vanilla JavaScript, Chart.js for visualizations
- **Deployment**: Railway/Render compatible, Gunicorn WSGI server

## Authentication System

Default users (development):
- **superadmin** / admin123 (Super Admin - all access)
- **coordinator1** / coord1 (Program Coordinator - CR101, CS201)
- **coordinator2** / coord2 (Program Coordinator - DS301, AI401)  
- **coordinator3** / coord3 (Program Coordinator - ML501, WEB601)

## API Integration Points

Critical endpoints for ML operations:
- `POST /api/retrain-model`: Rebuilds ML model with current data
- `POST /api/update-predictions`: Bulk updates all learner engagement scores
- `GET /api/learners/{id}`: Retrieve learner details with real-time predictions
- `POST /api/interventions`: Create automated nudges based on ML risk assessment

## Development Context

This is an educational technology platform focused on predicting and improving student engagement. The ML component is the core differentiator - it moves beyond simple rule-based scoring to sophisticated behavioral pattern recognition. When working with this codebase, understand that engagement prediction drives all major features: risk identification, intervention timing, resource allocation, and administrative reporting.

The system is designed for educational institutions to proactively identify at-risk learners and implement targeted interventions before dropout occurs.