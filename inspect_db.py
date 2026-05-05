#!/usr/bin/env python
"""
Local Database Inspector for EduBridge
Run this to see all data in your local database
"""

from app import app
from models import db, User, Learner, Educator, Parent, Game, TestResult, TestAssignment
from sqlalchemy import func
import json

def inspect_database():
    with app.app_context():
        print("\n" + "="*60)
        print("EDUBRIDGE LOCAL DATABASE INSPECTOR")
        print("="*60)
        
        # ============ USERS ============
        print("\nUSERS TABLE")
        print("-" * 40)
        users = User.query.all()
        print(f"Total users: {len(users)}")
        for user in users:
            print(f"  ID:{user.id} | {user.name} | {user.email} | Role:{user.role}")
        
        # ============ LEARNERS ============
        print("\nLEARNERS")
        print("-" * 40)
        learners = Learner.query.all()
        for learner in learners:
            parent = Parent.query.get(learner.parent_id)
            print(f"  Name: {learner.user.name}")
            print(f"    - Email: {learner.email if hasattr(learner, 'email') else 'N/A'}")
            print(f"    - ID Number: {learner.id_number}")
            print(f"    - Age: {learner.age}")
            print(f"    - Grade: {learner.grade}")
            print(f"    - Parent: {parent.user.name if parent else 'N/A'}")
            print()
        
        # ============ EDUCATORS ============
        print("\nEDUCATORS")
        print("-" * 40)
        educators = Educator.query.all()
        for educator in educators:
            print(f"  Name: {educator.user.name}")
            print(f"    - Email: {educator.user.email}")
            print(f"    - Phone: {educator.phone_number}")
            print(f"    - Teaching Grade: {educator.grade_teaching}")
            print()
        
        # ============ PARENTS ============
        print("\nPARENTS")
        print("-" * 40)
        parents = Parent.query.all()
        for parent in parents:
            children = Learner.query.filter_by(parent_id=parent.id).all()
            print(f"  Name: {parent.user.name}")
            print(f"    - ID Number: {parent.id_number}")
            print(f"    - Email: {parent.user.email}")
            print(f"    - Children: {', '.join([c.user.name for c in children]) if children else 'None'}")
            print()
        
        # ============ GAMES ============
        print("\nGAMES")
        print("-" * 40)
        games = Game.query.all()
        for game in games:
            questions = json.loads(game.questions)
            print(f"  ID:{game.id} | {game.name}")
            print(f"    - Category: {game.category}")
            print(f"    - Questions: {len(questions)}")
            print(f"    - Time: {game.time_limit_minutes} min")
            print()
        
        # ============ TEST ASSIGNMENTS ============
        print("\nTEST ASSIGNMENTS")
        print("-" * 40)
        assignments = TestAssignment.query.all()
        for assignment in assignments:
            learner = assignment.learner
            game = assignment.game
            print(f"  Student: {learner.user.name}")
            print(f"    - Test: {game.name}")
            print(f"    - Status: {assignment.status}")
            print(f"    - Assigned: {assignment.assigned_at.strftime('%Y-%m-%d') if assignment.assigned_at else 'N/A'}")
            print()
        
        # ============ TEST RESULTS ============
        print("\nTEST RESULTS")
        print("-" * 40)
        results = TestResult.query.all()
        if results:
            for result in results:
                assignment = result.assignment
                learner = assignment.learner
                game = assignment.game
                print(f"  Student: {learner.user.name}")
                print(f"    - Test: {game.name}")
                print(f"    - Score: {result.score}/30 ({result.percentage:.1f}%)")
                print(f"    - Result: {'PASSED' if result.passed else 'FAILED'}")
                print(f"    - Date: {result.completed_at.strftime('%Y-%m-%d %H:%M') if result.completed_at else 'N/A'}")
                print()
        else:
            print("  No test results yet")
        
        # ============ STATISTICS ============
        print("\nSTATISTICS")
        print("-" * 40)
        
        total_users = User.query.count()
        total_learners = Learner.query.count()
        total_educators = Educator.query.count()
        total_parents = Parent.query.count()
        total_games = Game.query.count()
        total_assignments = TestAssignment.query.count()
        total_completed = TestResult.query.count()
        
        print(f"  Total Users: {total_users}")
        print(f"    - Learners: {total_learners}")
        print(f"    - Educators: {total_educators}")
        print(f"    - Parents: {total_parents}")
        print(f"  Total Games: {total_games}")
        print(f"  Total Assignments: {total_assignments}")
        print(f"  Total Completed Tests: {total_completed}")
        
        if total_completed > 0:
            avg_score = db.session.query(func.avg(TestResult.percentage)).scalar()
            pass_count = TestResult.query.filter_by(passed=True).count()
            pass_rate = (pass_count / total_completed) * 100
            print(f"  Average Score: {avg_score:.1f}%")
            print(f"  Pass Rate: {pass_rate:.1f}%")
        
        print("\n" + "="*60)
        print("INSPECTION COMPLETE")
        print("="*60 + "\n")

if __name__ == "__main__":
    inspect_database()