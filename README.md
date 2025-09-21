# LearnEngage AI

AI-powered learner engagement prediction system that helps educational institutions monitor and predict student engagement levels using machine learning algorithms.

## Features

- **Dashboard**: Real-time overview of learner statistics and engagement metrics
- **Learner Management**: Comprehensive learner profiles with engagement scoring
- **Predictive Analytics**: ML-powered engagement prediction and risk assessment
- **Intervention System**: Automated nudging and support ticket management
- **Analytics**: Detailed reports on learner behavior and course performance

## Technology Stack

- **Backend**: Flask (Python)
- **Machine Learning**: Scikit-learn, Pandas, NumPy
- **Database**: SQLite
- **Frontend**: HTML, CSS, JavaScript (with Chart.js for visualizations)
- **Deployment**: Render

## Local Development

1. Clone the repository:
```bash
git clone <repository-url>
cd learnengageAI-main
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Initialize the database:
```bash
python db.py
```

4. Run the application:
```bash
python app.py
```

The application will be available at `http://localhost:5000`

## Deployment

This application is configured for deployment on Render. The deployment process includes:

1. Automatic dependency installation via `requirements.txt`
2. Database initialization via `build.sh` script
3. Production-ready Flask configuration

## Project Structure

```
learnengageAI-main/
├── app.py                 # Main Flask application
├── db.py                  # Database setup and data generation
├── engagement_predictor.py # ML model for engagement prediction
├── templates/             # HTML templates
├── static/               # Static files (CSS, JS)
├── requirements.txt      # Python dependencies
├── build.sh             # Build script for deployment
├── package.json         # Node.js configuration
└── README.md           # Project documentation
```

## API Endpoints

- `/dashboard` - Main dashboard
- `/learners` - Learner management
- `/analytics` - Analytics dashboard
- `/interventions` - Intervention management
- `/tickets` - Support ticket system
- `/api/*` - REST API endpoints for data

## License

This project is licensed under the MIT License.