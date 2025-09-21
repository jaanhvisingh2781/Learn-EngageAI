from flask import Flask, jsonify, render_template, redirect, url_for
import sqlite3
import os
import random

app = Flask(__name__)
app.secret_key = 'learnengage_secret_key_2024'

def get_db_connection():
    conn = sqlite3.connect('engagement_hackathon.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    # Get stats for dashboard
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM Learners")
        total_learners = cursor.fetchone()['total']
        conn.close()
        
        stats = {
            'total_learners': total_learners,
            'on_track': int(total_learners * 0.6),
            'at_risk': int(total_learners * 0.3),
            'drop_off': int(total_learners * 0.1)
        }
    except:
        stats = {
            'total_learners': 100,
            'on_track': 60,
            'at_risk': 30,
            'drop_off': 10
        }
    
    # Mock trend data for charts
    trend_data = {
        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'average_engagement': [65, 59, 70, 65, 72, 68, 74],
        'at_risk_engagement': [15, 18, 12, 20, 16, 22, 14]
    }
    
    return render_template('dashboard.html', stats=stats, trend_data=trend_data)

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

@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as total FROM Learners")
        total_learners = cursor.fetchone()['total']
        conn.close()
        
        return jsonify({
            'total_learners': total_learners,
            'avg_engagement': 72.5,
            'on_track': int(total_learners * 0.6),
            'at_risk': int(total_learners * 0.3),
            'will_drop': int(total_learners * 0.1)
        })
    except:
        return jsonify({
            'total_learners': 100,
            'avg_engagement': 72.5,
            'on_track': 60,
            'at_risk': 30,
            'will_drop': 10
        })

@app.route('/api/learners')
def api_learners():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT learner_id, name, email FROM Learners LIMIT 50")
        learners = cursor.fetchall()
        conn.close()
        
        result = []
        for learner in learners:
            result.append({
                'id': learner['learner_id'],
                'name': learner['name'],
                'email': learner['email'],
                'cohort': 'C101',
                'engagement': round(random.uniform(40, 95), 1),
                'status': random.choice(['On Track', 'At Risk', 'Will Drop Off']),
                'last_active': f"{random.randint(1, 30)} days ago"
            })
        
        return jsonify(result)
    except:
        return jsonify([{
            'id': 'L001',
            'name': 'Demo Student',
            'email': 'demo@example.com',
            'cohort': 'C101',
            'engagement': 75.0,
            'status': 'On Track',
            'last_active': '2 days ago'
        }])

@app.route('/api/analytics')
def api_analytics():
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
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting LearnEngage AI on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)