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
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role')
        
        user = User.query.filter_by(email=email).first()
        
        if not user and role == 'learner':
            learner = Learner.query.filter_by(id_number=email).first()
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
        id_number = request.form.get('id_number')
        parent_id_number = request.form.get('parent_id')
        password = request.form.get('password')
        
        is_valid, result = validate_rsa_id(id_number)
        if not is_valid:
            flash(result, 'error')
            return redirect(url_for('register_learner'))
        
        date_of_birth = result
        age = calculate_age(date_of_birth)
        
        is_valid_age, age_message = validate_learner_age(age)
        if not is_valid_age:
            flash(age_message, 'error')
            return redirect(url_for('register_learner'))
        
        grade = determine_grade_from_age(age)
        
        parent = Parent.query.filter_by(id_number=parent_id_number).first()
        if not parent:
            flash('Parent ID number not found. Please check with your parent.', 'error')
            return redirect(url_for('register_learner'))
        
        if Learner.query.filter_by(id_number=id_number).first():
            flash('Learner ID already registered', 'error')
            return redirect(url_for('register_learner'))
        
        email = f"{id_number}@learner.edubridge.com"
        
        user = User(email=email, name=name, role='learner')
        user.set_password(password)
        db.session.add(user)
        db.session.flush()
        
        learner = Learner(
            user_id=user.id, 
            id_number=id_number, 
            age=age,
            grade=grade, 
            parent_id=parent.id
        )
        db.session.add(learner)
        db.session.commit()
        
        flash(f'Registration successful! You are {age} years old and placed in Grade {grade}.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register_learner.html')

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
    games = Game.query.all()
    return render_template('games_list.html', games=games)

@app.route('/games/<int:game_id>')
@login_required
def view_game_details(game_id):
    game = Game.query.get_or_404(game_id)
    questions = json.loads(game.questions)
    return render_template('game_details.html', game=game, questions=questions)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

# ==================== RUN THE APP ====================

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)