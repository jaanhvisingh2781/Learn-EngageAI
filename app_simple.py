# Simple Flask app for deployment without heavy ML dependencies
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import sqlite3
import os
from datetime import datetime, timedelta
import json
import random

app = Flask(__name__)
app.secret_key = 'learnengage_secret_key_2024'

# Database connection helper function
def get_db_connection():
    conn = sqlite3.connect('engagement_hackathon.db')
    conn.row_factory = sqlite3.Row
    return conn

# Simple engagement calculation without ML
def calculate_engagement_score_simple(learner_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get login activity
        cursor.execute("SELECT total_duration FROM Login_Activity WHERE learner_id=?", (learner_id,))
        login_data = cursor.fetchall()
        total_login_time = sum([row['total_duration'] for row in login_data]) if login_data else 0
        
        # Get assignment submissions
        cursor.execute("SELECT COUNT(*) FROM Assignment_Details WHERE learner_id=? AND assignment_status='Submitted'", (learner_id,))
        submitted_assignments = cursor.fetchone()[0]
        
        # Get quiz attempts
        cursor.execute("SELECT COUNT(*) FROM Quiz_Details WHERE learner_id=? AND quiz_status='Attempted'", (learner_id,))
        attempted_quizzes = cursor.fetchone()[0]
        
        # Get live session attendance
        cursor.execute("SELECT COUNT(*) FROM Live_Session WHERE learner_id=? AND attendance_status='Present'", (learner_id,))
        attended_sessions = cursor.fetchone()[0]
        
        # Simple scoring algorithm
        login_score = min(total_login_time / 3600, 10)  # 1 point per hour, max 10
        assignment_score = submitted_assignments * 5    # 5 points per submission
        quiz_score = attempted_quizzes * 3              # 3 points per quiz
        attendance_score = attended_sessions * 7        # 7 points per session
        
        total_score = login_score + assignment_score + quiz_score + attendance_score
        max_possible = 10 + (5 * 5) + (3 * 5) + (7 * 5)  # Example max possible
        
        engagement_percentage = (total_score / max_possible) * 100 if max_possible > 0 else 0
        
        return min(engagement_percentage, 100)  # Cap at 100%
    except Exception as e:
        print(f"Error calculating engagement: {e}")
        return 50  # Default score
    finally:
        conn.close()

# Simple status prediction
def predict_status_simple(engagement_score):
    if engagement_score >= 70:
        return "On Track"
    elif engagement_score >= 40:
        return "At Risk"
    else:
        return "Will Drop Off"

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/learners')
def learners():
    return render_template('learners.html')

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/interventions')
def interventions():
    return render_template('interventions.html')

@app.route('/tickets')
def tickets():
    return render_template('tickets.html')

# API Routes
@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get basic stats
        cursor.execute("SELECT COUNT(*) as total FROM Learners")
        total_learners = cursor.fetchone()['total']
        
        # Mock engagement stats
        stats = {
            'total_learners': total_learners,
            'avg_engagement': round(random.uniform(60, 80), 1),
            'on_track': random.randint(int(total_learners * 0.4), int(total_learners * 0.7)),
            'at_risk': random.randint(int(total_learners * 0.2), int(total_learners * 0.4)),
            'will_drop': random.randint(1, int(total_learners * 0.2))
        }
        
        return jsonify(stats)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/learners')
def api_learners():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT l.learner_id, l.name, l.email, c.cohort_id as cohort
            FROM Learners l
            LEFT JOIN Cohorts c ON l.cohort_id = c.cohort_id
            ORDER BY l.name
        """)
        
        learners = cursor.fetchall()
        result = []
        
        for learner in learners:
            engagement_score = calculate_engagement_score_simple(learner['learner_id'])
            status = predict_status_simple(engagement_score)
            
            result.append({
                'id': learner['learner_id'],
                'name': learner['name'],
                'email': learner['email'],
                'cohort': learner['cohort'] or 'N/A',
                'engagement': round(engagement_score, 1),
                'status': status,
                'last_active': f"{random.randint(1, 30)} days ago"
            })
        
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.route('/api/analytics')
def api_analytics():
    # Mock analytics data
    return jsonify({
        'avg_engagement': 72.5,
        'completion_rate': 68.2,
        'retention_rate': 85.7,
        'engagement_trend': 5.2,
        'engagement_by_day': {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'values': [65, 59, 70, 65, 72, 68, 74]
        },
        'activity_distribution': {
            'labels': ['Login', 'Assignments', 'Quizzes', 'Sessions'],
            'values': [35, 25, 20, 20]
        }
    })

if __name__ == '__main__':
    # Get port from environment variable (for Render deployment)
    port = int(os.environ.get('PORT', 5000))
    
    # Initialize database
    try:
        # Simple database check
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM Learners")
        count = cursor.fetchone()[0]
        print(f"Database ready with {count} learners")
        conn.close()
    except Exception as e:
        print(f"Database initialization warning: {e}")
    
    # Run the app
    print(f"Starting LearnEngage AI on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)