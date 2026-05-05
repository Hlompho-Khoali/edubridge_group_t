"""
AI Learning Analyzer for EduBridge
Analyzes test results, explains performance, and provides recommendations
"""

import json
from datetime import datetime

class AILearningAnalyzer:
    """AI-powered learning analyzer"""
    
    def __init__(self):
        self.skill_descriptions = {
            'Mathematics': {
                'name': 'Math & Processing Speed',
                'description': 'How quickly and accurately you solve math problems',
                'tips': [
                    'Practice mental math daily',
                    'Use flashcards for quick recall',
                    'Play number games'
                ]
            },
            'Pattern Recognition': {
                'name': 'Pattern Recognition',
                'description': 'Ability to identify patterns and sequences',
                'tips': [
                    'Play pattern matching games',
                    'Practice completing sequences',
                    'Look for patterns in everyday life'
                ]
            },
            'Memory': {
                'name': 'Working Memory',
                'description': 'Ability to hold and use information temporarily',
                'tips': [
                    'Play memory matching games',
                    'Practice recalling sequences',
                    'Use visualization techniques'
                ]
            },
            'Attention': {
                'name': 'Attention & Focus',
                'description': 'Ability to concentrate and ignore distractions',
                'tips': [
                    'Use a timer for focused work',
                    'Take short breaks between tasks',
                    'Create a quiet study space'
                ]
            },
            'Response Inhibition': {
                'name': 'Impulse Control',
                'description': 'Ability to think before acting',
                'tips': [
                    'Practice "stop and think" exercises',
                    'Count to 3 before answering',
                    'Play go/no-go games'
                ]
            },
            'Sustained Attention': {
                'name': 'Sustained Attention',
                'description': 'Ability to maintain focus over time',
                'tips': [
                    'Gradually increase study time',
                    'Use the Pomodoro technique',
                    'Remove distractions'
                ]
            },
            'General': {
                'name': 'General Learning',
                'description': 'Overall learning abilities',
                'tips': [
                    'Practice regularly',
                    'Get enough sleep',
                    'Stay positive'
                ]
            }
        }
    
    def analyze_results(self, test_results, learner_age, learner_grade):
        """Main analysis function"""
        if not test_results:
            return self._get_no_data_analysis()
        
        # Calculate overall performance
        scores = [r['percentage'] for r in test_results]
        avg_score = sum(scores) / len(scores)
        
        # Analyze by category
        category_analysis = self._analyze_categories(test_results)
        
        # Identify strengths and weaknesses
        strengths = self._identify_strengths(category_analysis)
        weaknesses = self._identify_weaknesses(category_analysis)
        
        # Generate overall assessment
        overall_assessment = self._generate_overall_assessment(avg_score, len(test_results))
        
        # Generate recommendations
        recommendations = self._generate_recommendations(weaknesses, strengths, learner_age, learner_grade)
        
        # Generate motivational message
        motivation = self._get_motivational_message(avg_score, len(test_results))
        
        return {
            'summary': {
                'total_tests': len(test_results),
                'average_score': round(avg_score, 1),
                'best_score': max(scores),
                'lowest_score': min(scores),
                'improving': self._is_improving(scores)
            },
            'category_analysis': category_analysis,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'overall_assessment': overall_assessment,
            'recommendations': recommendations,
            'motivation': motivation,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M')
        }
    
    def _analyze_categories(self, test_results):
        """Analyze performance by category"""
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
        
        analysis = {}
        for category, scores in category_scores.items():
            avg = sum(scores) / len(scores)
            skill_info = self.skill_descriptions.get(category, self.skill_descriptions['General'])
            
            if avg >= 70:
                level = 'Strong'
                explanation = f"You're doing very well in {skill_info['name']}! {skill_info['description']}."
            elif avg >= 50:
                level = 'Developing'
                explanation = f"You're making good progress in {skill_info['name']}. {skill_info['description']} With more practice, you'll get even better."
            else:
                level = 'Needs Attention'
                explanation = f"{skill_info['name']} is an area to focus on. {skill_info['description']} Don't worry - with practice, you can improve!"
            
            analysis[category] = {
                'name': skill_info['name'],
                'average': round(avg, 1),
                'level': level,
                'explanation': explanation,
                'tips': skill_info['tips'],
                'tests_taken': category_counts[category]
            }
        
        return analysis
    
    def _identify_strengths(self, category_analysis):
        """Identify top 3 strengths"""
        strengths = []
        for category, data in category_analysis.items():
            if data['average'] >= 65:
                strengths.append({
                    'category': category,
                    'name': data['name'],
                    'score': data['average'],
                    'message': f"You excel at {data['name']}! Keep up the great work."
                })
        
        # Sort by score and take top 3
        strengths.sort(key=lambda x: x['score'], reverse=True)
        return strengths[:3] if strengths else [{'message': 'Complete more tests to identify your strengths!'}]
    
    def _identify_weaknesses(self, category_analysis):
        """Identify areas needing improvement"""
        weaknesses = []
        for category, data in category_analysis.items():
            if data['average'] < 55:
                weaknesses.append({
                    'category': category,
                    'name': data['name'],
                    'score': data['average'],
                    'message': f"Let's work on {data['name']}. The good news is that with practice, you can improve significantly!",
                    'tips': data['tips'][:2]
                })
        
        # Sort by score (lowest first)
        weaknesses.sort(key=lambda x: x['score'])
        return weaknesses[:3] if weaknesses else []
    
    def _generate_overall_assessment(self, avg_score, total_tests):
        """Generate overall performance assessment"""
        if total_tests < 3:
            return "You're just getting started! Complete a few more tests to get a detailed analysis of your learning patterns."
        
        if avg_score >= 80:
            return "Excellent work! Your performance is outstanding. You're mastering the material very well. Keep challenging yourself with new games!"
        elif avg_score >= 70:
            return "Great job! You're performing above average. Your learning strategies are working well. Keep up the consistent effort!"
        elif avg_score >= 60:
            return "Good progress! You're on the right track. With a bit more practice in specific areas, you'll see even better results."
        elif avg_score >= 50:
            return "You're making progress! Some areas need more attention, but you're building a solid foundation. Stay persistent!"
        else:
            return "Learning takes time and practice. Don't be discouraged! Let's focus on specific areas where small improvements can make a big difference."
    
    def _generate_recommendations(self, weaknesses, strengths, age, grade):
        """Generate personalized learning recommendations"""
        recommendations = []
        
        # Priority 1: Address weaknesses
        for weakness in weaknesses[:2]:  # Top 2 weaknesses
            recommendations.append({
                'priority': 'High',
                'area': weakness['name'],
                'recommendation': f"Focus on {weakness['name']}. {weakness['tips'][0]}",
                'action': f"Practice {weakness['category']} games 2-3 times per week",
                'expected_improvement': "You could see significant improvement within 2-3 weeks"
            })
        
        # Priority 2: Build on strengths
        if strengths and strengths[0].get('category'):
            recommendations.append({
                'priority': 'Medium',
                'area': strengths[0]['name'],
                'recommendation': f"Build on your strength in {strengths[0]['name']}! Try more challenging games in this category.",
                'action': "Challenge yourself with advanced level games",
                'expected_improvement': "Continue to excel and build confidence"
            })
        
        # Priority 3: General learning tips
        recommendations.append({
            'priority': 'Low',
            'area': 'Study Habits',
            'recommendation': f"At age {age}, short focused sessions work best. Try 15-20 minute practice sessions.",
            'action': "Use a timer and take short breaks",
            'expected_improvement': "Better focus and retention"
        })
        
        # Add age-appropriate tip
        if age <= 7:
            recommendations.append({
                'priority': 'Low',
                'area': 'Learning Style',
                'recommendation': "Young learners benefit from hands-on activities and visual learning.",
                'action': "Use colorful materials and physical activities while learning",
                'expected_improvement': "More engaging and enjoyable learning"
            })
        elif age <= 10:
            recommendations.append({
                'priority': 'Low',
                'area': 'Learning Style',
                'recommendation': "At this age, mixing digital learning with physical activities works well.",
                'action': "Alternate between computer games and physical movement breaks",
                'expected_improvement': "Better sustained attention"
            })
        
        return recommendations
    
    def _is_improving(self, scores):
        """Check if performance is improving over time"""
        if len(scores) < 3:
            return None
        
        # Compare first half to second half
        mid = len(scores) // 2
        first_half_avg = sum(scores[:mid]) / mid
        second_half_avg = sum(scores[mid:]) / (len(scores) - mid)
        
        return second_half_avg > first_half_avg
    
    def _get_motivational_message(self, avg_score, total_tests):
        """Get personalized motivational message"""
        if total_tests == 0:
            return "Take your first test to unlock personalized insights and recommendations!"
        
        if avg_score >= 80:
            return "🌟 Amazing work! You're showing excellent understanding. Keep challenging yourself!"
        elif avg_score >= 70:
            return "🎉 Great progress! Your hard work is paying off. Keep going!"
        elif avg_score >= 60:
            return "📈 You're on the right track! Consistent practice will help you reach your goals."
        elif avg_score >= 50:
            return "💪 You're making progress! Every test helps you learn and grow. Stay determined!"
        else:
            return "🌱 Learning is a journey. Every test teaches you something new. Don't give up - you've got this!"
    
    def _get_no_data_analysis(self):
        """Return analysis when no test data exists"""
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

# Create global instance
ai_analyzer = AILearningAnalyzer()