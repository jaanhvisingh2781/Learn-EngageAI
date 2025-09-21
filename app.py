# app.py (Enhanced version)
from flask import Flask, jsonify, request, render_template, session, redirect, url_for
import sqlite3
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import numpy as np
from datetime import datetime, timedelta
import json
import re
import traceback
from engagement_predictor import EngagementPredictor
import joblib
import os


app = Flask(__name__)
app.secret_key = 'your_secret_key_here'  # Needed for session management

# Database connection helper function
def get_db_connection():
    conn = sqlite3.connect('engagement_hackathon.db')
    conn.row_factory = sqlite3.Row  # This enables column access by name
    return conn

# Add to your imports
from engagement_predictor import EngagementPredictor
import joblib
import os

# Initialize the predictor
predictor = EngagementPredictor()
MODEL_PATH = 'engagement_model.joblib'

# Check if model exists, otherwise train it
def initialize_model():
    conn = get_db_connection()
    try:
        if os.path.exists(MODEL_PATH):
            predictor.load_model(MODEL_PATH)
            print("Loaded pre-trained model")
        else:
            print("Training new model...")
            mae, r2 = predictor.train_model(conn)
            predictor.save_model(MODEL_PATH)
            print(f"Model trained and saved with MAE: {mae:.2f}, R²: {r2:.2f}")
    except Exception as e:
        print(f"Error initializing model: {e}")
    finally:
        conn.close()

# Update the calculate_engagement_score function
def calculate_engagement_score(learner_id):
    conn = get_db_connection()
    try:
        # Use ML model for prediction
        engagement_score = predictor.predict_engagement(learner_id, conn)
        return engagement_score
    except Exception as e:
        print(f"Error predicting engagement score: {e}")
        # Fallback to rule-based approach
        return calculate_engagement_score_fallback(learner_id)
    finally:
        conn.close()

# Keep the fallback function as backup
def calculate_engagement_score_fallback(learner_id):
    # Your original rule-based implementation here
    conn = get_db_connection()
    cursor = conn.cursor()
    
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
    
    # Calculate score (simplified for demo)
    login_score = min(total_login_time / 3600, 10)  # 1 point per hour, max 10
    assignment_score = submitted_assignments * 5    # 5 points per submission
    quiz_score = attempted_quizzes * 3              # 3 points per quiz
    attendance_score = attended_sessions * 7        # 7 points per session
    
    total_score = login_score + assignment_score + quiz_score + attendance_score
    max_possible = 10 + (5 * 5) + (3 * 5) + (7 * 5)  # Example max possible
    
    engagement_percentage = (total_score / max_possible) * 100
    
    conn.close()
    
    return min(engagement_percentage, 100)  # Cap at 100%

# Update the predict_learner_status function
def predict_learner_status(learner_id):
    engagement_score = calculate_engagement_score(learner_id)
    status = predictor.predict_status(engagement_score)
    return status, engagement_score

# Add API endpoint to retrain model
@app.route('/api/retrain-model', methods=['POST'])
def api_retrain_model():
    try:
        conn = get_db_connection()
        mae, r2 = predictor.train_model(conn)
        predictor.save_model(MODEL_PATH)
        conn.close()
        
        return jsonify({
            'success': True, 
            'message': f'Model retrained successfully with MAE: {mae:.2f}, R²: {r2:.2f}'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error retraining model: {str(e)}'
        })

# Initialize the model when the app starts
initialize_model()

def update_all_predictions():
    """Update engagement predictions for all learners"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get all learners
    cursor.execute("SELECT learner_id FROM Learners")
    learners = cursor.fetchall()
    
    updated_count = 0
    for learner in learners:
        learner_id = learner['learner_id']
        
        # Predict engagement and status
        status, engagement_score = predict_learner_status(learner_id)
        
        # Update database
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cursor.execute("""
            UPDATE Learners 
            SET total_engagement_score = ?, status = ?, prediction_timestamp = ?
            WHERE learner_id = ?
        """, (engagement_score, status, timestamp, learner_id))
        
        updated_count += 1
    
    conn.commit()
    conn.close()
    
    print(f"Updated predictions for {updated_count} learners")
    return updated_count

# Add API endpoint
@app.route('/api/update-predictions', methods=['POST'])
def api_update_predictions():
    try:
        count = update_all_predictions()
        return jsonify({
            'success': True, 
            'message': f'Updated predictions for {count} learners'
        })
    except Exception as e:
        return jsonify({
            'success': False, 
            'message': f'Error updating predictions: {str(e)}'
        })

# Function to get all learners with their predicted status
def get_all_learners_with_status():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT learner_id, name, email FROM Learners")
    learners = cursor.fetchall()
    
    result = []
    for learner in learners:
        status, engagement_score = predict_learner_status(learner['learner_id'])
        result.append({
            'id': learner['learner_id'],
            'name': learner['name'],
            'email': learner['email'],
            'status': status,
            'engagement_score': engagement_score
        })
    
    conn.close()
    return result

# Function to get dashboard statistics
def get_dashboard_stats():
    learners = get_all_learners_with_status()
    
    total_learners = len(learners)
    on_track = len([l for l in learners if l['status'] == 'On Track'])
    at_risk = len([l for l in learners if l['status'] == 'At Risk'])
    drop_off = len([l for l in learners if l['status'] == 'Will Drop Off'])
    
    return {
        'total_learners': total_learners,
        'on_track': on_track,
        'at_risk': at_risk,
        'drop_off': drop_off
    }

# Function to get engagement trend data
def get_engagement_trend_data():
    # For simplicity, returning mock data
    # In a real implementation, you would query the database for historical data
    return {
        'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
        'average_engagement': [65, 59, 70, 65, 72, 68, 74],
        'at_risk_engagement': [40, 45, 38, 42, 35, 30, 28]
    }

# Function to get learner by email
def get_learner_by_email(email):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Learners WHERE email=?", (email,))
    learner = cursor.fetchone()
    
    conn.close()
    return learner

# Function to get all nudge logs
def get_nudge_logs():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("SELECT * FROM Nudge_Logs ORDER BY timestamp DESC")
    nudge_logs = cursor.fetchall()
    
    conn.close()
    return nudge_logs

# Update the get_tickets function to handle the missing column
def get_tickets():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, check if the created_at column exists
        cursor.execute("PRAGMA table_info(Ticket_Details)")
        columns = [col[1] for col in cursor.fetchall()]
        
        if 'created_at' in columns:
            cursor.execute("""
                SELECT t.*, l.name as learner_name, l.email as learner_email
                FROM Ticket_Details t 
                JOIN Learners l ON t.learner_id = l.learner_id 
                ORDER BY t.created_at DESC
            """)
        else:
            # Fallback if created_at doesn't exist
            cursor.execute("""
                SELECT t.*, l.name as learner_name, l.email as learner_email
                FROM Ticket_Details t 
                JOIN Learners l ON t.learner_id = l.learner_id 
                ORDER BY t.ticket_id DESC
            """)
            
        tickets = cursor.fetchall()
        
        conn.close()
        return tickets
    except Exception as e:
        print(f"Error in get_tickets: {e}")
        traceback.print_exc()
        return []

# Add these imports at the top if not already present
import json
from datetime import datetime, timedelta

# Add these API endpoints to your app.py

@app.route('/api/learner-stats')
def api_learner_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total learners
        cursor.execute("SELECT COUNT(*) FROM Learners")
        total_learners = cursor.fetchone()[0]
        
        # Active learners (logged in within last 7 days)
        cursor.execute("""
            SELECT COUNT(DISTINCT learner_id) 
            FROM Login_Activity 
            WHERE login_time >= date('now', '-7 days')
        """)
        active_learners = cursor.fetchone()[0]
        
        # At-risk learners (engagement < 40)
        cursor.execute("SELECT COUNT(*) FROM Learners WHERE total_engagement_score < 40")
        at_risk_learners = cursor.fetchone()[0]
        
        # Completed learners (engagement > 80)
        cursor.execute("SELECT COUNT(*) FROM Learners WHERE total_engagement_score > 80")
        completed_learners = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_learners': total_learners,
            'active_learners': active_learners,
            'at_risk_learners': at_risk_learners,
            'completed_learners': completed_learners
        })
    except Exception as e:
        print(f"Error in api_learner_stats: {e}")
        return jsonify({
            'total_learners': 0,
            'active_learners': 0,
            'at_risk_learners': 0,
            'completed_learners': 0
        })
        
@app.route('/api/intervention-stats')
def api_intervention_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Email stats
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Email%'")
        email_sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Email%' AND status IN ('Opened', 'Read')")
        email_opened = cursor.fetchone()[0]
        email_opened_rate = round((email_opened / email_sent * 100), 1) if email_sent > 0 else 0
        
        # Mock effectiveness rate
        email_effective_rate = round(email_opened_rate * 0.8, 1)
        
        # Mentor stats
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Mentor%'")
        mentor_requests = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Mentor%' AND status = 'Read'")
        mentor_sessions = cursor.fetchone()[0]
        mentor_success_rate = round((mentor_sessions / mentor_requests * 100), 1) if mentor_requests > 0 else 0
        
        # Challenge stats
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Challenge%'")
        challenges_created = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Challenge%' AND status = 'Read'")
        challenges_joined = cursor.fetchone()[0]
        challenges_completed_rate = round((challenges_joined / challenges_created * 100), 1) if challenges_created > 0 else 0
        
        # Reminder stats
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Reminder%'")
        reminders_sent = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM Nudge_Logs WHERE nudge_type LIKE '%Reminder%' AND status IN ('Opened', 'Read')")
        reminders_effective = cursor.fetchone()[0]
        reminders_effective_rate = round((reminders_effective / reminders_sent * 100), 1) if reminders_sent > 0 else 0
        
        # Mock engagement rate
        reminders_engagement_rate = round(reminders_effective_rate * 0.7, 1)
        
        conn.close()
        
        return jsonify({
            'email_sent': email_sent,
            'email_opened_rate': email_opened_rate,
            'email_effective_rate': email_effective_rate,
            'mentor_requests': mentor_requests,
            'mentor_sessions': mentor_sessions,
            'mentor_success_rate': mentor_success_rate,
            'challenges_created': challenges_created,
            'challenges_joined': challenges_joined,
            'challenges_completed_rate': challenges_completed_rate,
            'reminders_sent': reminders_sent,
            'reminders_effective_rate': reminders_effective_rate,
            'reminders_engagement_rate': reminders_engagement_rate
        })
    except Exception as e:
        print(f"Error in api_intervention_stats: {e}")
        return jsonify({
            'email_sent': 0,
            'email_opened_rate': 0,
            'email_effective_rate': 0,
            'mentor_requests': 0,
            'mentor_sessions': 0,
            'mentor_success_rate': 0,
            'challenges_created': 0,
            'challenges_joined': 0,
            'challenges_completed_rate': 0,
            'reminders_sent': 0,
            'reminders_effective_rate': 0,
            'reminders_engagement_rate': 0
        })

@app.route('/api/ticket-stats')
def api_ticket_stats():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total tickets
        cursor.execute("SELECT COUNT(*) FROM Ticket_Details")
        total_tickets = cursor.fetchone()[0]
        
        # Open tickets
        cursor.execute("SELECT COUNT(*) FROM Ticket_Details WHERE status = 'Open'")
        open_tickets = cursor.fetchone()[0]
        
        # Pending tickets
        cursor.execute("SELECT COUNT(*) FROM Ticket_Details WHERE status = 'Pending'")
        pending_tickets = cursor.fetchone()[0]
        
        # Resolved tickets
        cursor.execute("SELECT COUNT(*) FROM Ticket_Details WHERE status = 'Resolved'")
        resolved_tickets = cursor.fetchone()[0]
        
        conn.close()
        
        return jsonify({
            'total_tickets': total_tickets,
            'open_tickets': open_tickets,
            'pending_tickets': pending_tickets,
            'resolved_tickets': resolved_tickets
        })
    except Exception as e:
        print(f"Error in api_ticket_stats: {e}")
        return jsonify({
            'total_tickets': 0,
            'open_tickets': 0,
            'pending_tickets': 0,
            'resolved_tickets': 0
        })

@app.route('/api/train-model', methods=['POST'])
def api_train_model():
    try:
        # Simulate model training
        # In a real implementation, you would train your ML model here
        return jsonify({'success': True, 'message': 'Model training started successfully'})
    except Exception as e:
        print(f"Error in api_train_model: {e}")
        return jsonify({'success': False, 'message': 'Error training model'})

# Add the missing API endpoint for nudge logs
@app.route('/api/nudge-logs')
def api_nudge_logs():
    try:
        nudge_logs = get_nudge_logs()
        return jsonify([dict(log) for log in nudge_logs])
    except Exception as e:
        print(f"Error in api_nudge_logs: {e}")
        traceback.print_exc()
        return jsonify([])

# Add other missing API endpoints that your frontend expects
@app.route('/api/dashboard-stats')
def api_dashboard_stats():
    try:
        stats = get_dashboard_stats()
        return jsonify(stats)
    except Exception as e:
        print(f"Error in api_dashboard_stats: {e}")
        traceback.print_exc()
        return jsonify({
            'total_learners': 0,
            'on_track': 0,
            'at_risk': 0,
            'drop_off': 0
        })

@app.route('/api/engagement-trend')
def api_engagement_trend():
    try:
        trend_data = get_engagement_trend_data()
        return jsonify(trend_data)
    except Exception as e:
        print(f"Error in api_engagement_trend: {e}")
        traceback.print_exc()
        return jsonify({
            'labels': [],
            'average_engagement': [],
            'at_risk_engagement': []
        })

# Add a function to initialize the database with proper schema
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if Ticket_Details table has created_at column
    cursor.execute("PRAGMA table_info(Ticket_Details)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'created_at' not in columns:
        print("Adding created_at column to Ticket_Details table...")
        cursor.execute("ALTER TABLE Ticket_Details ADD COLUMN created_at TEXT")
        conn.commit()
        print("Column added successfully!")
    
    conn.close()

# Call this function when the app starts
init_db()

# Function to get a specific ticket
def get_ticket(ticket_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT t.*, l.name as learner_name, l.email as learner_email
        FROM Ticket_Details t 
        JOIN Learners l ON t.learner_id = l.learner_id 
        WHERE t.ticket_id = ?
    """, (ticket_id,))
    ticket = cursor.fetchone()
    
    conn.close()
    return ticket

# Function to create a new ticket
def create_ticket(learner_email, subject, description, priority):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get learner by email
    learner = get_learner_by_email(learner_email)
    if not learner:
        return False, "Learner not found with that email"
    
    # Create ticket
    ticket_id = f"TKT{datetime.now().strftime('%Y%m%d%H%M%S')}"
    created_at = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        INSERT INTO Ticket_Details 
        (ticket_id, learner_id, subject, description, priority, status, created_at)
        VALUES (?, ?, ?, ?, ?, 'Open', ?)
    """, (ticket_id, learner['learner_id'], subject, description, priority, created_at))
    
    conn.commit()
    conn.close()
    
    return True, "Ticket created successfully"

# Function to update a ticket
def update_ticket(ticket_id, status=None, feedback=None, satisfied=None):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    updates = []
    params = []
    
    if status:
        updates.append("status = ?")
        params.append(status)
        
        if status == 'Resolved':
            updates.append("resolved_at = ?")
            params.append(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
    
    if feedback is not None:
        updates.append("feedback = ?")
        params.append(feedback)
    
    if satisfied is not None:
        updates.append("satisfied = ?")
        params.append(satisfied)
    
    if updates:
        query = f"UPDATE Ticket_Details SET {', '.join(updates)} WHERE ticket_id = ?"
        params.append(ticket_id)
        
        cursor.execute(query, params)
        conn.commit()
    
    conn.close()
    return True, "Ticket updated successfully"

# Function to get learner details
def get_learner_details(learner_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Get learner info
    cursor.execute("SELECT * FROM Learners WHERE learner_id=?", (learner_id,))
    learner = cursor.fetchone()
    
    if not learner:
        conn.close()
        return None
    
    # Get login activity
    cursor.execute("SELECT * FROM Login_Activity WHERE learner_id=?", (learner_id,))
    login_activity = cursor.fetchall()
    
    # Get assignment details
    cursor.execute("SELECT * FROM Assignment_Details WHERE learner_id=?", (learner_id,))
    assignments = cursor.fetchall()
    
    # Get quiz details
    cursor.execute("SELECT * FROM Quiz_Details WHERE learner_id=?", (learner_id,))
    quizzes = cursor.fetchall()
    
    # Get live session details
    cursor.execute("SELECT * FROM Live_Session WHERE learner_id=?", (learner_id,))
    live_sessions = cursor.fetchall()
    
    conn.close()
    
    return {
        'learner': dict(learner) if learner else None,
        'login_activity': [dict(row) for row in login_activity],
        'assignments': [dict(row) for row in assignments],
        'quizzes': [dict(row) for row in quizzes],
        'live_sessions': [dict(row) for row in live_sessions]
    }

# Function to search learners
def search_learners(query):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Search by name or email
    cursor.execute("""
        SELECT learner_id, name, email 
        FROM Learners 
        WHERE name LIKE ? OR email LIKE ?
    """, (f'%{query}%', f'%{query}%'))
    
    learners = cursor.fetchall()
    conn.close()
    
    return [dict(learner) for learner in learners]

# Function to send a nudge
def send_nudge(learner_id, nudge_type, message):
    conn = get_db_connection()
    cursor = conn.cursor()
    
    nudge_id = f"NDG{datetime.now().strftime('%Y%m%d%H%M%S')}"
    timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    cursor.execute("""
        INSERT INTO Nudge_Logs 
        (nudge_id, learner_id, nudge_type, message, timestamp)
        VALUES (?, ?, ?, ?, ?)
    """, (nudge_id, learner_id, nudge_type, message, timestamp))
    
    conn.commit()
    conn.close()
    
    return True, "Nudge sent successfully"

# Routes
@app.route('/')
def index():
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    try:
        stats = get_dashboard_stats()
        trend_data = get_engagement_trend_data()
        return render_template('dashboard.html', stats=stats, trend_data=trend_data)
    except Exception as e:
        print(f"Error in dashboard: {e}")
        # Return default data if there's an error
        return render_template('dashboard.html', stats={
            'total_learners': 0,
            'on_track': 0,
            'at_risk': 0,
            'drop_off': 0
        }, trend_data={
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'average_engagement': [0, 0, 0, 0, 0, 0, 0],
            'at_risk_engagement': [0, 0, 0, 0, 0, 0, 0]
        })

@app.route('/learners')
def learners():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get courses for filter dropdown
        cursor.execute("SELECT course_id, course_name FROM Courses")
        courses = [dict(row) for row in cursor.fetchall()]
        
        # Get cohorts for filter dropdown
        cursor.execute("SELECT DISTINCT cohort_id FROM Cohorts ORDER BY cohort_id")
        cohorts = [dict(row) for row in cursor.fetchall()]
        
        conn.close()
        
        return render_template('learners.html', courses=courses, cohorts=cohorts)
    except Exception as e:
        print(f"Error in learners: {e}")
        return render_template('learners.html', courses=[], cohorts=[])

@app.route('/api/learners')
def api_learners():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all learners with their details including course information
        cursor.execute("""
            SELECT l.learner_id as id, l.name, l.email, l.cohort_id as cohort, 
                   c.course_id, c.course_name,
                   l.total_engagement_score as engagement,
                   CASE 
                       WHEN l.total_engagement_score >= 70 THEN 'low'
                       WHEN l.total_engagement_score >= 40 THEN 'medium'
                       ELSE 'high'
                   END as risk_level,
                   MAX(la.login_time) as last_active,
                   ROUND(l.total_engagement_score * 1.2, 1) as progress
            FROM Learners l
            LEFT JOIN Cohorts ch ON l.cohort_id = ch.cohort_id
            LEFT JOIN Courses c ON ch.course_id = c.course_id
            LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
            GROUP BY l.learner_id
            ORDER BY l.name
        """)
        
        learners = cursor.fetchall()
        conn.close()
        
        # Convert to list of dictionaries
        result = []
        for learner in learners:
            result.append({
                'id': learner['id'],
                'name': learner['name'],
                'email': learner['email'],
                'cohort': learner['cohort'],
                'course_id': learner['course_id'],
                'course_name': learner['course_name'],
                'engagement': round(learner['engagement'], 1) if learner['engagement'] else 0,
                'progress': min(learner['progress'], 100) if learner['progress'] else 0,
                'risk_level': learner['risk_level'],
                'last_active': learner['last_active'] or 'Never'
            })
        
        return jsonify(result)
    except Exception as e:
        print(f"Error in api_learners: {e}")
        traceback.print_exc()
        return jsonify([])

@app.route('/learner/<learner_id>')
def learner_details(learner_id):
    learner_data = get_learner_details(learner_id)
    if not learner_data:
        return "Learner not found", 404
    
    status, engagement_score = predict_learner_status(learner_id)
    learner_data['status'] = status
    learner_data['engagement_score'] = engagement_score
    
    return render_template('learner_details.html', data=learner_data)

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

@app.route('/interventions')
def interventions():
    try:
        nudge_logs = get_nudge_logs()
        return render_template('interventions.html', nudge_logs=nudge_logs)
    except Exception as e:
        print(f"Error in interventions: {e}")
        return render_template('interventions.html', nudge_logs=[])

@app.route('/tickets')
def tickets():
    return render_template('tickets.html')

@app.route('/search-learner')
def search_learner():
    query = request.args.get('q', '')
    results = []
    if query:
        results = search_learners(query)
    return render_template('search_learner.html', query=query, results=results)

# API Routes
@app.route('/api/tickets')
def api_tickets():
    tickets = get_tickets()
    return jsonify([dict(ticket) for ticket in tickets])

@app.route('/api/ticket/<ticket_id>')
def api_ticket(ticket_id):
    ticket = get_ticket(ticket_id)
    if not ticket:
        return jsonify({'error': 'Ticket not found'}), 404
    return jsonify(dict(ticket))

@app.route('/api/create-ticket', methods=['POST'])
def api_create_ticket():
    data = request.get_json()
    success, message = create_ticket(
        data.get('learner_email'),
        data.get('subject'),
        data.get('description'),
        data.get('priority', 'Medium')
    )
    
    return jsonify({'success': success, 'message': message})

@app.route('/api/update-ticket/<ticket_id>', methods=['POST'])
def api_update_ticket(ticket_id):
    data = request.get_json()
    success, message = update_ticket(
        ticket_id,
        data.get('status'),
        data.get('feedback'),
        data.get('satisfied')
    )
    
    return jsonify({'success': success, 'message': message})
def get_all_learners_for_ui():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT l.learner_id, l.name, l.email, l.cohort_id as cohort, 
               l.total_engagement_score as engagement,
               CASE 
                   WHEN l.total_engagement_score >= 70 THEN 'low'
                   WHEN l.total_engagement_score >= 40 THEN 'medium'
                   ELSE 'high'
               END as risk_level,
               MAX(la.login_time) as last_active
        FROM Learners l
        LEFT JOIN Login_Activity la ON l.learner_id = la.learner_id
        GROUP BY l.learner_id
        ORDER BY l.name
    """)
    
    learners = cursor.fetchall()
    conn.close()
    
    result = []
    for learner in learners:
        # Calculate progress based on completed activities
        progress = min(learner['engagement'] * 1.2, 100)  # Mock progress calculation
        
        result.append({
            'id': learner['learner_id'],
            'name': learner['name'],
            'email': learner['email'],
            'cohort': learner['cohort'],
            'engagement': round(learner['engagement'], 1),
            'progress': round(progress, 1),
            'risk_level': learner['risk_level'],
            'last_active': learner['last_active'] or 'Never'
        })
    
    return result

@app.route('/api/learner/<learner_id>')
def api_learner_details(learner_id):
    learner_data = get_learner_details(learner_id)
    if not learner_data:
        return jsonify({'error': 'Learner not found'}), 404
    
    status, engagement_score = predict_learner_status(learner_id)
    learner_data['status'] = status
    learner_data['engagement_score'] = engagement_score
    
    return jsonify(learner_data)

@app.route('/api/send-nudge', methods=['POST'])
def api_send_nudge():
    data = request.get_json()
    success, message = send_nudge(
        data.get('learner_id'),
        data.get('nudge_type'),
        data.get('message')
    )
    
    return jsonify({'success': success, 'message': message})

# New API endpoints for analytics
@app.route('/api/analytics')
def api_analytics():
    # Mock data for analytics - in a real app, you'd query the database
    return jsonify({
        'avg_engagement': 72.5,
        'completion_rate': 68.2,
        'retention_rate': 85.7,
        'engagement_trend': 5.2,
        'completion_trend': 3.8,
        'retention_trend': -1.5,
        'engagement_by_day': {
            'labels': ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'],
            'values': [65, 59, 70, 65, 72, 68, 74]
        },
        'activity_distribution': {
            'labels': ['Login', 'Assignments', 'Quizzes', 'Sessions'],
            'values': [35, 25, 20, 20]
        }
    })

@app.route('/api/cohorts')
def api_cohorts():
    # Mock data for cohorts - in a real app, you'd query the database
    cohorts = [
        {
            'cohort_id': 'C101',
            'start_date': '2024-01-15',
            'learner_count': 45,
            'avg_engagement': 78.3,
            'completion_rate': 82.2,
            'retention_rate': 88.5
        },
        {
            'cohort_id': 'C102',
            'start_date': '2024-02-10',
            'learner_count': 38,
            'avg_engagement': 65.7,
            'completion_rate': 70.1,
            'retention_rate': 75.3
        },
        {
            'cohort_id': 'C103',
            'start_date': '2024-03-05',
            'learner_count': 52,
            'avg_engagement': 82.1,
            'completion_rate': 85.6,
            'retention_rate': 90.2
        }
    ]
    return jsonify(cohorts)

@app.route('/api/dropout-analysis')
def api_dropout_analysis():
    # Mock data for dropout analysis - in a real app, you'd query the database
    return jsonify({
        'risk_distribution': {
            'labels': ['C101', 'C102', 'C103'],
            'low_risk': [30, 20, 35],
            'medium_risk': [10, 12, 10],
            'high_risk': [5, 6, 7]
        },
        'top_risk_factors': [
            'Low login frequency',
            'Missed assignment deadlines',
            'Poor quiz performance',
            'Low session attendance'
        ],
        'recommended_interventions': [
            'Personalized email check-ins',
            'Mentor support sessions',
            'Peer learning groups',
            'Reminder notifications'
        ]
    })

if __name__ == '__main__':
    import os
    # Initialize database with proper schema
    try:
        init_db()
        print("Database initialized successfully!")
    except Exception as e:
        print(f"Error initializing database: {e}")
    
    # Initialize ML model
    initialize_model()
    
    # Get port from environment variable (for Render deployment)
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
