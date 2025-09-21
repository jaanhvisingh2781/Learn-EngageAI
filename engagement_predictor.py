# Enhanced ML algorithm for engagement prediction
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor, VotingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.impute import SimpleImputer
import joblib
import sqlite3
from datetime import datetime, timedelta

class EngagementPredictor:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.imputer = SimpleImputer(strategy='median')
        self.feature_names = []
        
    def extract_features(self, learner_id, conn):
        """Extract comprehensive features for a learner"""
        features = {}
        
        # Login activity features
        login_df = pd.read_sql("""
            SELECT total_duration, login_time 
            FROM Login_Activity 
            WHERE learner_id = ?
            ORDER BY login_time DESC
        """, conn, params=[learner_id])
        
        if not login_df.empty:
            features['login_count'] = len(login_df)
            features['avg_session_duration'] = login_df['total_duration'].mean()
            features['total_login_time'] = login_df['total_duration'].sum()
            features['days_since_last_login'] = (datetime.now() - pd.to_datetime(login_df['login_time'].iloc[0])).days
            features['login_frequency'] = features['login_count'] / max(1, (datetime.now() - pd.to_datetime(login_df['login_time'].iloc[-1])).days)
        else:
            features.update({
                'login_count': 0,
                'avg_session_duration': 0,
                'total_login_time': 0,
                'days_since_last_login': 999,
                'login_frequency': 0
            })
        
        # Assignment features
        assignment_df = pd.read_sql("""
            SELECT assignment_status, assignment_score, submitted_at, normalized_score
            FROM Assignment_Details 
            WHERE learner_id = ?
        """, conn, params=[learner_id])
        
        if not assignment_df.empty:
            features['assignment_count'] = len(assignment_df)
            features['assignment_submission_rate'] = len(assignment_df[assignment_df['assignment_status'] == 'Submitted']) / len(assignment_df)
            features['avg_assignment_score'] = assignment_df['assignment_score'].mean() if 'assignment_score' in assignment_df.columns else 0
            features['on_time_submission_rate'] = len(assignment_df[assignment_df['assignment_status'] == 'Submitted']) / len(assignment_df)
        else:
            features.update({
                'assignment_count': 0,
                'assignment_submission_rate': 0,
                'avg_assignment_score': 0,
                'on_time_submission_rate': 0
            })
        
        # Quiz features
        quiz_df = pd.read_sql("""
            SELECT quiz_status, quiz_score, attempted_at, normalized_score
            FROM Quiz_Details 
            WHERE learner_id = ?
        """, conn, params=[learner_id])
        
        if not quiz_df.empty:
            features['quiz_count'] = len(quiz_df)
            features['quiz_attempt_rate'] = len(quiz_df[quiz_df['quiz_status'] == 'Attempted']) / len(quiz_df)
            features['avg_quiz_score'] = quiz_df['quiz_score'].mean() if 'quiz_score' in quiz_df.columns else 0
            features['quiz_consistency'] = quiz_df['quiz_score'].std() if 'quiz_score' in quiz_df.columns else 0
        else:
            features.update({
                'quiz_count': 0,
                'quiz_attempt_rate': 0,
                'avg_quiz_score': 0,
                'quiz_consistency': 0
            })
        
        # Live session features
        session_df = pd.read_sql("""
            SELECT attendance_status
            FROM Live_Session 
            WHERE learner_id = ?
        """, conn, params=[learner_id])
        
        if not session_df.empty:
            features['session_count'] = len(session_df)
            features['attendance_rate'] = len(session_df[session_df['attendance_status'] == 'Present']) / len(session_df)
        else:
            features.update({
                'session_count': 0,
                'attendance_rate': 0
            })
        
        # Ticket features
        ticket_df = pd.read_sql("""
            SELECT status, priority, satisfied, resolved_at, created_at
            FROM Ticket_Details 
            WHERE learner_id = ?
        """, conn, params=[learner_id])
        
        if not ticket_df.empty:
            features['ticket_count'] = len(ticket_df)
            features['resolved_ticket_rate'] = len(ticket_df[ticket_df['status'] == 'Resolved']) / len(ticket_df)
            features['avg_resolution_time'] = 0  # Would calculate from created_at and resolved_at
            features['satisfaction_rate'] = ticket_df['satisfied'].mean() if 'satisfied' in ticket_df.columns else 0
        else:
            features.update({
                'ticket_count': 0,
                'resolved_ticket_rate': 0,
                'avg_resolution_time': 0,
                'satisfaction_rate': 0
            })
        
        return features
    
    def prepare_training_data(self, conn):
        """Prepare training data from all learners"""
        # Get all learners
        learners_df = pd.read_sql("SELECT learner_id, total_engagement_score FROM Learners", conn)
        
        X = []
        y = []
        learner_ids = []
        
        for _, row in learners_df.iterrows():
            features = self.extract_features(row['learner_id'], conn)
            X.append(list(features.values()))
            y.append(row['total_engagement_score'])
            learner_ids.append(row['learner_id'])
            
            if len(self.feature_names) == 0:
                self.feature_names = list(features.keys())
        
        X = np.array(X)
        y = np.array(y)
        
        # Handle missing values
        X = self.imputer.fit_transform(X)
        
        # Scale features
        X = self.scaler.fit_transform(X)
        
        return X, y, learner_ids
    
    def train_model(self, conn, test_size=0.2):
        """Train the ensemble model"""
        X, y, learner_ids = self.prepare_training_data(conn)
        
        # Split data
        X_train, X_test, y_train, y_test, ids_train, ids_test = train_test_split(
            X, y, learner_ids, test_size=test_size, random_state=42
        )
        
        # Create ensemble model
        rf = RandomForestRegressor(n_estimators=100, random_state=42, max_depth=10)
        gb = GradientBoostingRegressor(n_estimators=100, random_state=42, max_depth=8)
        
        self.model = VotingRegressor([('rf', rf), ('gb', gb)])
        self.model.fit(X_train, y_train)
        
        # Evaluate model
        y_pred = self.model.predict(X_test)
        mae = mean_absolute_error(y_test, y_pred)
        r2 = r2_score(y_test, y_pred)
        
        print(f"Model trained with MAE: {mae:.2f}, R²: {r2:.2f}")
        
        return mae, r2
    
    def predict_engagement(self, learner_id, conn):
        """Predict engagement score for a single learner"""
        features = self.extract_features(learner_id, conn)
        X = np.array([list(features.values())])
        
        # Preprocess
        X = self.imputer.transform(X)
        X = self.scaler.transform(X)
        
        # Predict
        engagement_score = self.model.predict(X)[0]
        
        # Ensure score is within bounds
        engagement_score = max(0, min(100, engagement_score))
        
        return engagement_score
    
    def predict_status(self, engagement_score):
        """Convert engagement score to status"""
        if engagement_score >= 70:
            return "On Track"
        elif engagement_score >= 40:
            return "At Risk"
        else:
            return "Will Drop Off"
    
    def save_model(self, filepath):
        """Save the trained model"""
        joblib.dump({
            'model': self.model,
            'scaler': self.scaler,
            'imputer': self.imputer,
            'feature_names': self.feature_names
        }, filepath)
    
    def load_model(self, filepath):
        """Load a trained model"""
        data = joblib.load(filepath)
        self.model = data['model']
        self.scaler = data['scaler']
        self.imputer = data['imputer']
        self.feature_names = data['feature_names']