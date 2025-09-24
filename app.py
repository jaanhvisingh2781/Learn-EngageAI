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

# Ensure DB exists and tables are created on startup (Render-safe)
try:
    from db import create_tables_if_not_exist
    _conn = get_db_connection()
    _cur = _conn.cursor()
    create_tables_if_not_exist(_cur)
    _conn.commit()
    _conn.close()
except Exception as e:
    print(f"Warning: DB init check failed: {e}")

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

def get_course_names(course_ids):
    """Get course names for given course IDs"""
    if not course_ids:
        return []
    
    conn = get_db_connection()
    cursor = conn.cursor()
    placeholders = ','.join('?' * len(course_ids))
    cursor.execute(f"SELECT course_id, course_name FROM Courses WHERE course_id IN ({placeholders})", course_ids)
    courses = cursor.fetchall()
    conn.close()
    
    return [{'id': course['course_id'], 'name': course['course_name']} for course in courses]

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
    
    # Get REAL stats for dashboard based on user role and actual data
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] == 'Super Admin':
            # Super admin sees all learners with comprehensive stats
            dashboard_query = """
                SELECT 
                    COUNT(DISTINCT l.learner_id) as total_learners,
                    COUNT(DISTINCT c.course_id) as total_courses,
                    COUNT(DISTINCT co.cohort_id) as total_cohorts,
                    SUM(la.total_duration) as total_login_time,
                    COUNT(DISTINCT ad.assignment_id) as total_assignments,
                    COUNT(DISTINCT CASE WHEN ad.assignment_status = 'Submitted' THEN ad.assignment_id END) as completed_assignments,
                    COUNT(DISTINCT qd.quiz_id) as total_quizzes,
                    COUNT(DISTINCT CASE WHEN qd.quiz_status = 'Attempted' THEN qd.quiz_id END) as attempted_quizzes,
                    COUNT(DISTINCT ls.session_id) as total_sessions,
                    COUNT(DISTINCT CASE WHEN ls.attendance_status = 'Present' THEN ls.session_id END) as attended_sessions,
                    COUNT(DISTINCT td.ticket_id) as total_tickets,
                    COUNT(DISTINCT CASE WHEN td.status = 'Resolved' THEN td.ticket_id END) as resolved_tickets
                FROM Learners l
                LEFT JOIN Cohorts co ON l.cohort_id = co.cohort_id
                LEFT JOIN Courses c ON co.course_id = c.course_id
                LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
                LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
                LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
                LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
                LEFT JOIN Ticket_Details td ON l.learner_id = td.learner_id
            """
            cursor.execute(dashboard_query)
        else:
            # Program coordinator sees only their assigned courses data
            placeholders = ','.join('?' * len(user_courses))
            dashboard_query = f"""
                SELECT 
                    COUNT(DISTINCT l.learner_id) as total_learners,
                    COUNT(DISTINCT c.course_id) as total_courses,
                    COUNT(DISTINCT co.cohort_id) as total_cohorts,
                    SUM(la.total_duration) as total_login_time,
                    COUNT(DISTINCT ad.assignment_id) as total_assignments,
                    COUNT(DISTINCT CASE WHEN ad.assignment_status = 'Submitted' THEN ad.assignment_id END) as completed_assignments,
                    COUNT(DISTINCT qd.quiz_id) as total_quizzes,
                    COUNT(DISTINCT CASE WHEN qd.quiz_status = 'Attempted' THEN qd.quiz_id END) as attempted_quizzes,
                    COUNT(DISTINCT ls.session_id) as total_sessions,
                    COUNT(DISTINCT CASE WHEN ls.attendance_status = 'Present' THEN ls.session_id END) as attended_sessions,
                    COUNT(DISTINCT td.ticket_id) as total_tickets,
                    COUNT(DISTINCT CASE WHEN td.status = 'Resolved' THEN td.ticket_id END) as resolved_tickets
                FROM Learners l
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
                LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
                LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
                LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
                LEFT JOIN Ticket_Details td ON l.learner_id = td.learner_id
                WHERE c.course_id IN ({placeholders})
            """
            cursor.execute(dashboard_query, user_courses)
            
        dashboard_data = cursor.fetchone()
        
        # Get engagement distribution for the coordinator's learners
        if user['role'] == 'Super Admin':
            engagement_query = """
                SELECT l.learner_id,
                       COALESCE(SUM(la.total_duration)/3600.0, 0) as login_hours,
                       COALESCE(COUNT(CASE WHEN ad.assignment_status = 'Submitted' THEN 1 END), 0) as completed_assignments,
                       COALESCE(COUNT(CASE WHEN qd.quiz_status = 'Attempted' THEN 1 END), 0) as attempted_quizzes,
                       COALESCE(COUNT(CASE WHEN ls.attendance_status = 'Present' THEN 1 END), 0) as attended_sessions
                FROM Learners l
                LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
                LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
                LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
                LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
                GROUP BY l.learner_id
            """
            cursor.execute(engagement_query)
        else:
            engagement_query = f"""
                SELECT l.learner_id,
                       COALESCE(SUM(la.total_duration)/3600.0, 0) as login_hours,
                       COALESCE(COUNT(CASE WHEN ad.assignment_status = 'Submitted' THEN 1 END), 0) as completed_assignments,
                       COALESCE(COUNT(CASE WHEN qd.quiz_status = 'Attempted' THEN 1 END), 0) as attempted_quizzes,
                       COALESCE(COUNT(CASE WHEN ls.attendance_status = 'Present' THEN 1 END), 0) as attended_sessions
                FROM Learners l
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
                LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
                LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
                LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
                WHERE c.course_id IN ({placeholders})
                GROUP BY l.learner_id
            """
            cursor.execute(engagement_query, user_courses)
        
        learner_engagement = cursor.fetchall()
        
        # Calculate real engagement distribution
        on_track = at_risk = drop_off = 0
        engagement_scores = []
        
        for learner in learner_engagement:
            # Real engagement calculation
            login_score = min(learner['login_hours'], 10)
            assignment_score = learner['completed_assignments'] * 5
            quiz_score = learner['attempted_quizzes'] * 3
            attendance_score = learner['attended_sessions'] * 7
            
            total_engagement = login_score + assignment_score + quiz_score + attendance_score
            engagement_percentage = min(total_engagement, 100)
            engagement_scores.append(engagement_percentage)
            
            if engagement_percentage >= 70:
                on_track += 1
            elif engagement_percentage >= 40:
                at_risk += 1
            else:
                drop_off += 1
        
        conn.close()
        
        # Real statistics
        stats = {
            'total_learners': dashboard_data['total_learners'] or 0,
            'total_courses': dashboard_data['total_courses'] or 0,
            'total_cohorts': dashboard_data['total_cohorts'] or 0,
            'on_track': on_track,
            'at_risk': at_risk,
            'drop_off': drop_off,
            'avg_engagement': round(sum(engagement_scores) / len(engagement_scores), 1) if engagement_scores else 0,
            'total_login_hours': round((dashboard_data['total_login_time'] or 0) / 3600, 1),
            'assignment_completion_rate': round(
                (dashboard_data['completed_assignments'] / dashboard_data['total_assignments'] * 100) 
                if dashboard_data['total_assignments'] else 0, 1
            ),
            'quiz_attempt_rate': round(
                (dashboard_data['attempted_quizzes'] / dashboard_data['total_quizzes'] * 100) 
                if dashboard_data['total_quizzes'] else 0, 1
            ),
            'session_attendance_rate': round(
                (dashboard_data['attended_sessions'] / dashboard_data['total_sessions'] * 100) 
                if dashboard_data['total_sessions'] else 0, 1
            ),
            'ticket_resolution_rate': round(
                (dashboard_data['resolved_tickets'] / dashboard_data['total_tickets'] * 100) 
                if dashboard_data['total_tickets'] else 100, 1
            )
        }
        
        # Real trend data based on daily login activity
        trend_query = """
            SELECT 
                strftime('%w', login_time) as day_of_week,
                AVG(total_duration/3600.0) as avg_daily_hours,
                COUNT(DISTINCT learner_id) as daily_active_users
            FROM Login_Activity 
            WHERE login_time IS NOT NULL
            GROUP BY strftime('%w', login_time)
            ORDER BY day_of_week
        """
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(trend_query)
        trend_raw = cursor.fetchall()
        conn.close()
        
        # Format trend data
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        daily_engagement = [0] * 7
        daily_users = [0] * 7
        
        for row in trend_raw:
            day_idx = int(row['day_of_week'] or 0)
            daily_engagement[day_idx] = round(row['avg_daily_hours'] or 0, 1)
            daily_users[day_idx] = row['daily_active_users'] or 0
            
        trend_data = {
            'labels': days,
            'average_engagement': daily_engagement,
            'at_risk_engagement': [max(0, x-10) for x in daily_engagement],  # Mock at-risk data
            'daily_active_users': daily_users,
            'course_info': {
                'assigned_courses': user_courses,
                'course_names': get_course_names(user_courses) if user_courses else []
            }
        }
        
    except Exception as e:
        print(f"Dashboard error: {e}")
        # Fallback stats
        stats = {
            'total_learners': 0,
            'total_courses': len(user_courses),
            'total_cohorts': 0,
            'on_track': 0,
            'at_risk': 0,
            'drop_off': 0,
            'avg_engagement': 0,
            'total_login_hours': 0,
            'assignment_completion_rate': 0,
            'quiz_attempt_rate': 0,
            'session_attendance_rate': 0,
            'ticket_resolution_rate': 100
        }
        trend_data = {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'average_engagement': [0] * 7,
            'at_risk_engagement': [0] * 7,
            'daily_active_users': [0] * 7,
            'course_info': {
                'assigned_courses': user_courses,
                'course_names': []
            }
        }
    
    return render_template('dashboard.html', stats=stats, trend_data=trend_data, user=user)

@app.route('/learners')
@login_required
def learners():
    user = session['user']
    user_courses = get_user_courses()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get courses accessible to user for filtering
        if user['role'] == 'Super Admin':
            cursor.execute("SELECT course_id, course_name FROM Courses")
        else:
            placeholders = ','.join('?' * len(user_courses))
            cursor.execute(f"SELECT course_id, course_name FROM Courses WHERE course_id IN ({placeholders})", user_courses)
        
        courses = cursor.fetchall()
        
        # Get cohorts for filtering
        if user['role'] == 'Super Admin':
            cursor.execute("SELECT DISTINCT c.cohort_id FROM Cohorts c")
        else:
            placeholders = ','.join('?' * len(user_courses))
            cursor.execute(f"SELECT DISTINCT c.cohort_id FROM Cohorts c WHERE c.course_id IN ({placeholders})", user_courses)
        
        cohorts = cursor.fetchall()
        conn.close()
        
    except Exception as e:
        print(f"Error loading courses/cohorts: {e}")
        courses = []
        cohorts = []
        
    return render_template('learners.html', user=user, courses=courses, cohorts=cohorts)

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
@login_required
def api_dashboard_stats():
    user = session['user']
    user_courses = get_user_courses()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Deterministic counts by engagement thresholds for all roles
        if user['role'] == 'Super Admin':
            query = """
                SELECT 
                    COUNT(*) as total_learners,
                    SUM(CASE WHEN l.total_engagement_score >= 85 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN l.total_engagement_score >= 70 AND l.total_engagement_score < 85 THEN 1 ELSE 0 END) as on_track,
                    SUM(CASE WHEN l.total_engagement_score >= 40 AND l.total_engagement_score < 70 THEN 1 ELSE 0 END) as at_risk,
                    SUM(CASE WHEN l.total_engagement_score < 40 OR l.total_engagement_score IS NULL THEN 1 ELSE 0 END) as will_drop,
                    ROUND(AVG(l.total_engagement_score), 1) as avg_engagement
                FROM Learners l
            """
            cursor.execute(query)
        else:
            placeholders = ','.join('?' * len(user_courses))
            query = f"""
                SELECT 
                    COUNT(*) as total_learners,
                    SUM(CASE WHEN l.total_engagement_score >= 85 THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN l.total_engagement_score >= 70 AND l.total_engagement_score < 85 THEN 1 ELSE 0 END) as on_track,
                    SUM(CASE WHEN l.total_engagement_score >= 40 AND l.total_engagement_score < 70 THEN 1 ELSE 0 END) as at_risk,
                    SUM(CASE WHEN l.total_engagement_score < 40 OR l.total_engagement_score IS NULL THEN 1 ELSE 0 END) as will_drop,
                    ROUND(AVG(l.total_engagement_score), 1) as avg_engagement
                FROM Learners l
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({placeholders})
            """
            cursor.execute(query, user_courses)
            
        result = cursor.fetchone()
        conn.close()
        
        stats = {
            'total_learners': result['total_learners'] or 0,
            'avg_engagement': result['avg_engagement'] or 0,
            'on_track': result['on_track'] or 0,
            'at_risk': result['at_risk'] or 0,
            'will_drop': result['will_drop'] or 0,
            'completed': result['completed'] or 0,
            'user_info': {
                'role': user['role'],
                'courses': user_courses
            }
        }
        return jsonify(stats)
        
    except Exception as e:
        print(f"Dashboard stats API error: {e}")
        return jsonify({
            'total_learners': 0,
            'avg_engagement': 0,
            'on_track': 0,
            'at_risk': 0,
            'will_drop': 0,
            'completed': 0,
            'user_info': {
                'role': user.get('role', 'Unknown'),
                'courses': user_courses
            }
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
            # Super admin sees all learners with accurate aggregated data
            query = """
                SELECT 
                    l.learner_id, l.name, l.email, l.contact, l.country_region, l.work_ex,
                    l.total_engagement_score,
                    c.cohort_id, co.course_id, co.course_name,
                    la.total_logins,
                    la.total_login_time,
                    ad.total_assignments,
                    ad.completed_assignments,
                    ad.avg_assignment_score,
                    qd.total_quizzes,
                    qd.attempted_quizzes,
                    qd.avg_quiz_score,
                    ls.total_sessions,
                    ls.attended_sessions,
                    td.total_tickets,
                    la.last_login
                FROM Learners l 
                LEFT JOIN Cohorts c ON l.cohort_id = c.cohort_id
                LEFT JOIN Courses co ON c.course_id = co.course_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT login_id) as total_logins,
                           SUM(total_duration) as total_login_time,
                           MAX(login_time) as last_login
                    FROM Login_Activity
                    GROUP BY learner_id
                ) la ON l.learner_id = la.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT assignment_id) as total_assignments,
                           COUNT(DISTINCT CASE WHEN assignment_status = 'Submitted' THEN assignment_id END) as completed_assignments,
                           AVG(assignment_score) as avg_assignment_score
                    FROM Assignment_Details
                    GROUP BY learner_id
                ) ad ON l.learner_id = ad.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT quiz_id) as total_quizzes,
                           COUNT(DISTINCT CASE WHEN quiz_status = 'Attempted' THEN quiz_id END) as attempted_quizzes,
                           AVG(quiz_score) as avg_quiz_score
                    FROM Quiz_Details
                    GROUP BY learner_id
                ) qd ON l.learner_id = qd.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT session_id) as total_sessions,
                           COUNT(DISTINCT CASE WHEN attendance_status = 'Present' THEN session_id END) as attended_sessions
                    FROM Live_Session
                    GROUP BY learner_id
                ) ls ON l.learner_id = ls.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT ticket_id) as total_tickets
                    FROM Ticket_Details
                    GROUP BY learner_id
                ) td ON l.learner_id = td.learner_id
                ORDER BY l.name
            """
            cursor.execute(query)
        else:
            # Program coordinator sees only learners from their assigned courses (accurate aggregates)
            placeholders = ','.join('?' * len(user_courses))
            query = f"""
                SELECT 
                    l.learner_id, l.name, l.email, l.contact, l.country_region, l.work_ex,
                    l.total_engagement_score,
                    c.cohort_id, co.course_id, co.course_name,
                    la.total_logins,
                    la.total_login_time,
                    ad.total_assignments,
                    ad.completed_assignments,
                    ad.avg_assignment_score,
                    qd.total_quizzes,
                    qd.attempted_quizzes,
                    qd.avg_quiz_score,
                    ls.total_sessions,
                    ls.attended_sessions,
                    td.total_tickets,
                    la.last_login
                FROM Learners l 
                JOIN Cohorts c ON l.cohort_id = c.cohort_id
                JOIN Courses co ON c.course_id = co.course_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT login_id) as total_logins,
                           SUM(total_duration) as total_login_time,
                           MAX(login_time) as last_login
                    FROM Login_Activity
                    GROUP BY learner_id
                ) la ON l.learner_id = la.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT assignment_id) as total_assignments,
                           COUNT(DISTINCT CASE WHEN assignment_status = 'Submitted' THEN assignment_id END) as completed_assignments,
                           AVG(assignment_score) as avg_assignment_score
                    FROM Assignment_Details
                    GROUP BY learner_id
                ) ad ON l.learner_id = ad.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT quiz_id) as total_quizzes,
                           COUNT(DISTINCT CASE WHEN quiz_status = 'Attempted' THEN quiz_id END) as attempted_quizzes,
                           AVG(quiz_score) as avg_quiz_score
                    FROM Quiz_Details
                    GROUP BY learner_id
                ) qd ON l.learner_id = qd.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT session_id) as total_sessions,
                           COUNT(DISTINCT CASE WHEN attendance_status = 'Present' THEN session_id END) as attended_sessions
                    FROM Live_Session
                    GROUP BY learner_id
                ) ls ON l.learner_id = ls.learner_id
                LEFT JOIN (
                    SELECT learner_id,
                           COUNT(DISTINCT ticket_id) as total_tickets
                    FROM Ticket_Details
                    GROUP BY learner_id
                ) td ON l.learner_id = td.learner_id
                WHERE co.course_id IN ({placeholders})
                ORDER BY l.name
            """
            cursor.execute(query, user_courses)
            
        learners = cursor.fetchall()
        conn.close()
        
        result = []
        for learner in learners:
            # Use the stored engagement score consistently
            engagement_percentage = round(learner['total_engagement_score'] or 0, 1)
            
            # Deterministic status banding so Admin/Coordinators see consistent counts
            if engagement_percentage >= 85:
                status = "Completed"
            elif engagement_percentage >= 70:
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
            
            # Progress scaled from engagement
            progress_percentage = min(engagement_percentage * 0.8 + 20, 100)
            
            # Map status to risk level
            if status == 'On Track' or status == 'Completed':
                risk_level = 'low'
            elif status == 'At Risk':
                risk_level = 'medium'
            else:
                risk_level = 'high'
            
            result.append({
                'id': learner['learner_id'],
                'name': learner['name'],
                'email': learner['email'],
                'contact': learner['contact'],
                'country': learner['country_region'],
                'work_experience': learner['work_ex'],
                'cohort': learner['cohort_id'] or 'N/A',
                'course': learner['course_name'] or 'N/A',
                'course_name': learner['course_name'] or 'N/A',
                'course_id': learner['course_id'] or 'N/A',
                'engagement': engagement_percentage,
                'progress': round(progress_percentage, 1),
                'status': status,
                'risk_level': risk_level,
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
@login_required
def api_analytics():
    user = session['user']
    user_courses = get_user_courses()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Build query based on user role
        if user['role'] == 'Super Admin':
            base_filter = ""
            params = []
        else:
            placeholders = ','.join('?' * len(user_courses))
            base_filter = f"""
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({placeholders})
            """
            params = user_courses
        
        # Get comprehensive analytics
        analytics_query = f"""
            SELECT 
                COUNT(DISTINCT l.learner_id) as total_learners,
                COUNT(DISTINCT ad.assignment_id) as total_assignments,
                COUNT(DISTINCT CASE WHEN ad.assignment_status = 'Submitted' THEN ad.assignment_id END) as completed_assignments,
                AVG(ad.assignment_score) as avg_assignment_score,
                COUNT(DISTINCT qd.quiz_id) as total_quizzes,
                COUNT(DISTINCT CASE WHEN qd.quiz_status = 'Attempted' THEN qd.quiz_id END) as attempted_quizzes,
                AVG(qd.quiz_score) as avg_quiz_score,
                COUNT(DISTINCT ls.session_id) as total_sessions,
                COUNT(DISTINCT CASE WHEN ls.attendance_status = 'Present' THEN ls.session_id END) as attended_sessions,
                SUM(la.total_duration) as total_login_time,
                COUNT(DISTINCT la.login_id) as total_logins
            FROM Learners l
            {base_filter}
            LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
            LEFT JOIN Assignment_Details ad ON l.learner_id = ad.learner_id
            LEFT JOIN Quiz_Details qd ON l.learner_id = qd.learner_id
            LEFT JOIN Live_Session ls ON l.learner_id = ls.learner_id
        """
        
        cursor.execute(analytics_query, params)
        analytics = cursor.fetchone()
        
        # Get simplified engagement distribution
        engagement_query = f"""
            SELECT 
                'On Track' as status,
                COUNT(*) as count
            FROM Learners l
            {base_filter}
            WHERE l.total_engagement_score >= 70
            UNION ALL
            SELECT 
                'At Risk' as status,
                COUNT(*) as count
            FROM Learners l
            {base_filter}
            WHERE l.total_engagement_score >= 40 AND l.total_engagement_score < 70
            UNION ALL
            SELECT 
                'Will Drop Off' as status,
                COUNT(*) as count
            FROM Learners l
            {base_filter}
            WHERE l.total_engagement_score < 40 OR l.total_engagement_score IS NULL
        """
        
        # Execute queries with correct parameters for each UNION
        if user['role'] == 'Super Admin':
            cursor.execute(engagement_query.replace(base_filter, ''))
        else:
            # For coordinators, need to execute the full query with proper JOIN conditions
            full_engagement_query = f"""
                SELECT 
                    'On Track' as status,
                    COUNT(*) as count
                FROM Learners l
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({','.join('?' * len(user_courses))}) AND l.total_engagement_score >= 70
                UNION ALL
                SELECT 
                    'At Risk' as status,
                    COUNT(*) as count
                FROM Learners l
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({','.join('?' * len(user_courses))}) AND l.total_engagement_score >= 40 AND l.total_engagement_score < 70
                UNION ALL
                SELECT 
                    'Will Drop Off' as status,
                    COUNT(*) as count
                FROM Learners l
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({','.join('?' * len(user_courses))}) AND (l.total_engagement_score < 40 OR l.total_engagement_score IS NULL)
            """
            cursor.execute(full_engagement_query, user_courses + user_courses + user_courses)
            
        engagement_data = cursor.fetchall()
        
        # Get daily activity trends
        trend_query = f"""
            SELECT 
                strftime('%w', la.login_time) as day_of_week,
                AVG(la.total_duration/3600.0) as avg_hours
            FROM Learners l
            {base_filter}
            LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
            WHERE la.login_time IS NOT NULL
            GROUP BY strftime('%w', la.login_time)
            ORDER BY day_of_week
        """
        
        cursor.execute(trend_query, params)
        trend_data = cursor.fetchall()
        
        conn.close()
        
        # Process results
        completion_rate = round((analytics['completed_assignments'] / analytics['total_assignments'] * 100) if analytics['total_assignments'] else 0, 1)
        quiz_attempt_rate = round((analytics['attempted_quizzes'] / analytics['total_quizzes'] * 100) if analytics['total_quizzes'] else 0, 1)
        attendance_rate = round((analytics['attended_sessions'] / analytics['total_sessions'] * 100) if analytics['total_sessions'] else 0, 1)
        avg_engagement = round((analytics['avg_assignment_score'] or 0 + analytics['avg_quiz_score'] or 0) / 2, 1)
        
        # Format engagement distribution
        status_counts = {'On Track': 0, 'At Risk': 0, 'Will Drop Off': 0}
        for row in engagement_data:
            status_counts[row['status']] += row['count']
        
        # Format trend data
        days = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
        daily_engagement = [0] * 7
        for row in trend_data:
            if row['day_of_week'] is not None:
                daily_engagement[int(row['day_of_week'])] = round(row['avg_hours'] or 0, 1)
        
        return jsonify({
            'total_learners': analytics['total_learners'] or 0,
            'avg_engagement': avg_engagement,
            'completion_rate': completion_rate,
            'quiz_attempt_rate': quiz_attempt_rate,
            'attendance_rate': attendance_rate,
            'total_login_hours': round((analytics['total_login_time'] or 0) / 3600, 1),
            'engagement_distribution': {
                'labels': ['On Track', 'At Risk', 'Will Drop Off'],
                'values': [status_counts['On Track'], status_counts['At Risk'], status_counts['Will Drop Off']]
            },
            'engagement_by_day': {
                'labels': days,
                'values': daily_engagement
            },
            'activity_distribution': {
                'labels': ['Login Hours', 'Assignments', 'Quizzes', 'Sessions'],
                'values': [
                    round((analytics['total_login_time'] or 0) / 3600, 1),
                    analytics['completed_assignments'] or 0,
                    analytics['attempted_quizzes'] or 0,
                    analytics['attended_sessions'] or 0
                ]
            }
        })
        
    except Exception as e:
        print(f"Analytics API error: {e}")
        return jsonify({
            'total_learners': 0,
            'avg_engagement': 0,
            'completion_rate': 0,
            'quiz_attempt_rate': 0,
            'attendance_rate': 0,
            'total_login_hours': 0,
            'engagement_distribution': {'labels': [], 'values': []},
            'engagement_by_day': {'labels': days, 'values': [0] * 7},
            'activity_distribution': {'labels': [], 'values': []}
        })
# API endpoint for tickets
@app.route('/api/tickets')
@login_required
def api_tickets():
    user = session['user']
    user_courses = get_user_courses()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] == 'Super Admin':
            query = """
                SELECT t.ticket_id, t.subject, t.description, t.priority, t.status, 
                       t.created_at, t.resolved_at, t.feedback, t.satisfied,
                       l.name as learner_name, l.email as learner_email,
                       c.course_name
                FROM Ticket_Details t
                JOIN Learners l ON t.learner_id = l.learner_id
                LEFT JOIN Cohorts co ON l.cohort_id = co.cohort_id
                LEFT JOIN Courses c ON co.course_id = c.course_id
                ORDER BY t.created_at DESC
                LIMIT 100
            """
            cursor.execute(query)
        else:
            placeholders = ','.join('?' * len(user_courses))
            query = f"""
                SELECT t.ticket_id, t.subject, t.description, t.priority, t.status, 
                       t.created_at, t.resolved_at, t.feedback, t.satisfied,
                       l.name as learner_name, l.email as learner_email,
                       c.course_name
                FROM Ticket_Details t
                JOIN Learners l ON t.learner_id = l.learner_id
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({placeholders})
                ORDER BY t.created_at DESC
                LIMIT 100
            """
            cursor.execute(query, user_courses)
            
        tickets = cursor.fetchall()
        conn.close()
        
        result = []
        for ticket in tickets:
            result.append({
                'id': ticket['ticket_id'],
                'subject': ticket['subject'],
                'description': ticket['description'],
                'priority': ticket['priority'],
                'status': ticket['status'],
                'created_at': ticket['created_at'],
                'resolved_at': ticket['resolved_at'],
                'learner_name': ticket['learner_name'],
                'learner_email': ticket['learner_email'],
                'course': ticket['course_name'] or 'N/A',
                'feedback': ticket['feedback'],
                'satisfied': ticket['satisfied']
            })
            
        return jsonify(result)
        
    except Exception as e:
        print(f"Tickets API error: {e}")
        return jsonify([])

# API endpoint for interventions/nudges
@app.route('/api/interventions')
@login_required
def api_interventions():
    user = session['user']
    user_courses = get_user_courses()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        if user['role'] == 'Super Admin':
            query = """
                SELECT n.nudge_id, n.nudge_type, n.message, n.timestamp, n.status, n.channel,
                       l.name as learner_name, l.email as learner_email,
                       c.course_name
                FROM Nudge_Logs n
                JOIN Learners l ON n.learner_id = l.learner_id
                LEFT JOIN Cohorts co ON l.cohort_id = co.cohort_id
                LEFT JOIN Courses c ON co.course_id = c.course_id
                ORDER BY n.timestamp DESC
                LIMIT 100
            """
            cursor.execute(query)
        else:
            placeholders = ','.join('?' * len(user_courses))
            query = f"""
                SELECT n.nudge_id, n.nudge_type, n.message, n.timestamp, n.status, n.channel,
                       l.name as learner_name, l.email as learner_email,
                       c.course_name
                FROM Nudge_Logs n
                JOIN Learners l ON n.learner_id = l.learner_id
                JOIN Cohorts co ON l.cohort_id = co.cohort_id
                JOIN Courses c ON co.course_id = c.course_id
                WHERE c.course_id IN ({placeholders})
                ORDER BY n.timestamp DESC
                LIMIT 100
            """
            cursor.execute(query, user_courses)
            
        interventions = cursor.fetchall()
        conn.close()
        
        result = []
        for intervention in interventions:
            result.append({
                'id': intervention['nudge_id'],
                'type': intervention['nudge_type'],
                'message': intervention['message'],
                'timestamp': intervention['timestamp'],
                'status': intervention['status'],
                'channel': intervention['channel'],
                'learner_name': intervention['learner_name'],
                'learner_email': intervention['learner_email'],
                'course': intervention['course_name'] or 'N/A'
            })
            
        return jsonify(result)
        
    except Exception as e:
        print(f"Interventions API error: {e}")
        return jsonify([])

# API endpoint for monthly engagement trends
@app.route('/api/monthly-engagement')
@login_required
def api_monthly_engagement():
    user = session['user']
    user_courses = get_user_courses()
    
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Optional date range filters: start=YYYY-MM, end=YYYY-MM
        from datetime import datetime
        start_param = request.args.get('start')  # e.g., '2025-01'
        end_param = request.args.get('end')      # e.g., '2025-12'
        
        if start_param and end_param:
            start_clause = " AND strftime('%Y-%m', la.login_time) >= ? AND strftime('%Y-%m', la.login_time) <= ?"
            range_params = [start_param, end_param]
        else:
            start_clause = " AND strftime('%Y-%m', la.login_time) >= strftime('%Y-%m', 'now', '-11 months')"
            range_params = []
        
        if user['role'] == 'Super Admin':
            query = f"""
                SELECT 
                    strftime('%Y-%m', la.login_time) as month,
                    AVG(la.total_duration/3600.0) as avg_monthly_hours,
                    COUNT(DISTINCT l.learner_id) as monthly_active_users,
                    AVG(l.total_engagement_score) as avg_engagement_score
                FROM Login_Activity la
                LEFT JOIN Learners l ON la.learner_id = l.learner_id
                WHERE la.login_time IS NOT NULL
                    {start_clause}
                GROUP BY strftime('%Y-%m', la.login_time)
                ORDER BY month
            """
            cursor.execute(query, range_params)
        else:
            placeholders = ','.join('?' * len(user_courses))
            query = f"""
                SELECT 
                    strftime('%Y-%m', la.login_time) as month,
                    AVG(la.total_duration/3600.0) as avg_monthly_hours,
                    COUNT(DISTINCT l.learner_id) as monthly_active_users,
                    AVG(l.total_engagement_score) as avg_engagement_score
                FROM Login_Activity la
                LEFT JOIN Learners l ON la.learner_id = l.learner_id
                LEFT JOIN Cohorts co ON l.cohort_id = co.cohort_id
                LEFT JOIN Courses c ON co.course_id = c.course_id
                WHERE la.login_time IS NOT NULL
                    AND c.course_id IN ({placeholders})
                    {start_clause}
                GROUP BY strftime('%Y-%m', la.login_time)
                ORDER BY month
            """
            cursor.execute(query, user_courses + range_params)
            
        monthly_data = cursor.fetchall()
        conn.close()
        
        # Format data for Chart.js
        from datetime import datetime, timedelta
        
        # Create last 12 months labels or range labels
        if start_param and end_param:
            # Build month keys between start and end inclusive
            start_date = datetime.strptime(start_param + '-01', '%Y-%m-%d')
            end_date = datetime.strptime(end_param + '-01', '%Y-%m-%d')
            months_data = {}
            month_labels = []
            month_keys_order = []
            cur = start_date
            while cur <= end_date:
                key = cur.strftime('%Y-%m')
                label = cur.strftime('%b %Y')
                month_labels.append(label)
                month_keys_order.append(key)
                months_data[key] = {'engagement': 0, 'at_risk_engagement': 0, 'active_users': 0}
                # increment month
                if cur.month == 12:
                    cur = cur.replace(year=cur.year+1, month=1)
                else:
                    cur = cur.replace(month=cur.month+1)
        else:
            current_date = datetime.now()
            months_data = {}
            month_labels = []
            month_keys_order = []
            for i in range(11, -1, -1):
                month_date = current_date.replace(day=1) - timedelta(days=32*i)
                month_key = month_date.strftime('%Y-%m')
                month_label = month_date.strftime('%b %Y')
                month_labels.append(month_label)
                month_keys_order.append(month_key)
                months_data[month_key] = {'engagement': 0, 'at_risk_engagement': 0, 'active_users': 0}
        
        # Fill in actual data
        for row in monthly_data:
            if row['month'] in months_data:
                months_data[row['month']] = {
                    'engagement': round(row['avg_engagement_score'] or 0, 1),
                    'at_risk_engagement': round(max(0, (row['avg_engagement_score'] or 0) - 20), 1),
                    'active_users': row['monthly_active_users'] or 0
                }
        
        # Extract values in the same order as labels to avoid misalignment
        engagement_values = [months_data[key]['engagement'] for key in month_keys_order]
        at_risk_values = [months_data[key]['at_risk_engagement'] for key in month_keys_order]
        active_users_values = [months_data[key]['active_users'] for key in month_keys_order]
        
        return jsonify({
            'labels': month_labels,
            'engagement_data': engagement_values,
            'at_risk_data': at_risk_values,
            'active_users_data': active_users_values
        })
        
    except Exception as e:
        print(f"Monthly engagement API error: {e}")
        # Return empty 12-month data
        from datetime import datetime, timedelta
        current_date = datetime.now()
        month_labels = []
        for i in range(11, -1, -1):
            month_date = current_date.replace(day=1) - timedelta(days=32*i)
            month_labels.append(month_date.strftime('%b %Y'))
        
        return jsonify({
            'labels': month_labels,
            'engagement_data': [0] * 12,
            'at_risk_data': [0] * 12,
            'active_users_data': [0] * 12
        })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting LearnEngage AI on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
