import os
from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Admin, Educator, Parent, Learner, Game, TestAssignment, TestResult, CognitiveAssessment
from utils.games_data import get_all_games
from utils.validators import validate_rsa_id, calculate_age, validate_learner_age, determine_grade_from_age
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Database configuration for PostgreSQL on Render
DATABASE_URL = os.environ.get('DATABASE_URL')

if DATABASE_URL:
    # Fix for PostgreSQL URL (Render uses postgres:// not postgresql://)
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER', 'false').lower() == 'true'
app.config['REMEMBER_COOKIE_SECURE'] = os.environ.get('RENDER', 'false').lower() == 'true'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Custom Jinja2 filter
@app.template_filter('fromjson')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except:
            return []
    return []

# Initialize database with app context
with app.app_context():
    db.create_all()
    print("Database tables created/verified")
    
    # Create super admin if not exists
    admin_user = User.query.filter_by(email='admin@edubridge.com').first()
    if not admin_user:
        admin_user = User(
            email='admin@edubridge.com',
            name='Super Admin',
            role='admin'
        )
        admin_user.set_password('admin123')
        db.session.add(admin_user)
        db.session.flush()
        
        admin_profile = Admin(
            user_id=admin_user.id,
            employee_id='ADMIN001',
            department='System Administration'
        )
        db.session.add(admin_profile)
        db.session.commit()
        print("Super Admin created: admin@edubridge.com / admin123")
    
    # Add default games if not exists
    games_data = get_all_games()
    for game_data in games_data:
        game = Game.query.filter_by(name=game_data['name']).first()
        if not game:
            game = Game(
                name=game_data['name'],
                description=game_data['description'],
                category=game_data.get('category', 'General'),
                questions=json.dumps(game_data['questions']),
                passing_score=15,
                time_limit_minutes=60
            )
            db.session.add(game)
    
    db.session.commit()
    print(f"Database initialized with {len(games_data)} games")

# ==================== AUTHENTICATION ROUTES ====================

@app.route('/')
def index():
    games_count = Game.query.count()
    return render_template('index.html', games_count=games_count)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email_or_id = request.form.get('email')
        password = request.form.get('password')
        
        # Try to find user by email
        user = User.query.filter_by(email=email_or_id).first()
        
        # If not found and it might be a learner ID number
        if not user and email_or_id.isdigit() and len(email_or_id) == 13:
            learner = Learner.query.filter_by(id_number=email_or_id).first()
            if learner:
                user = learner.user
        
        # Check password and login
        if user and user.check_password(password):
            login_user(user)
            
            # Redirect based on role
            if user.role == 'educator':
                return redirect(url_for('educator_dashboard'))
            elif user.role == 'parent':
                return redirect(url_for('parent_dashboard'))
            elif user.role == 'learner':
                return redirect(url_for('learner_dashboard'))
            elif user.role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('login.html')

@app.route('/register/educator', methods=['GET', 'POST'])
def register_educator():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        grade = int(request.form.get('grade'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register_educator'))
        
        user = User(email=email, name=name, role='educator')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        educator = Educator(user_id=user.id, phone_number=phone, grade_teaching=grade)
        db.session.add(educator)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_educator.html')

@app.route('/register/parent', methods=['GET', 'POST'])
def register_parent():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        id_number = request.form.get('id_number')
        password = request.form.get('password')
        
        is_valid, result = validate_rsa_id(id_number)
        if not is_valid:
            flash(result, 'error')
            return redirect(url_for('register_parent'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'error')
            return redirect(url_for('register_parent'))
        
        if Parent.query.filter_by(id_number=id_number).first():
            flash('ID number already registered', 'error')
            return redirect(url_for('register_parent'))
        
        user = User(email=email, name=name, role='parent')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        parent = Parent(user_id=user.id, id_number=id_number)
        db.session.add(parent)
        db.session.commit()
        
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_parent.html')



# ==================== PROFILE ROUTES ====================
@app.route('/learner-login', methods=['GET', 'POST'])
def learner_login():
    if request.method == 'POST':
        # Combine the 6 digits
        code = ''.join([request.form.get(f'digit{i}') for i in range(1, 7)])
        
        # Find learner by code
        learner = Learner.query.filter_by(login_code=code).first()
        
        if learner:
            # Log them in
            login_user(learner.user)
            flash(f'Welcome back, {learner.user.name}! ', 'success')
            return redirect(url_for('learner_dashboard'))
        else:
            flash('Invalid code! Please check with your teacher or parent.', 'error')
    
    return render_template('learner_login.html')
@app.route('/profile')
@login_required
def view_profile():
    user = current_user
    
    if user.role == 'educator':
        profile = Educator.query.filter_by(user_id=user.id).first()
        return render_template('profile.html', user=user, profile=profile, role_data=profile)
    elif user.role == 'parent':
        profile = Parent.query.filter_by(user_id=user.id).first()
        return render_template('profile.html', user=user, profile=profile, role_data=profile)
    elif user.role == 'learner':
        profile = Learner.query.filter_by(user_id=user.id).first()
        return render_template('profile.html', user=user, profile=profile, role_data=profile)
    elif user.role == 'admin':
        profile = Admin.query.filter_by(user_id=user.id).first()
        return render_template('profile.html', user=user, profile=profile, role_data=profile)
    
    return render_template('profile.html', user=user, profile=None, role_data=None)

@app.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user
    
    if user.role == 'educator':
        profile = Educator.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.phone_number = request.form.get('phone_number')
            profile.qualification = request.form.get('qualification')
            profile.school = request.form.get('school')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('view_profile'))
        
        return render_template('edit_profile.html', user=user, profile=profile)
    
    elif user.role == 'parent':
        profile = Parent.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.occupation = request.form.get('occupation')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('view_profile'))
        
        return render_template('edit_profile.html', user=user, profile=profile)
    
    elif user.role == 'learner':
        profile = Learner.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.school = request.form.get('school')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('view_profile'))
        
        return render_template('edit_profile.html', user=user, profile=profile)
    
    elif user.role == 'admin':
        profile = Admin.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.department = request.form.get('department')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('view_profile'))
        
        return render_template('edit_profile.html', user=user, profile=profile)
    
    return redirect(url_for('index'))

@app.route('/profile/delete', methods=['POST'])
@login_required
def delete_profile():
    user = current_user
    role = user.role
    
    if role == 'admin':
        flash('Admin accounts cannot be deleted', 'error')
        return redirect(url_for('view_profile'))
    
    try:
        user_id = user.id
        
        if role == 'educator':
            profile = Educator.query.filter_by(user_id=user_id).first()
            if profile:
                db.session.delete(profile)
        elif role == 'parent':
            profile = Parent.query.filter_by(user_id=user_id).first()
            if profile:
                db.session.delete(profile)
        elif role == 'learner':
            profile = Learner.query.filter_by(user_id=user_id).first()
            if profile:
                db.session.delete(profile)
        
        db.session.commit()
        
        user_to_delete = User.query.get(user_id)
        if user_to_delete:
            db.session.delete(user_to_delete)
            db.session.commit()
        
        logout_user()
        flash('Your account has been deleted', 'success')
        return redirect(url_for('index'))
        
    except Exception as e:
        db.session.rollback()
        flash('An error occurred', 'error')
        return redirect(url_for('view_profile'))

# ==================== ADMIN ROUTES ====================

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    admin_profile = Admin.query.filter_by(user_id=current_user.id).first()
    educators = Educator.query.all()
    parents = Parent.query.all()
    learners = Learner.query.all()
    games = Game.query.all()
    assignments = TestAssignment.query.all()
    results = TestResult.query.all()
    
    stats = {
        'total_educators': len(educators),
        'total_parents': len(parents),
        'total_learners': len(learners),
        'total_games': len(games),
        'total_assignments': len(assignments),
        'total_completed': len(results),
        'total_pending': len([a for a in assignments if a.status == 'pending']),
        'avg_score': sum([r.percentage for r in results]) / len(results) if results else 0,
        'pass_rate': len([r for r in results if r.passed]) / len(results) * 100 if results else 0
    }
    
    return render_template('admin_dashboard.html', stats=stats, admin_profile=admin_profile)

@app.route('/admin/users')
@login_required
def admin_users():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    educators = Educator.query.all()
    parents = Parent.query.all()
    learners = Learner.query.all()
    
    return render_template('admin_users.html', educators=educators, parents=parents, learners=learners)

@app.route('/admin/games')
@login_required
def admin_games():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    games = Game.query.all()
    return render_template('admin_games.html', games=games)

@app.route('/admin/results')
@login_required
def admin_results():
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    results = TestResult.query.all()
    results_data = []
    for result in results:
        assignment = result.assignment
        results_data.append({
            'result': result,
            'assignment': assignment,
            'game': assignment.game,
            'learner': assignment.learner,
            'educator': assignment.educator
        })
    
    return render_template('admin_results.html', results_data=results_data)

@app.route('/admin/user/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot delete your own admin account', 'error')
        return redirect(url_for('admin_users'))
    
    if user.role == 'admin':
        flash('Cannot delete other admin users', 'error')
        return redirect(url_for('admin_users'))
    
    try:
        if user.role == 'learner':
            learner = Learner.query.filter_by(user_id=user.id).first()
            if learner:
                assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
                for assignment in assignments:
                    TestResult.query.filter_by(assignment_id=assignment.id).delete()
                    db.session.delete(assignment)
                db.session.delete(learner)
        elif user.role == 'parent':
            parent = Parent.query.filter_by(user_id=user.id).first()
            if parent:
                learners = Learner.query.filter_by(parent_id=parent.id).all()
                for learner in learners:
                    assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
                    for assignment in assignments:
                        TestResult.query.filter_by(assignment_id=assignment.id).delete()
                        db.session.delete(assignment)
                    db.session.delete(learner)
                db.session.delete(parent)
        elif user.role == 'educator':
            educator = Educator.query.filter_by(user_id=user.id).first()
            if educator:
                assignments = TestAssignment.query.filter_by(educator_id=educator.id).all()
                for assignment in assignments:
                    db.session.delete(assignment)
                db.session.delete(educator)
        
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.name} deleted', 'success')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error: {str(e)}', 'error')
    
    return redirect(url_for('admin_users'))

# ==================== EDUCATOR ROUTES ====================

@app.route('/educator/dashboard')
@login_required
def educator_dashboard():
    if current_user.role != 'educator':
        return redirect(url_for('login'))
    
    educator = Educator.query.filter_by(user_id=current_user.id).first()
    learners = Learner.query.filter_by(grade=educator.grade_teaching).all()
    assignments = TestAssignment.query.filter_by(educator_id=educator.id).all()
    games = Game.query.all()
    
    assignments_with_results = []
    for assignment in assignments:
        result = TestResult.query.filter_by(assignment_id=assignment.id).first()
        assignments_with_results.append({
            'assignment': assignment,
            'result': result
        })
    
    return render_template('educator_dashboard.html', 
                         educator=educator,
                         learners=learners, 
                         assignments=assignments_with_results,
                         games=games)

@app.route('/educator/assign_test', methods=['POST'])
@login_required
def assign_test():
    if current_user.role != 'educator':
        flash('Unauthorized', 'error')
        return redirect(url_for('login'))
    
    educator = Educator.query.filter_by(user_id=current_user.id).first()
    learner_id = request.form.get('learner_id')
    game_id = request.form.get('game_id')
    
    existing = TestAssignment.query.filter_by(
        game_id=game_id,
        learner_id=learner_id,
        educator_id=educator.id,
        status='pending'
    ).first()
    
    if existing:
        flash('Test already assigned', 'warning')
    else:
        assignment = TestAssignment(
            game_id=game_id,
            educator_id=educator.id,
            learner_id=learner_id,
            status='pending'
        )
        db.session.add(assignment)
        db.session.commit()
        flash('Test assigned successfully!', 'success')
    
    return redirect(url_for('educator_dashboard'))

# ==================== LEARNER ROUTES ====================
@app.route('/parent/add-learner', methods=['POST'])
@login_required
def parent_add_learner():
    if current_user.role != 'parent':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    name = request.form.get('name')
    email = request.form.get('email')
    id_number = request.form.get('id_number')
    grade = int(request.form.get('grade'))
    
    parent = Parent.query.filter_by(user_id=current_user.id).first()
    
    # Check if email already exists
    if User.query.filter_by(email=email).first():
        flash('Email already registered', 'error')
        return redirect(url_for('parent_dashboard'))
    
    # Validate ID number
    is_valid, result = validate_rsa_id(id_number)
    if not is_valid:
        flash(result, 'error')
        return redirect(url_for('parent_dashboard'))
    
    date_of_birth = result
    age = calculate_age(date_of_birth)
    
    # Check if learner already exists
    if Learner.query.filter_by(id_number=id_number).first():
        flash('ID number already registered', 'error')
        return redirect(url_for('parent_dashboard'))
    
    # Generate 6-digit login code
    import random
    import string
    def generate_code():
        return ''.join(random.choices(string.digits, k=6))
    
    login_code = generate_code()
    while Learner.query.filter_by(login_code=login_code).first():
        login_code = generate_code()
    
    # Create user account
    user = User(email=email, name=name, role='learner')
    user.set_password(login_code)  # Use code as temporary password
    db.session.add(user)
    db.session.flush()
    
    # Create learner profile
    learner = Learner(
        user_id=user.id,
        email=email,
        id_number=id_number,
        date_of_birth=date_of_birth,
        age=age,
        grade=grade,
        parent_id=parent.id,
        login_code=login_code
    )
    db.session.add(learner)
    db.session.commit()
    
    # Show the code on a dedicated page instead of flashing
    return render_template('learner_code_display.html', 
                           login_code=login_code, 
                           learner_name=name, 
                           grade=grade)

@app.route('/learner/dashboard')
@login_required
def learner_dashboard():
    
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
        # Auto-load all games as learning path (no teacher assignment required)
    all_games = Game.query.all()
    
    available_tests = []
    completed_tests = []
    
    for game in all_games:
        # Check if learner has already completed this game
        existing_assignment = TestAssignment.query.filter_by(
            learner_id=learner.id, 
            game_id=game.id
        ).first()
        
        # Check for existing result
        result = None
        if existing_assignment:
            result = TestResult.query.filter_by(assignment_id=existing_assignment.id).first()
        
        if result:
            completed_tests.append({
                'assignment': existing_assignment,
                'game': game,
                'result': result
            })
        else:
            # Game is available to play (auto-learning path)
            available_tests.append({
                'assignment': existing_assignment,
                'game': game
            })
    
    return render_template('learner_dashboard.html', 
                         learner=learner,
                         available_tests=available_tests,
                         completed_tests=completed_tests)
@app.route('/game/memory-match')
@login_required
def memory_match_game():
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    return render_template('game_memory_match.html')
@app.route('/test/start/<int:assignment_id>')
@login_required
def start_test(assignment_id):
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    assignment = TestAssignment.query.get_or_404(assignment_id)
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    
    if assignment.learner_id != learner.id:
        flash('This test is not assigned to you', 'error')
        return redirect(url_for('learner_dashboard'))
    
    if assignment.status == 'completed':
        flash('You have already completed this test', 'warning')
        return redirect(url_for('learner_dashboard'))
    
    if assignment.status == 'expired':
        flash('This test has expired', 'error')
        return redirect(url_for('learner_dashboard'))
    
    if assignment.status == 'pending':
        assignment.status = 'in_progress'
        assignment.started_at = datetime.utcnow()
        db.session.commit()
    
    game = Game.query.get(assignment.game_id)
    questions = json.loads(game.questions)
    
    return render_template('take_test.html', 
                         assignment=assignment, 
                         game=game, 
                         questions=questions)

@app.route('/test/submit/<int:assignment_id>', methods=['POST'])
@login_required
def submit_test(assignment_id):
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    assignment = TestAssignment.query.get_or_404(assignment_id)
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    
    if assignment.learner_id != learner.id:
        flash('Unauthorized', 'error')
        return redirect(url_for('learner_dashboard'))
    
    if assignment.status == 'completed':
        flash('Test already submitted', 'warning')
        return redirect(url_for('learner_dashboard'))
    
    game = Game.query.get(assignment.game_id)
    questions = json.loads(game.questions)
    
    total_points = 0
    earned_points = 0
    user_answers = []
    
    for i, question in enumerate(questions):
        points = question.get('points', 2)
        total_points += points
        
        user_answer = request.form.get(f'question_{i}')
        user_answers.append(user_answer or 'Not answered')
        
        if user_answer == question['correct']:
            earned_points += points
    
    percentage = (earned_points / total_points) * 100
    passed = percentage >= 50
    
    result = TestResult(
        assignment_id=assignment.id,
        score=earned_points,
        percentage=percentage,
        passed=passed,
        answers=json.dumps(user_answers)
    )
    
    assignment.status = 'completed'
    assignment.completed_at = datetime.utcnow()
    
    db.session.add(result)
    db.session.commit()
    
    flash(f'Test submitted! Score: {earned_points}/{total_points} ({percentage:.1f}%)', 'success')
    return redirect(url_for('test_results', result_id=result.id))

@app.route('/test/results/<int:result_id>')
@login_required
def test_results(result_id):
    result = TestResult.query.get_or_404(result_id)
    assignment = result.assignment
    game = Game.query.get(assignment.game_id)
    questions = json.loads(game.questions)
    user_answers = json.loads(result.answers) if result.answers else []
    
    learner = assignment.learner
    educator = assignment.educator
    
    if current_user.role == 'learner':
        learner_user = Learner.query.filter_by(user_id=current_user.id).first()
        if assignment.learner_id != learner_user.id:
            return redirect(url_for('login'))
    elif current_user.role == 'parent':
        parent = Parent.query.filter_by(user_id=current_user.id).first()
        if learner.parent_id != parent.id:
            return redirect(url_for('login'))
    elif current_user.role == 'educator':
        if assignment.educator_id != educator.id:
            return redirect(url_for('login'))
    
    question_review = []
    for i, question in enumerate(questions):
        user_answer = user_answers[i] if i < len(user_answers) else 'Not answered'
        is_correct = user_answer == question['correct']
        question_review.append({
            'number': i + 1,
            'question': question['question'],
            'user_answer': user_answer,
            'correct_answer': question['correct'],
            'is_correct': is_correct,
            'points': question['points']
        })
    
    return render_template('test_results.html', 
                         result=result, 
                         assignment=assignment, 
                         game=game,
                         learner=learner,
                         educator=educator,
                         question_review=question_review,
                         total_points=len(questions) * 2)

# ==================== PARENT ROUTES ====================

@app.route('/parent/dashboard')
@login_required
def parent_dashboard():
    if current_user.role != 'parent':
        return redirect(url_for('login'))
    
    parent = Parent.query.filter_by(user_id=current_user.id).first()
    learners = Learner.query.filter_by(parent_id=parent.id).all()
    
    learners_data = []
    for learner in learners:
        # Count completed games
        completed_ids = json.loads(learner.completed_game_ids) if learner.completed_game_ids else []
        
        learners_data.append({
            'learner': learner,
            'completed_games': len(completed_ids),
            'total_games': 29
        })
    
    return render_template('parent_dashboard.html', 
                         learners_data=learners_data)
@app.route('/game/penguin-says')
@login_required
def penguin_says_game():
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    return render_template('game_penguin_says.html')

@app.route('/game/red-light')
@login_required
def red_light_game():
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    return render_template('game_red_light.html')

@app.route('/game/save-result', methods=['POST'])
@login_required
def save_game_result():
    if current_user.role != 'learner':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    
    # Create an assignment for this game if it doesn't exist
    game = Game.query.filter_by(name=data.get('game_name')).first()
    if not game:
        return jsonify({'error': 'Game not found'}), 404
    
    # Check if already have result for this game
    existing_assignment = TestAssignment.query.filter_by(
        learner_id=learner.id,
        game_id=game.id
    ).first()
    
    if not existing_assignment:
        # Create new assignment
        assignment = TestAssignment(
            game_id=game.id,
            learner_id=learner.id,
            status='completed',
            completed_at=datetime.utcnow()
        )
        db.session.add(assignment)
        db.session.flush()
        
        # Calculate percentage
        total_points = len(json.loads(game.questions)) * 2 if game.questions else 30
        earned_points = int((data.get('percentage', 0) / 100) * total_points)
        
        # Create result
        result = TestResult(
            assignment_id=assignment.id,
            score=earned_points,
            percentage=data.get('percentage', 0),
            passed=data.get('passed', False),
            answers=json.dumps(['game']),
            completed_at=datetime.utcnow()
        )
        db.session.add(result)
        db.session.commit()
    
    return jsonify({'success': True})
@app.route('/parent/learner-progress/<int:learner_id>')
@login_required
def view_learner_progress(learner_id):
    if current_user.role != 'parent':
        flash('Access denied', 'error')
        return redirect(url_for('login'))
    
    parent = Parent.query.filter_by(user_id=current_user.id).first()
    learner = Learner.query.get_or_404(learner_id)
    
    # Verify this learner belongs to the logged-in parent
    if learner.parent_id != parent.id:
        flash('Access denied', 'error')
        return redirect(url_for('parent_dashboard'))
    
    # Get completed games
    import json
    completed_ids = json.loads(learner.completed_game_ids) if learner.completed_game_ids else []
    
    # Get all games
    games = Game.query.all()
    
    # Calculate progress by category
    categories = {}
    for game in games:
        if game.category not in categories:
            categories[game.category] = {'total': 0, 'completed': 0}
        categories[game.category]['total'] += 1
        if game.id in completed_ids:
            categories[game.category]['completed'] += 1
    
    completed_count = len(completed_ids)
    total_games = len(games)
    percentage = (completed_count / total_games * 100) if total_games > 0 else 0
    
    return render_template('learner_progress.html', 
                         learner=learner,
                         games=games,
                         completed_ids=completed_ids,
                         categories=categories,
                         completed_count=completed_count,
                         total_games=total_games,
                         percentage=percentage)
# ==================== GAMES ROUTES ====================

@app.route('/games')
@login_required
def view_all_games():
    if current_user.role == 'learner':
        flash('Access denied. Learners cannot view the games library.', 'error')
        return redirect(url_for('learner_dashboard'))
    
    games = Game.query.all()
    return render_template('games_list.html', games=games)

@app.route('/games/<int:game_id>')
@login_required
def view_game_details(game_id):
    if current_user.role == 'learner':
        flash('Access denied. Learners cannot view game details.', 'error')
        return redirect(url_for('learner_dashboard'))
    
    game = Game.query.get_or_404(game_id)
    questions = json.loads(game.questions)
    return render_template('game_details.html', game=game, questions=questions)

@app.route('/play/phase/<int:phase>')
@login_required
def play_phase(phase):
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    
    # Define games for each phase
    phase_games = {
        1: [3, 6, 8, 14, 15, 16, 18, 19, 25],  # Brain Boosters
        2: [4, 5, 9, 12, 13, 17, 21, 22, 24, 10],  # Word Explorers
        3: [1, 7, 11, 20, 23, 26, 27, 28, 29, 2]  # Number Heroes
    }
    
    games_list = phase_games.get(phase, [])
    completed_ids = json.loads(learner.completed_game_ids) if learner.completed_game_ids else []
    
    # Find first incomplete game
    current_game_id = None
    for game_id in games_list:
        if game_id not in completed_ids:
            current_game_id = game_id
            break
    
    if not current_game_id:
        flash(f'Phase {phase} is already complete!', 'success')
        return redirect(url_for('learner_dashboard'))
    
    game = Game.query.get(current_game_id)
    
    # Create or get assignment
    assignment = TestAssignment.query.filter_by(
        learner_id=learner.id,
        game_id=current_game_id
    ).first()
    
    if not assignment:
        assignment = TestAssignment(
            game_id=current_game_id,
            learner_id=learner.id,
            educator_id=None,
            status='in_progress',
            started_at=datetime.utcnow()
        )
        db.session.add(assignment)
        db.session.commit()
    
    # Redirect to the appropriate game template
    return redirect(url_for('play_game', game_id=current_game_id, assignment_id=assignment.id)) 

@app.route('/play/game/<int:game_id>/<int:assignment_id>')
@login_required
def play_game(game_id, assignment_id):
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    game = Game.query.get(game_id)
    
    # Map game names to templates
    game_templates = {
        'Memory Match': 'game_memory_match.html',
        'Penguin Says': 'game_penguin_says.html',
        'Red Light, Green Light': 'game_red_light.html'
    }
    
    template = game_templates.get(game.name, 'game_generic.html')
    
    return render_template(template, 
                         game=game, 
                         assignment_id=assignment_id,
                         return_phase=True)

@app.route('/game/complete-and-next', methods=['POST'])
@login_required
def complete_and_next():
    if current_user.role != 'learner':
        return jsonify({'error': 'Unauthorized'}), 403
    
    data = request.get_json()
    game_id = data.get('game_id')
    assignment_id = data.get('assignment_id')
    
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    
    # Mark game as completed
    completed_ids = json.loads(learner.completed_game_ids) if learner.completed_game_ids else []
    if game_id not in completed_ids:
        completed_ids.append(game_id)
        learner.completed_game_ids = json.dumps(completed_ids)
        db.session.commit()
    
    return jsonify({'success': True, 'next_game': True})

@app.route('/games/public')
@login_required
def view_public_games():
    if current_user.role != 'learner':
        return redirect(url_for('view_all_games'))
    
    games = Game.query.all()
    return render_template('public_games.html', games=games)

# ==================== AI ANALYSIS ROUTE ====================

def generate_ai_analysis(test_results, learner):
    if not test_results:
        return {
            'summary': {'total_tests': 0, 'average_score': 0, 'best_score': 0, 'lowest_score': 0, 'improving': None},
            'category_analysis': {},
            'strengths': [{'message': 'Complete your first test to see your strengths!'}],
            'weaknesses': [],
            'overall_assessment': "Welcome to EduBridge! Take your first test to get personalized AI analysis.",
            'recommendations': [{'priority': 'High', 'area': 'Getting Started', 'recommendation': 'Complete your first assigned test', 'action': 'Go to your dashboard', 'expected_improvement': 'Unlock insights'}],
            'motivation': "Ready to start learning? Complete your first test!",
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    scores = [r['percentage'] for r in test_results]
    avg_score = sum(scores) / len(scores)
    
    category_scores = {}
    for result in test_results:
        if result.get('game'):
            category = result['game'].category
            if category not in category_scores:
                category_scores[category] = []
            category_scores[category].append(result['percentage'])
    
    category_analysis = {}
    for category, scores_list in category_scores.items():
        avg = sum(scores_list) / len(scores_list)
        if avg >= 70:
            level = 'Strong'
            explanation = f"You're doing very well in {category}!"
        elif avg >= 50:
            level = 'Developing'
            explanation = f"You're making good progress in {category}."
        else:
            level = 'Needs Attention'
            explanation = f"{category} is an area to focus on."
        
        category_analysis[category] = {
            'name': category,
            'average': round(avg, 1),
            'level': level,
            'explanation': explanation,
            'tips': ['Practice regularly', 'Review mistakes'],
            'tests_taken': len(scores_list)
        }
    
    strengths = []
    weaknesses = []
    for category, data in category_analysis.items():
        if data['average'] >= 65:
            strengths.append({'name': category, 'score': data['average'], 'message': f"You excel at {category}!"})
        elif data['average'] < 55:
            weaknesses.append({'name': category, 'score': data['average'], 'message': f"Let's work on {category}."})
    
    if avg_score >= 70:
        overall = "Excellent work! You're mastering the material very well."
        motivation = "Amazing work! Keep challenging yourself!"
    elif avg_score >= 50:
        overall = "Good progress! You're on the right track."
        motivation = "Great progress! Keep going!"
    else:
        overall = "Learning takes time. Don't be discouraged!"
        motivation = "Every test teaches you something new. Keep trying!"
    
    return {
        'summary': {
            'total_tests': len(test_results),
            'average_score': round(avg_score, 1),
            'best_score': max(scores),
            'lowest_score': min(scores),
            'improving': None
        },
        'category_analysis': category_analysis,
        'strengths': strengths[:3] if strengths else [{'message': 'Complete more tests to identify strengths!'}],
        'weaknesses': weaknesses[:3],
        'overall_assessment': overall,
        'recommendations': [],
        'motivation': motivation,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

@app.route('/ai/analysis')
@login_required
def ai_analysis():
    if current_user.role != 'learner':
        flash('AI analysis is only available for learners', 'warning')
        return redirect(url_for('learner_dashboard'))
    
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    if not learner:
        flash('Learner profile not found', 'error')
        return redirect(url_for('learner_dashboard'))
    
    # Collect all game results
    assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
    game_results = []
    
    for assignment in assignments:
        result = TestResult.query.filter_by(assignment_id=assignment.id).first()
        if result:
            game = Game.query.get(assignment.game_id)
            game_results.append({
                'game_id': game.id,
                'game_name': game.name,
                'percentage': result.percentage,
                'score': result.score,
                'passed': result.passed,
                'reaction_time': 350,  # Placeholder - would come from game data
                'errors': 0,  # Placeholder
                'date': result.completed_at
            })
    
    # Run AI analysis
    from utils.ai_analyzer import AIAnalyzer
    analyzer = AIAnalyzer(learner, game_results)
    analysis = analyzer.analyze()
    
    # Save assessment to database
    import json
    assessment = CognitiveAssessment(
        learner_id=learner.id,
        attention_score=analysis['cognitive_scores'].get('attention', 0) or 0,
        impulse_control_score=analysis['cognitive_scores'].get('impulse_control', 0) or 0,
        working_memory_score=analysis['cognitive_scores'].get('working_memory', 0) or 0,
        processing_speed_score=analysis['cognitive_scores'].get('processing_speed', 0) or 0,
        problem_solving_score=analysis['cognitive_scores'].get('problem_solving', 0) or 0,
        language_score=analysis['cognitive_scores'].get('language', 0) or 0,
        adhd_risk_score=analysis['adhd_indicators']['overall_risk'],
        attention_deficit_risk=analysis['adhd_indicators']['attention_deficit_risk'],
        hyperactivity_risk=analysis['adhd_indicators']['hyperactivity_risk'],
        impulsivity_risk=analysis['adhd_indicators']['impulsivity_risk'],
        recommendations=json.dumps(analysis['recommendations']),
        strengths=json.dumps(analysis['strengths']),
        concerns=json.dumps(analysis['concerns']),
        summary_report=analysis['summary']
    )
    db.session.add(assessment)
    db.session.commit()
    
    return render_template('ai_analysis.html', 
                         learner=learner,
                         analysis=analysis,
                         game_results=game_results,
                         assessment=assessment)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

# ==================== RUN THE APP ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('RENDER', 'false').lower() != 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)