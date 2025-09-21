from flask import Flask, jsonify, render_template, redirect, url_for, request, session, flash
import sqlite3
import os
import random
import hashlib

app = Flask(__name__)
app.secret_key = 'learnengage_secret_key_2024'

def get_db_connection():
    conn = sqlite3.connect('engagement_hackathon.db')
    conn.row_factory = sqlite3.Row
    return conn

# Authentication functions
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def authenticate_user(username, password):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM Users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()
    
    if user and user['password_hash'] == hash_password(password):
        return {
            'user_id': user['user_id'],
            'username': user['username'],
            'role': user['role'],
            'assigned_courses': user['assigned_courses']
        }
    return None

def login_required(f):
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

def get_user_courses():
    """Get courses accessible to current user"""
    if 'user' not in session:
        return []
    
    user = session['user']
    if user['role'] == 'Super Admin' or user['assigned_courses'] == 'ALL':
        # Super admin can see all courses
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT course_id FROM Courses")
        courses = [row['course_id'] for row in cursor.fetchall()]
        conn.close()
        return courses
    else:
        # Program coordinator can only see assigned courses
        return user['assigned_courses'].split(',')

@app.route('/')
def index():
    if 'user' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        user = authenticate_user(username, password)
        if user:
            session['user'] = user
            flash(f'Welcome {user["username"]}! You are logged in as {user["role"]}.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password!', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    username = session.get('user', {}).get('username', 'User')
    session.pop('user', None)
    flash(f'Goodbye {username}! You have been logged out successfully.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    user = session['user']
    user_courses = get_user_courses()
    
    # Get stats for dashboard based on user role
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] == 'Super Admin':
            # Super admin sees all learners
            cursor.execute("SELECT COUNT(*) as total FROM Learners")
        else:
            # Program coordinator sees only learners from their assigned courses
            placeholders = ','.join('?' * len(user_courses))
            cursor.execute(f"""
                SELECT COUNT(*) as total 
                FROM Learners l 
                JOIN Cohorts c ON l.cohort_id = c.cohort_id 
                WHERE c.course_id IN ({placeholders})
            """, user_courses)
            
        total_learners = cursor.fetchone()['total']
        conn.close()
        
        stats = {
            'total_learners': total_learners,
            'on_track': int(total_learners * 0.6),
            'at_risk': int(total_learners * 0.3),
            'drop_off': int(total_learners * 0.1)
        }
    except Exception as e:
        print(f"Dashboard error: {e}")
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
    
    return render_template('dashboard.html', stats=stats, trend_data=trend_data, user=user)

@app.route('/learners')
@login_required
def learners():
    user = session['user']
    return render_template('learners.html', user=user)

@app.route('/analytics')
@login_required
def analytics():
    user = session['user']
    return render_template('analytics.html', user=user)

@app.route('/interventions')
@login_required
def interventions():
    user = session['user']
    return render_template('interventions.html', user=user)

@app.route('/tickets')
@login_required
def tickets():
    user = session['user']
    return render_template('tickets.html', user=user)

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
@login_required
def api_learners():
    try:
        user = session['user']
        user_courses = get_user_courses()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] == 'Super Admin':
            # Super admin sees all learners
            cursor.execute("""
                SELECT l.learner_id, l.name, l.email, c.cohort_id, co.course_id
                FROM Learners l 
                LEFT JOIN Cohorts c ON l.cohort_id = c.cohort_id
                LEFT JOIN Courses co ON c.course_id = co.course_id
                LIMIT 100
            """)
        else:
            # Program coordinator sees only learners from their assigned courses
            placeholders = ','.join('?' * len(user_courses))
            cursor.execute(f"""
                SELECT l.learner_id, l.name, l.email, c.cohort_id, co.course_id
                FROM Learners l 
                JOIN Cohorts c ON l.cohort_id = c.cohort_id
                JOIN Courses co ON c.course_id = co.course_id
                WHERE co.course_id IN ({placeholders})
                LIMIT 100
            """, user_courses)
            
        learners = cursor.fetchall()
        conn.close()
        
        result = []
        for learner in learners:
            result.append({
                'id': learner['learner_id'],
                'name': learner['name'],
                'email': learner['email'],
                'cohort': learner['cohort_id'] or 'N/A',
                'course': learner['course_id'] or 'N/A',
                'engagement': round(random.uniform(40, 95), 1),
                'status': random.choice(['On Track', 'At Risk', 'Will Drop Off']),
                'last_active': f"{random.randint(1, 30)} days ago"
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"API learners error: {e}")
        return jsonify([{
            'id': 'L001',
            'name': 'Demo Student',
            'email': 'demo@example.com',
            'cohort': 'C101',
            'course': user_courses[0] if user_courses else 'N/A',
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