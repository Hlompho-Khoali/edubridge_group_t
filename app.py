import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, User, Admin, Educator, Parent, Learner, Game, TestAssignment, TestResult
from utils.games_data import get_all_games
from utils.validators import validate_rsa_id, calculate_age, validate_learner_age, determine_grade_from_age
from datetime import datetime
import json

# Load environment variables
load_dotenv()

# Create Flask app
app = Flask(__name__)

# Configuration
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///database.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SESSION_COOKIE_SECURE'] = os.environ.get('RENDER', 'false').lower() == 'true'
app.config['REMEMBER_COOKIE_SECURE'] = os.environ.get('RENDER', 'false').lower() == 'true'

# Initialize extensions
db.init_app(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Custom Jinja2 filter
@app.template_filter('fromjson')
def from_json_filter(value):
    if value:
        try:
            return json.loads(value)
        except:
            return []
    return []

# ==================== INITIALIZATION FUNCTION ====================

def init_db():
    """Initialize database with admin user and games"""
    with app.app_context():
        # Create tables
        db.create_all()
        
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
            
            # Create admin profile
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
        role = request.form.get('role')
        
        user = None
        
        # Try to find user by email first
        user = User.query.filter_by(email=email_or_id).first()
        
        # If not found and role is learner, try to find by learner ID number
        if not user and role == 'learner':
            learner = Learner.query.filter_by(id_number=email_or_id).first()
            if learner:
                user = learner.user
        
        if user and user.check_password(password) and user.role == role:
            login_user(user)
            
            if role == 'educator':
                return redirect(url_for('educator_dashboard'))
            elif role == 'parent':
                return redirect(url_for('parent_dashboard'))
            elif role == 'learner':
                return redirect(url_for('learner_dashboard'))
            elif role == 'admin':
                return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials or role mismatch', 'error')
    
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

@app.route('/register/learner', methods=['GET', 'POST'])
def register_learner():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        id_number = request.form.get('id_number')
        grade = int(request.form.get('grade'))
        parent_id_number = request.form.get('parent_id')
        password = request.form.get('password')
        
        # Validate email
        if not email or '@' not in email:
            flash('Please enter a valid email address', 'error')
            return redirect(url_for('register_learner'))
        
        # Check if email already exists
        if User.query.filter_by(email=email).first():
            flash('Email already registered. Please use a different email.', 'error')
            return redirect(url_for('register_learner'))
        
        # Validate grade
        if grade not in [1, 2, 3]:
            flash('Please select a valid grade (1-3)', 'error')
            return redirect(url_for('register_learner'))
        
        # Validate RSA ID
        is_valid, result = validate_rsa_id(id_number)
        if not is_valid:
            flash(result, 'error')
            return redirect(url_for('register_learner'))
        
        date_of_birth = result
        age = calculate_age(date_of_birth)
        
        # Validate age (6-12 years old)
        is_valid_age, age_message = validate_learner_age(age)
        if not is_valid_age:
            flash(age_message, 'error')
            return redirect(url_for('register_learner'))
        
        # Find parent
        parent = Parent.query.filter_by(id_number=parent_id_number).first()
        if not parent:
            flash('Parent ID number not found. Please check with your parent.', 'error')
            return redirect(url_for('register_learner'))
        
        # Check if learner ID already exists
        if Learner.query.filter_by(id_number=id_number).first():
            flash('ID number already registered', 'error')
            return redirect(url_for('register_learner'))
        
        # Check if learner with this email already exists
        if Learner.query.filter_by(email=email).first():
            flash('Email already registered as learner', 'error')
            return redirect(url_for('register_learner'))
        
        # Create user account
        user = User(email=email, name=name, role='learner')
        user.set_password(password)
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
            parent_id=parent.id
        )
        db.session.add(learner)
        db.session.commit()
        
        flash(f'Registration successful! You are {age} years old and registered for Grade {grade}. You can login with your email: {email}', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_learner.html')

# ==================== PROFILE ROUTES ====================

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
        flash('Admin accounts cannot be deleted through this interface', 'error')
        return redirect(url_for('view_profile'))
    
    logout_user()
    db.session.delete(user)
    db.session.commit()
    
    flash('Your account has been deleted successfully', 'success')
    return redirect(url_for('index'))

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
        'total_in_progress': len([a for a in assignments if a.status == 'in_progress']),
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

@app.route('/admin/user/edit/<int:user_id>', methods=['GET', 'POST'])
@login_required
def admin_edit_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    
    if user.role == 'educator':
        profile = Educator.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.phone_number = request.form.get('phone_number')
            profile.grade_teaching = int(request.form.get('grade_teaching'))
            profile.qualification = request.form.get('qualification')
            profile.school = request.form.get('school')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash(f'User {user.name} updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        
        return render_template('admin_edit_user.html', user=user, profile=profile)
    
    elif user.role == 'parent':
        profile = Parent.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.occupation = request.form.get('occupation')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash(f'User {user.name} updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        
        return render_template('admin_edit_user.html', user=user, profile=profile)
    
    elif user.role == 'learner':
        profile = Learner.query.filter_by(user_id=user.id).first()
        if request.method == 'POST':
            user.name = request.form.get('name')
            user.email = request.form.get('email')
            user.phone = request.form.get('phone')
            user.address = request.form.get('address')
            profile.grade = int(request.form.get('grade'))
            profile.school = request.form.get('school')
            
            new_password = request.form.get('new_password')
            if new_password:
                user.set_password(new_password)
            
            db.session.commit()
            flash(f'User {user.name} updated successfully!', 'success')
            return redirect(url_for('admin_users'))
        
        return render_template('admin_edit_user.html', user=user, profile=profile)
    
    else:
        flash('Cannot edit this user type', 'error')
        return redirect(url_for('admin_users'))

@app.route('/admin/user/delete/<int:user_id>')
@login_required
def admin_delete_user(user_id):
    if current_user.role != 'admin':
        return redirect(url_for('login'))
    
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot delete another admin user', 'error')
    else:
        db.session.delete(user)
        db.session.commit()
        flash(f'User {user.name} has been deleted', 'success')
    
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
        flash('Unauthorized access', 'error')
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
        flash('This test is already assigned to this student', 'warning')
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

@app.route('/learner/dashboard')
@login_required
def learner_dashboard():
    if current_user.role != 'learner':
        return redirect(url_for('login'))
    
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
    
    available_tests = []
    completed_tests = []
    
    for assignment in assignments:
        game = Game.query.get(assignment.game_id)
        result = TestResult.query.filter_by(assignment_id=assignment.id).first()
        
        if result:
            completed_tests.append({
                'assignment': assignment,
                'game': game,
                'result': result
            })
        else:
            if assignment.status == 'in_progress' and assignment.started_at:
                time_elapsed = (datetime.utcnow() - assignment.started_at).total_seconds()
                if time_elapsed > 3600:
                    assignment.status = 'expired'
                    db.session.commit()
                    continue
            
            available_tests.append({
                'assignment': assignment,
                'game': game
            })
    
    return render_template('learner_dashboard.html', 
                         learner=learner,
                         available_tests=available_tests,
                         completed_tests=completed_tests)

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
    
    flash(f'Test submitted! You scored {earned_points}/{total_points} ({percentage:.1f}%)', 'success')
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
        assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
        results = []
        for assignment in assignments:
            result = TestResult.query.filter_by(assignment_id=assignment.id).first()
            if result:
                results.append({
                    'assignment': assignment,
                    'result': result,
                    'game': assignment.game,
                    'educator': assignment.educator
                })
        
        total_tests = len(results)
        passed_tests = len([r for r in results if r['result'].passed])
        avg_score = sum([r['result'].percentage for r in results]) / total_tests if total_tests > 0 else 0
        
        pending_assignments = []
        for assignment in assignments:
            if assignment.status != 'completed':
                pending_assignments.append({
                    'assignment': assignment,
                    'game': assignment.game,
                    'educator': assignment.educator
                })
        
        learners_data.append({
            'learner': learner,
            'results': results,
            'pending_assignments': pending_assignments,
            'pending_count': len(pending_assignments),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'avg_score': avg_score
        })
    
    return render_template('parent_dashboard.html', learners_data=learners_data)

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

@app.route('/games/public')
@login_required
def view_public_games():
    if current_user.role != 'learner':
        return redirect(url_for('view_all_games'))
    
    games = Game.query.all()
    return render_template('public_games.html', games=games)

# ==================== AI ANALYSIS ROUTE ====================

def generate_ai_analysis(test_results, learner):
    """Generate AI-powered analysis of test results"""
    
    if not test_results:
        return {
            'summary': {
                'total_tests': 0,
                'average_score': 0,
                'best_score': 0,
                'lowest_score': 0,
                'improving': None
            },
            'category_analysis': {},
            'strengths': [{'message': 'Complete your first test to see your strengths!'}],
            'weaknesses': [],
            'overall_assessment': "Welcome to EduBridge! Take your first test to get personalized AI analysis of your learning patterns.",
            'recommendations': [
                {
                    'priority': 'High',
                    'area': 'Getting Started',
                    'recommendation': 'Complete your first assigned test to begin your learning journey!',
                    'action': 'Go to your dashboard and start an available test',
                    'expected_improvement': 'Unlock personalized insights'
                }
            ],
            'motivation': "Ready to start learning? Complete your first test and I'll help you understand your results!",
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    # Skill descriptions
    skill_descriptions = {
        'Mathematics': {
            'name': 'Math & Processing Speed',
            'description': 'How quickly and accurately you solve math problems',
            'tips': ['Practice mental math daily', 'Use flashcards for quick recall', 'Play number games']
        },
        'Pattern Recognition': {
            'name': 'Pattern Recognition',
            'description': 'Ability to identify patterns and sequences',
            'tips': ['Play pattern matching games', 'Practice completing sequences', 'Look for patterns in everyday life']
        },
        'Memory': {
            'name': 'Working Memory',
            'description': 'Ability to hold and use information temporarily',
            'tips': ['Play memory matching games', 'Practice recalling sequences', 'Use visualization techniques']
        },
        'Attention': {
            'name': 'Attention & Focus',
            'description': 'Ability to concentrate and ignore distractions',
            'tips': ['Use a timer for focused work', 'Take short breaks between tasks', 'Create a quiet study space']
        },
        'General': {
            'name': 'General Learning',
            'description': 'Overall learning abilities',
            'tips': ['Practice regularly', 'Get enough sleep', 'Stay positive']
        }
    }
    
    # Calculate overall performance
    scores = [r['percentage'] for r in test_results]
    avg_score = sum(scores) / len(scores)
    
    # Analyze by category
    category_scores = {}
    category_counts = {}
    
    for result in test_results:
        if result['game']:
            category = result['game'].category
            score = result['percentage']
            
            if category not in category_scores:
                category_scores[category] = []
                category_counts[category] = 0
            
            category_scores[category].append(score)
            category_counts[category] += 1
    
    # Build category analysis
    category_analysis = {}
    for category, scores_list in category_scores.items():
        avg = sum(scores_list) / len(scores_list)
        skill_info = skill_descriptions.get(category, skill_descriptions['General'])
        
        if avg >= 70:
            level = 'Strong'
            explanation = f"You're doing very well in {skill_info['name']}! {skill_info['description']}"
        elif avg >= 50:
            level = 'Developing'
            explanation = f"You're making good progress in {skill_info['name']}. {skill_info['description']} With more practice, you'll get even better."
        else:
            level = 'Needs Attention'
            explanation = f"{skill_info['name']} is an area to focus on. {skill_info['description']} Don't worry - with practice, you can improve!"
        
        category_analysis[category] = {
            'name': skill_info['name'],
            'average': round(avg, 1),
            'level': level,
            'explanation': explanation,
            'tips': skill_info['tips'],
            'tests_taken': category_counts[category]
        }
    
    # Identify strengths
    strengths = []
    for category, data in category_analysis.items():
        if data['average'] >= 65:
            strengths.append({
                'category': category,
                'name': data['name'],
                'score': data['average'],
                'message': f"You excel at {data['name']}! Keep up the great work."
            })
    strengths.sort(key=lambda x: x['score'], reverse=True)
    strengths = strengths[:3] if strengths else [{'message': 'Complete more tests to identify your strengths!'}]
    
    # Identify weaknesses
    weaknesses = []
    for category, data in category_analysis.items():
        if data['average'] < 55:
            weaknesses.append({
                'category': category,
                'name': data['name'],
                'score': data['average'],
                'message': f"Let's work on {data['name']}. With practice, you can improve significantly!",
                'tips': data['tips'][:2]
            })
    weaknesses.sort(key=lambda x: x['score'])
    weaknesses = weaknesses[:3] if weaknesses else []
    
    # Check if improving
    improving = None
    if len(scores) >= 3:
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / mid
        second_half_avg = sum(scores[mid:]) / (len(scores) - mid)
        improving = second_half_avg > first_half_avg
    
    # Generate overall assessment
    if avg_score >= 80:
        overall_assessment = "Excellent work! Your performance is outstanding. You're mastering the material very well. Keep challenging yourself!"
    elif avg_score >= 70:
        overall_assessment = "Great job! You're performing above average. Your learning strategies are working well. Keep up the consistent effort!"
    elif avg_score >= 60:
        overall_assessment = "Good progress! You're on the right track. With a bit more practice in specific areas, you'll see even better results."
    elif avg_score >= 50:
        overall_assessment = "You're making progress! Some areas need more attention, but you're building a solid foundation. Stay persistent!"
    else:
        overall_assessment = "Learning takes time and practice. Don't be discouraged! Let's focus on specific areas where small improvements can make a big difference."
    
    # Generate recommendations
    recommendations = []
    
    for weakness in weaknesses[:2]:
        recommendations.append({
            'priority': 'High',
            'area': weakness['name'],
            'recommendation': f"Focus on {weakness['name']}. {weakness['tips'][0]}",
            'action': f"Practice {weakness['category']} games 2-3 times per week",
            'expected_improvement': "You could see significant improvement within 2-3 weeks"
        })
    
    if strengths and strengths[0].get('category'):
        recommendations.append({
            'priority': 'Medium',
            'area': strengths[0]['name'],
            'recommendation': f"Build on your strength in {strengths[0]['name']}! Try more challenging games in this category.",
            'action': "Challenge yourself with advanced level games",
            'expected_improvement': "Continue to excel and build confidence"
        })
    
    if learner.age <= 7:
        recommendations.append({
            'priority': 'Low',
            'area': 'Learning Style',
            'recommendation': "Young learners benefit from hands-on activities and visual learning.",
            'action': "Use colorful materials and physical activities while learning",
            'expected_improvement': "More engaging and enjoyable learning"
        })
    else:
        recommendations.append({
            'priority': 'Low',
            'area': 'Study Habits',
            'recommendation': f"At age {learner.age}, short focused sessions work best. Try 15-20 minute practice sessions.",
            'action': "Use a timer and take short breaks",
            'expected_improvement': "Better focus and retention"
        })
    
    # Generate motivational message
    if avg_score >= 80:
        motivation = "Amazing work! You're showing excellent understanding. Keep challenging yourself!"
    elif avg_score >= 70:
        motivation = "Great progress! Your hard work is paying off. Keep going!"
    elif avg_score >= 60:
        motivation = "You're on the right track! Consistent practice will help you reach your goals."
    elif avg_score >= 50:
        motivation = "You're making progress! Every test helps you learn and grow. Stay determined!"
    else:
        motivation = "Learning is a journey. Every test teaches you something new. Don't give up - you've got this!"
    
    return {
        'summary': {
            'total_tests': len(test_results),
            'average_score': round(avg_score, 1),
            'best_score': max(scores),
            'lowest_score': min(scores),
            'improving': improving
        },
        'category_analysis': category_analysis,
        'strengths': strengths,
        'weaknesses': weaknesses,
        'overall_assessment': overall_assessment,
        'recommendations': recommendations,
        'motivation': motivation,
        'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
    }

@app.route('/ai/analysis')
@login_required
def ai_analysis():
    """AI-powered learning analysis dashboard"""
    if current_user.role != 'learner':
        flash('AI analysis is only available for learners', 'warning')
        return redirect(url_for('learner_dashboard'))
    
    learner = Learner.query.filter_by(user_id=current_user.id).first()
    if not learner:
        flash('Learner profile not found', 'error')
        return redirect(url_for('learner_dashboard'))
    
    assignments = TestAssignment.query.filter_by(learner_id=learner.id).all()
    test_results = []
    
    for assignment in assignments:
        result = TestResult.query.filter_by(assignment_id=assignment.id).first()
        if result:
            game = Game.query.get(assignment.game_id)
            test_results.append({
                'result': result,
                'game': game,
                'percentage': result.percentage,
                'score': result.score,
                'passed': result.passed,
                'date': result.completed_at
            })
    
    analysis = generate_ai_analysis(test_results, learner)
    
    return render_template('ai_analysis.html', 
                         learner=learner,
                         analysis=analysis,
                         test_results=test_results)

# ==================== LOGOUT ROUTE ====================

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

# ==================== RUN THE APP ====================

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    debug_mode = os.environ.get('RENDER', 'false').lower() != 'true'
    app.run(debug=debug_mode, host='0.0.0.0', port=port)