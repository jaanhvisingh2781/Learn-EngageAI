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
            # Super admin sees all learners with comprehensive data
            query = """
                SELECT 
                    l.learner_id, l.name, l.email, l.contact, l.country_region, l.work_ex, l.status,
                    c.cohort_id, co.course_id, co.course_name,
                    COUNT(DISTINCT la.login_id) as total_logins,
                    SUM(la.total_duration) as total_login_time,
                    COUNT(DISTINCT ad.assignment_id) as total_assignments,
                    COUNT(DISTINCT CASE WHEN ad.assignment_status = 'Submitted' THEN ad.assignment_id END) as completed_assignments,
                    AVG(ad.assignment_score) as avg_assignment_score,
                    COUNT(DISTINCT qd.quiz_id) as total_quizzes,
                    COUNT(DISTINCT CASE WHEN qd.quiz_status = 'Attempted' THEN qd.quiz_id END) as attempted_quizzes,
                    AVG(qd.quiz_score) as avg_quiz_score,
                    COUNT(DISTINCT ls.session_id) as total_sessions,
                    COUNT(DISTINCT CASE WHEN ls.attendance_status = 'Present' THEN ls.session_id END) as attended_sessions,
                    COUNT(DISTINCT td.ticket_id) as total_tickets,
                    MAX(la.login_time) as last_login
                FROM Learners l 
                LEFT JOIN Cohorts c ON l.cohort_id = c.cohort_id
                LEFT JOIN Courses co ON c.course_id = co.course_id
                LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
                LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
                LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
                LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
                LEFT JOIN Ticket_Details td ON l.learner_id = td.learner_id
                GROUP BY l.learner_id, l.name, l.email, c.cohort_id, co.course_id, co.course_name
                ORDER BY l.name
                LIMIT 100
            """
            cursor.execute(query)
        else:
            # Program coordinator sees only learners from their assigned courses
            placeholders = ','.join('?' * len(user_courses))
            query = f"""
                SELECT 
                    l.learner_id, l.name, l.email, l.contact, l.country_region, l.work_ex, l.status,
                    c.cohort_id, co.course_id, co.course_name,
                    COUNT(DISTINCT la.login_id) as total_logins,
                    SUM(la.total_duration) as total_login_time,
                    COUNT(DISTINCT ad.assignment_id) as total_assignments,
                    COUNT(DISTINCT CASE WHEN ad.assignment_status = 'Submitted' THEN ad.assignment_id END) as completed_assignments,
                    AVG(ad.assignment_score) as avg_assignment_score,
                    COUNT(DISTINCT qd.quiz_id) as total_quizzes,
                    COUNT(DISTINCT CASE WHEN qd.quiz_status = 'Attempted' THEN qd.quiz_id END) as attempted_quizzes,
                    AVG(qd.quiz_score) as avg_quiz_score,
                    COUNT(DISTINCT ls.session_id) as total_sessions,
                    COUNT(DISTINCT CASE WHEN ls.attendance_status = 'Present' THEN ls.session_id END) as attended_sessions,
                    COUNT(DISTINCT td.ticket_id) as total_tickets,
                    MAX(la.login_time) as last_login
                FROM Learners l 
                JOIN Cohorts c ON l.cohort_id = c.cohort_id
                JOIN Courses co ON c.course_id = co.course_id
                LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
                LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
                LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
                LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
                LEFT JOIN Ticket_Details td ON l.learner_id = td.learner_id
                WHERE co.course_id IN ({placeholders})
                GROUP BY l.learner_id, l.name, l.email, c.cohort_id, co.course_id, co.course_name
                ORDER BY l.name
                LIMIT 100
            """
            cursor.execute(query, user_courses)
            
        learners = cursor.fetchall()
        conn.close()
        
        result = []
        for learner in learners:
            # Calculate engagement score based on actual data
            login_score = min((learner['total_login_time'] or 0) / 3600, 10)  # Max 10 points
            assignment_score = (learner['completed_assignments'] or 0) * 5     # 5 points per assignment
            quiz_score = (learner['attempted_quizzes'] or 0) * 3              # 3 points per quiz
            attendance_score = (learner['attended_sessions'] or 0) * 7         # 7 points per session
            
            total_engagement = login_score + assignment_score + quiz_score + attendance_score
            engagement_percentage = min(total_engagement, 100)
            
            # Determine status based on engagement
            if engagement_percentage >= 70:
                status = "On Track"
            elif engagement_percentage >= 40:
                status = "At Risk"
            else:
                status = "Will Drop Off"
                
            # Format last login
            last_active = "Never"
            if learner['last_login']:
                try:
                    from datetime import datetime
                    last_login = datetime.fromisoformat(learner['last_login'])
                    days_ago = (datetime.now() - last_login).days
                    if days_ago == 0:
                        last_active = "Today"
                    elif days_ago == 1:
                        last_active = "Yesterday"
                    else:
                        last_active = f"{days_ago} days ago"
                except:
                    last_active = "Recently"
            
            result.append({
                'id': learner['learner_id'],
                'name': learner['name'],
                'email': learner['email'],
                'contact': learner['contact'],
                'country': learner['country_region'],
                'work_experience': learner['work_ex'],
                'cohort': learner['cohort_id'] or 'N/A',
                'course': learner['course_name'] or 'N/A',
                'course_id': learner['course_id'] or 'N/A',
                'engagement': round(engagement_percentage, 1),
                'status': status,
                'last_active': last_active,
                'stats': {
                    'total_logins': learner['total_logins'] or 0,
                    'total_login_hours': round((learner['total_login_time'] or 0) / 3600, 1),
                    'assignments_completed': f"{learner['completed_assignments'] or 0}/{learner['total_assignments'] or 0}",
                    'avg_assignment_score': round(learner['avg_assignment_score'] or 0, 1),
                    'quizzes_attempted': f"{learner['attempted_quizzes'] or 0}/{learner['total_quizzes'] or 0}",
                    'avg_quiz_score': round(learner['avg_quiz_score'] or 0, 1),
                    'sessions_attended': f"{learner['attended_sessions'] or 0}/{learner['total_sessions'] or 0}",
                    'total_tickets': learner['total_tickets'] or 0
                }
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"API learners error: {e}")
        return jsonify([])

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