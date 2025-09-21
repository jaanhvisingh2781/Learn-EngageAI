import sqlite3
import random
import string
from datetime import datetime, timedelta
import uuid
import hashlib

def create_tables_if_not_exist(cursor):
    """Create tables if they don't exist"""
    
    # Users table for authentication
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Users (
        user_id TEXT PRIMARY KEY,
        username TEXT UNIQUE,
        password_hash TEXT,
        role TEXT,
        assigned_courses TEXT
    )
    """)
    
    # Courses table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Courses (
        course_id TEXT PRIMARY KEY,
        course_name TEXT
    )
    """)
    
    # Cohorts table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Cohorts (
        cohort_id TEXT PRIMARY KEY,
        course_id TEXT,
        start_date DATE,
        FOREIGN KEY(course_id) REFERENCES Courses(course_id)
    )
    """)
    
    # Learners table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Learners (
        learner_id TEXT PRIMARY KEY,
        cohort_id TEXT,
        name TEXT,
        email TEXT,
        contact TEXT,
        country_region TEXT,
        timezone TEXT,
        work_ex INTEGER,
        status TEXT,
        total_engagement_score REAL,
        FOREIGN KEY(cohort_id) REFERENCES Cohorts(cohort_id)
    )
    """)
    
    # Login_Activity table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Login_Activity (
        login_id TEXT PRIMARY KEY,
        learner_id TEXT,
        name TEXT,
        email TEXT,
        password TEXT,
        login_time DATETIME,
        logout_time DATETIME,
        total_duration INTEGER,
        FOREIGN KEY(learner_id) REFERENCES Learners(learner_id)
    )
    """)
    
    # Assignment_Details table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Assignment_Details (
        assignment_id TEXT PRIMARY KEY,
        learner_id TEXT,
        course_id TEXT,
        cohort_id TEXT,
        assignment_status TEXT,
        assignment_score REAL,
        submitted_at DATETIME,
        normalized_score REAL,
        FOREIGN KEY(learner_id) REFERENCES Learners(learner_id),
        FOREIGN KEY(course_id) REFERENCES Courses(course_id),
        FOREIGN KEY(cohort_id) REFERENCES Cohorts(cohort_id)
    )
    """)
    
    # Quiz_Details table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Quiz_Details (
        quiz_id TEXT PRIMARY KEY,
        learner_id TEXT,
        course_id TEXT,
        cohort_id TEXT,
        quiz_status TEXT,
        quiz_score REAL,
        attempted_at DATETIME,
        normalized_score REAL,
        FOREIGN KEY(learner_id) REFERENCES Learners(learner_id),
        FOREIGN KEY(course_id) REFERENCES Courses(course_id),
        FOREIGN KEY(cohort_id) REFERENCES Cohorts(cohort_id)
    )
    """)
    
    # Live_Session table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Live_Session (
        session_id TEXT PRIMARY KEY,
        course_id TEXT,
        cohort_id TEXT,
        learner_id TEXT,
        attendance_status TEXT,
        FOREIGN KEY(course_id) REFERENCES Courses(course_id),
        FOREIGN KEY(cohort_id) REFERENCES Cohorts(cohort_id),
        FOREIGN KEY(learner_id) REFERENCES Learners(learner_id)
    )
    """)
    
    # Updated Ticket_Details table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Ticket_Details (
        ticket_id TEXT PRIMARY KEY,
        learner_id TEXT,
        subject TEXT,
        description TEXT,
        priority TEXT,
        status TEXT,
        created_at TEXT,
        resolved_at TEXT,
        feedback TEXT,
        satisfied INTEGER,
        FOREIGN KEY (learner_id) REFERENCES Learners (learner_id)
    )
    """)
    
    # Updated Nudge_Logs table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS Nudge_Logs (
        nudge_id TEXT PRIMARY KEY,
        learner_id TEXT,
        nudge_type TEXT,
        message TEXT,
        timestamp TEXT,
        status TEXT DEFAULT 'Sent',
        channel TEXT DEFAULT 'Email',
        FOREIGN KEY (learner_id) REFERENCES Learners (learner_id)
    )
    """)

def hash_password(password):
    """Hash a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def generate_random_data(db_path):
    # Connect to the database
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # First, drop existing tables to avoid schema conflicts
    tables = ['Users', 'Nudge_Logs', 'Ticket_Details', 'Live_Session', 'Quiz_Details', 
              'Assignment_Details', 'Login_Activity', 'Learners', 'Cohorts', 'Courses']
    
    for table in tables:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table}")
        except sqlite3.Error as e:
            print(f"Error dropping table {table}: {e}")
    
    # Create tables if they don't exist
    create_tables_if_not_exist(cursor)
    conn.commit()
    
    # Create users with different roles
    print("Creating users...")
    users = [
        # Super Admin - can view all courses and cohorts
        ("U001", "superadmin", hash_password("admin123"), "Super Admin", "ALL"),
        # Program Coordinators - can view only assigned courses
        ("U002", "coordinator1", hash_password("coord1"), "Program Coordinator", "CR101,CS201"),
        ("U003", "coordinator2", hash_password("coord2"), "Program Coordinator", "DS301,AI401"),
        ("U004", "coordinator3", hash_password("coord3"), "Program Coordinator", "ML501,WEB601")
    ]
    
    cursor.executemany("INSERT INTO Users (user_id, username, password_hash, role, assigned_courses) VALUES (?, ?, ?, ?, ?)", users)
    conn.commit()
    
    # Helper functions
    def random_id(prefix, length=3):
        return f"{prefix}{random.randint(10**(length-1), 10**length - 1)}"
    
    def random_email(name):
        domains = ["gmail.com", "yahoo.com", "hotmail.com", "example.com", "outlook.com"]
        return f"{name.lower().replace(' ', '.')}@{random.choice(domains)}"
    
    def random_phone():
        return f"+91-{random.randint(9000000000, 9999999999)}"
    
    def random_date(start_date, end_date):
        delta = end_date - start_date
        random_days = random.randint(0, delta.days)
        return start_date + timedelta(days=random_days)
    
    def random_datetime(start_date, end_date):
        delta = end_date - start_date
        random_seconds = random.randint(0, int(delta.total_seconds()))  # Convert to int
        return start_date + timedelta(seconds=random_seconds)
    
    # Generate only 7 specific courses
    print("Generating Courses data...")
    courses = [
        ("CR101", "Introduction to Python Programming"),
        ("CS201", "Advanced Java Development"),
        ("DS301", "Data Science Fundamentals"),
        ("AI401", "Artificial Intelligence Essentials"),
        ("ML501", "Machine Learning Mastery"),
        ("WEB601", "Web Development Bootcamp"),
        ("NET701", "Network Security Fundamentals")
    ]
    
    cursor.executemany("INSERT INTO Courses (course_id, course_name) VALUES (?, ?)", courses)
    conn.commit()
    
    # 2. Cohorts
    print("Generating Cohorts data...")
    cohorts = []
    cohort_ids = set()  # To track unique cohort IDs
    
    for i in range(20):  # Reduced number of cohorts
        while True:
            cohort_id = f"C{random.randint(100, 999)}"
            if cohort_id not in cohort_ids:
                cohort_ids.add(cohort_id)
                break
                
        course_id = random.choice(courses)[0]
        start_date = random_date(datetime(2024, 1, 1), datetime(2025, 12, 31))
        cohorts.append((cohort_id, course_id, start_date.strftime("%Y-%m-%d")))
    
    cursor.executemany("INSERT INTO Cohorts (cohort_id, course_id, start_date) VALUES (?, ?, ?)", cohorts)
    conn.commit()
    
    # 3. Learners
    print("Generating Learners data...")
    learners = []
    learner_ids = set()  # To track unique learner IDs

    first_names = ["Akshit", "Omkar", "Mohammed", "Janhvi", "Rohit", "Sneha", "Karan", "Ananya", "Vikas", "Pooja",
                  "Rahul", "Priya", "Amit", "Neha", "Sanjay", "Divya", "Vishal", "Meera", "Raj", "Sunita"]
    last_names = ["Sharma", "Patil", "Khan", "Mehta", "Verma", "Gupta", "Joshi", "Roy", "Nair", "Iyer",
                 "Singh", "Kumar", "Patel", "Shah", "Reddy", "Malhotra", "Chopra", "Agarwal", "Bose", "Rao"]
    countries = ["India", "USA", "UK", "Canada", "Australia", "Germany", "France", "Japan", "Singapore", "Brazil"]
    timezones = ["IST (+5:30)", "PST (-8:00)", "EST (-5:00)", "GMT (+0:00)", "CET (+1:00)", "AEST (+10:00)"]
    statuses = ["On track", "At Risk", "Will Drop off"]

    # Generate unique learner IDs first
    for i in range(500):
        while True:
            learner_id = f"L{random.randint(1000, 9999)}"
            if learner_id not in learner_ids:
                learner_ids.add(learner_id)
                break

    # Now create learners with the pre-generated unique IDs
    for learner_id in learner_ids:
        cohort_id = random.choice(cohorts)[0] if cohorts else "C001"
        first_name = random.choice(first_names)
        last_name = random.choice(last_names)
        name = f"{first_name} {last_name}"
        email = random_email(name)
        contact = random_phone()
        country_region = random.choice(countries)
        timezone = random.choice(timezones)
        work_ex = random.randint(0, 20)
        status = random.choice(statuses)
        total_engagement_score = round(random.uniform(0, 100), 2)
        
        learners.append((learner_id, cohort_id, name, email, contact, country_region, timezone, work_ex, status, total_engagement_score))

    # Moved executemany OUTSIDE the loop
    cursor.executemany("INSERT INTO Learners (learner_id, cohort_id, name, email, contact, country_region, timezone, work_ex, status, total_engagement_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", learners)
    conn.commit()
    
    # 4. Login_Activity
    print("Generating Login_Activity data...")
    login_activities = []
    login_ids = set()  # To track unique login IDs
    
    for i in range(500):
        while True:
            login_id = f"LA{random.randint(1000, 9999)}"  # Increased range to avoid duplicates
            if login_id not in login_ids:
                login_ids.add(login_id)
                break
                
        learner = random.choice(learners)
        learner_id = learner[0]
        name = learner[2]
        email = learner[3]
        password = "hashedpwd"  # Placeholder for hashed password
        
        login_date = random_date(datetime(2025, 1, 1), datetime(2025, 12, 31))
        login_time = random_datetime(login_date.replace(hour=6, minute=0), login_date.replace(hour=12, minute=0))
        logout_time = login_time + timedelta(hours=random.randint(1, 8))
        total_duration = int((logout_time - login_time).total_seconds() / 60)  # in minutes
        
        login_activities.append((login_id, learner_id, name, email, password, 
                               login_time.strftime("%Y-%m-%d %H:%M:%S"), 
                               logout_time.strftime("%Y-%m-%d %H:%M:%S"), 
                               total_duration))
    
    cursor.executemany("INSERT INTO Login_Activity (login_id, learner_id, name, email, password, login_time, logout_time, total_duration) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", login_activities)
    conn.commit()
    
    # 5. Assignment_Details
    print("Generating Assignment_Details data...")
    assignments = []
    assignment_ids = set()  # To track unique assignment IDs
    
    statuses = ["Submitted", "Pending", "Graded", "Late"]
    
    for i in range(500):
        while True:
            assignment_id = f"A{random.randint(1000, 9999)}"  # Increased range to avoid duplicates
            if assignment_id not in assignment_ids:
                assignment_ids.add(assignment_id)
                break
                
        learner = random.choice(learners)
        learner_id = learner[0]
        course_id = random.choice(courses)[0]
        cohort_id = learner[1]
        assignment_status = random.choice(statuses)
        assignment_score = round(random.uniform(0, 100), 2) if assignment_status in ["Submitted", "Graded"] else None
        submitted_at = random_datetime(datetime(2025, 1, 1), datetime(2025, 12, 31)) if assignment_status != "Pending" else None
        normalized_score = round(assignment_score / 100, 2) if assignment_score is not None else None
        
        assignments.append((assignment_id, learner_id, course_id, cohort_id, assignment_status, 
                          assignment_score, 
                          submitted_at.strftime("%Y-%m-%d %H:%M:%S") if submitted_at else None, 
                          normalized_score))
    
    cursor.executemany("INSERT INTO Assignment_Details (assignment_id, learner_id, course_id, cohort_id, assignment_status, assignment_score, submitted_at, normalized_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", assignments)
    conn.commit()
    
    # 6. Quiz_Details
    print("Generating Quiz_Details data...")
    quizzes = []
    quiz_ids = set()  # To track unique quiz IDs
    
    statuses = ["Attempted", "Pending", "Completed", "Not Started"]
    
    for i in range(500):
        while True:
            quiz_id = f"Q{random.randint(1000, 9999)}"  # Increased range to avoid duplicates
            if quiz_id not in quiz_ids:
                quiz_ids.add(quiz_id)
                break
                
        learner = random.choice(learners)
        learner_id = learner[0]
        course_id = random.choice(courses)[0]
        cohort_id = learner[1]
        quiz_status = random.choice(statuses)
        quiz_score = round(random.uniform(0, 100), 2) if quiz_status == "Attempted" else None
        attempted_at = random_datetime(datetime(2025, 1, 1), datetime(2025, 12, 31)) if quiz_status == "Attempted" else None
        normalized_score = round(quiz_score / 100, 2) if quiz_score is not None else None
        
        quizzes.append((quiz_id, learner_id, course_id, cohort_id, quiz_status, quiz_score, 
                       attempted_at.strftime("%Y-%m-%d %H:%M:%S") if attempted_at else None, 
                       normalized_score))
    
    cursor.executemany("INSERT INTO Quiz_Details (quiz_id, learner_id, course_id, cohort_id, quiz_status, quiz_score, attempted_at, normalized_score) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", quizzes)
    conn.commit()
    
    # 7. Live_Session
    print("Generating Live_Session data...")
    live_sessions = []
    session_ids = set()  # To track unique session IDs
    
    statuses = ["Present", "Absent", "Late", "Left Early"]
    
    for i in range(500):
        while True:
            session_id = f"S{random.randint(1000, 9999)}"  # Increased range to avoid duplicates
            if session_id not in session_ids:
                session_ids.add(session_id)
                break
                
        course_id = random.choice(courses)[0]
        cohort_id = random.choice(cohorts)[0] if cohorts else "C001"
        learner = random.choice(learners)
        learner_id = learner[0]
        attendance_status = random.choice(statuses)
        
        live_sessions.append((session_id, course_id, cohort_id, learner_id, attendance_status))
    
    cursor.executemany("INSERT INTO Live_Session (session_id, course_id, cohort_id, learner_id, attendance_status) VALUES (?, ?, ?, ?, ?)", live_sessions)
    conn.commit()
    
    # 8. Ticket_Details
    print("Generating Ticket_Details data...")
    tickets = []
    ticket_ids = set()  # To track unique ticket IDs
    
    priorities = ["Low", "Medium", "High", "Urgent"]
    statuses = ["Open", "In Progress", "Resolved", "Closed"]
    subjects = ["Technical Issue", "Content Clarification", "Assignment Help", "Payment Issue", "Platform Bug"]
    descriptions = [
        "Having trouble accessing the learning materials",
        "Need clarification on module 3 content",
        "Assignment submission not working",
        "Payment gateway issue",
        "Video lectures not loading properly"
    ]
    feedback_options = ["Excellent support", "Good response", "Average", "Could be better", "Not helpful"]
    
    for i in range(500):
        while True:
            ticket_id = f"T{random.randint(1000, 9999)}"  # Increased range to avoid duplicates
            if ticket_id not in ticket_ids:
                ticket_ids.add(ticket_id)
                break
                
        learner = random.choice(learners)
        learner_id = learner[0]
        subject = random.choice(subjects)
        description = random.choice(descriptions)
        priority = random.choice(priorities)
        status = random.choice(statuses)
        created_at = random_datetime(datetime(2025, 1, 1), datetime(2025, 12, 31))
        resolved_at = created_at + timedelta(hours=random.randint(1, 72)) if status in ["Resolved", "Closed"] else None
        feedback = random.choice(feedback_options) if status in ["Resolved", "Closed"] else None
        satisfied = random.randint(0, 1) if status in ["Resolved", "Closed"] else None
        
        tickets.append((ticket_id, learner_id, subject, description, priority, status,
                       created_at.strftime("%Y-%m-%d %H:%M:%S"),
                       resolved_at.strftime("%Y-%m-%d %H:%M:%S") if resolved_at else None,
                       feedback, satisfied))
    
    cursor.executemany("INSERT INTO Ticket_Details (ticket_id, learner_id, subject, description, priority, status, created_at, resolved_at, feedback, satisfied) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", tickets)
    conn.commit()
    
    # 9. Nudge_Logs
    print("Generating Nudge_Logs data...")
    nudges = []
    nudge_ids = set()  # To track unique nudge IDs
    
    nudge_types = ["Reminder", "Peer Challenge", "Mentor Connect", "Progress Check", "Resource Share"]
    channels = ["Email", "WhatsApp", "Slack", "SMS", "In-app"]
    statuses = ["Sent", "Delivered", "Opened", "Failed", "Read"]
    
    for i in range(500):
        while True:
            nudge_id = f"N{random.randint(1000, 9999)}"  # Increased range to avoid duplicates
            if nudge_id not in nudge_ids:
                nudge_ids.add(nudge_id)
                break
                
        learner = random.choice(learners)
        learner_id = learner[0]
        nudge_type = random.choice(nudge_types)
        message = f"Hi {learner[2]}, this is your {nudge_type.lower()} reminder. Please check your upcoming tasks and deadlines."
        timestamp = random_datetime(datetime(2025, 1, 1), datetime(2025, 12, 31))
        channel = random.choice(channels)
        status = random.choice(statuses)
        
        nudges.append((nudge_id, learner_id, nudge_type, message, 
                      timestamp.strftime("%Y-%m-%d %H:%M:%S"), status, channel))
    
    cursor.executemany("INSERT INTO Nudge_Logs (nudge_id, learner_id, nudge_type, message, timestamp, status, channel) VALUES (?, ?, ?, ?, ?, ?, ?)", nudges)
    conn.commit()
    
    # Commit changes and close connection
    conn.close()
    print("Data generation completed successfully!")
    print("\nUser accounts created:")
    print("Super Admin: username='superadmin', password='admin123' (can view all courses)")
    print("Program Coordinator 1: username='coordinator1', password='coord1' (can view CR101, CS201)")
    print("Program Coordinator 2: username='coordinator2', password='coord2' (can view DS301, AI401)")
    print("Program Coordinator 3: username='coordinator3', password='coord3' (can view ML501, WEB601)")

# Add this to your init_db function
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Add prediction timestamp column if it doesn't exist
    cursor.execute("PRAGMA table_info(Learners)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'prediction_timestamp' not in columns:
        cursor.execute("ALTER TABLE Learners ADD COLUMN prediction_timestamp TEXT")
    
    conn.commit()
    conn.close()
# Usage
if __name__ == "__main__":
    db_path = "engagement_hackathon.db"  # Replace with your database path
    generate_random_data(db_path)