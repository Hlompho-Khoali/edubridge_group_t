from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import json

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.String(200), nullable=True)
    profile_picture = db.Column(db.String(200), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Admin(db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    employee_id = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100), nullable=True)
    
    user = db.relationship('User', backref='admin_profile')

class Educator(db.Model):
    __tablename__ = 'educators'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)
    grade_teaching = db.Column(db.Integer, nullable=False)
    qualification = db.Column(db.String(100), nullable=True)
    school = db.Column(db.String(100), nullable=True)
    
    user = db.relationship('User', backref='educator_profile')

class Parent(db.Model):
    __tablename__ = 'parents'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    id_number = db.Column(db.String(13), unique=True, nullable=False)
    occupation = db.Column(db.String(100), nullable=True)
    
    user = db.relationship('User', backref='parent_profile')
    learners = db.relationship('Learner', backref='parent', lazy='dynamic')

class Learner(db.Model):
    __tablename__ = 'learners'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    id_number = db.Column(db.String(13), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    date_of_birth = db.Column(db.DateTime, nullable=False)
    age = db.Column(db.Integer, nullable=False)
    grade = db.Column(db.Integer, nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('parents.id'), nullable=False)
    school = db.Column(db.String(100), nullable=True)
    
    login_code = db.Column(db.String(6), unique=True, nullable=True)
    # Phase tracking
    current_phase = db.Column(db.Integer, default=1)  # ← MUST HAVE INDENTATION (4 spaces)
    phase1_completed = db.Column(db.Boolean, default=False)
    phase2_completed = db.Column(db.Boolean, default=False)
    phase3_completed = db.Column(db.Boolean, default=False)
    completed_game_ids = db.Column(db.Text, default='[]')
    last_break_time = db.Column(db.DateTime, nullable=True)
    games_since_break = db.Column(db.Integer, default=0)
    
    user = db.relationship('User', backref='learner_profile')

class Game(db.Model):
    __tablename__ = 'games'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(500), nullable=False)
    category = db.Column(db.String(50), nullable=False)
    questions = db.Column(db.Text, nullable=False)
    passing_score = db.Column(db.Integer, default=15)
    time_limit_minutes = db.Column(db.Integer, default=60)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_questions(self):
        return json.loads(self.questions)
    
    def set_questions(self, questions):
        self.questions = json.dumps(questions)

class TestAssignment(db.Model):
    __tablename__ = 'test_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('games.id'), nullable=False)
    educator_id = db.Column(db.Integer, db.ForeignKey('educators.id'), nullable=False)
    learner_id = db.Column(db.Integer, db.ForeignKey('learners.id'), nullable=False)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='pending')
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    game = db.relationship('Game')
    educator = db.relationship('Educator')
    learner = db.relationship('Learner')

class TestResult(db.Model):
    __tablename__ = 'test_results'
    
    id = db.Column(db.Integer, primary_key=True)
    assignment_id = db.Column(db.Integer, db.ForeignKey('test_assignments.id'), nullable=False)
    score = db.Column(db.Integer, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    passed = db.Column(db.Boolean, nullable=False)
    answers = db.Column(db.Text, nullable=True)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    assignment = db.relationship('TestAssignment')
    
    def get_answers(self):
        return json.loads(self.answers) if self.answers else []
    
    def set_answers(self, answers):
        self.answers = json.dumps(answers)

    class CognitiveAssessment(db.Model):
    __tablename__ = 'cognitive_assessments'
    
    id = db.Column(db.Integer, primary_key=True)
    learner_id = db.Column(db.Integer, db.ForeignKey('learners.id'), nullable=False)
    assessment_date = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Cognitive domain scores (0-100)
    attention_score = db.Column(db.Float, default=0)
    impulse_control_score = db.Column(db.Float, default=0)
    working_memory_score = db.Column(db.Float, default=0)
    processing_speed_score = db.Column(db.Float, default=0)
    problem_solving_score = db.Column(db.Float, default=0)
    language_score = db.Column(db.Float, default=0)
    
    # ADHD indicators
    adhd_risk_score = db.Column(db.Float, default=0)  # 0-100, higher = more indicators
    attention_deficit_risk = db.Column(db.Float, default=0)
    hyperactivity_risk = db.Column(db.Float, default=0)
    impulsivity_risk = db.Column(db.Float, default=0)
    
    # Percentile rankings (compared to same age group)
    attention_percentile = db.Column(db.Float, default=50)
    memory_percentile = db.Column(db.Float, default=50)
    
    # Recommendations (JSON)
    recommendations = db.Column(db.Text, default='[]')
    strengths = db.Column(db.Text, default='[]')
    concerns = db.Column(db.Text, default='[]')
    
    # Report text
    summary_report = db.Column(db.Text, default='')
    
    learner = db.relationship('Learner', backref='assessments')
    