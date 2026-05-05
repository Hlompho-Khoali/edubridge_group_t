"""
AI-based ADHD risk prediction and learning analytics
"""
import json
import random
from datetime import datetime
from collections import defaultdict

class ADHDPredictor:
    """AI model for ADHD risk prediction based on test performance"""
    
    def __init__(self):
        # Weight factors for different cognitive skills
        self.skill_weights = {
            'processing_speed': 0.20,
            'attention': 0.25,
            'impulse_control': 0.20,
            'working_memory': 0.20,
            'sustained_attention': 0.15
        }
        
        # Thresholds for risk levels
        self.risk_thresholds = {
            'low': 30,
            'moderate': 50,
            'high': 70
        }
    
    def analyze_test_results(self, test_results):
        """Analyze test results to identify patterns"""
        if not test_results:
            return None
        
        # Categorize tests by skill type
        skill_scores = defaultdict(list)
        
        for result in test_results:
            game = result.get('game')
            if not game:
                continue
            
            # Map games to cognitive skills
            skill = self._map_game_to_skill(game.get('category', ''))
            skill_scores[skill].append(result.get('percentage', 0))
        
        # Calculate average scores per skill
        skill_averages = {}
        for skill, scores in skill_scores.items():
            if scores:
                skill_averages[skill] = sum(scores) / len(scores)
        
        return skill_averages
    
    def predict_adhd_risk(self, test_results, learner_age):
        """Predict ADHD risk level based on test performance"""
        skill_averages = self.analyze_test_results(test_results)
        
        if not skill_averages:
            return {
                'risk_level': 'insufficient_data',
                'risk_score': 0,
                'confidence': 0,
                'recommendations': ['Complete at least 5 tests for accurate prediction']
            }
        
        # Calculate weighted risk score
        risk_score = 0
        total_weight = 0
        
        for skill, score in skill_averages.items():
            weight = self.skill_weights.get(skill, 0.10)
            total_weight += weight
            # Lower scores = higher risk
            if score < 50:
                risk_score += weight * (50 - score) / 50 * 100
            else:
                risk_score += weight * 0
        
        # Normalize
        risk_score = (risk_score / total_weight) if total_weight > 0 else 0
        
        # Determine risk level
        if risk_score < self.risk_thresholds['low']:
            risk_level = 'low'
        elif risk_score < self.risk_thresholds['moderate']:
            risk_level = 'moderate'
        else:
            risk_level = 'high'
        
        # Generate personalized recommendations
        recommendations = self._generate_recommendations(skill_averages, risk_level, learner_age)
        
        return {
            'risk_level': risk_level,
            'risk_score': round(risk_score, 1),
            'confidence': self._calculate_confidence(len(test_results)),
            'skill_averages': skill_averages,
            'recommendations': recommendations,
            'analysis_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    
    def _map_game_to_skill(self, category):
        """Map game category to cognitive skill"""
        skill_mapping = {
            'Mathematics': 'processing_speed',
            'Pattern Recognition': 'attention',
            'Memory': 'working_memory',
            'Attention': 'attention',
            'Response Inhibition': 'impulse_control',
            'Sustained Attention': 'sustained_attention',
            'General': 'attention'
        }
        return skill_mapping.get(category, 'attention')
    
    def _calculate_confidence(self, num_tests):
        """Calculate prediction confidence based on number of tests"""
        if num_tests < 3:
            return 'low'
        elif num_tests < 7:
            return 'moderate'
        else:
            return 'high'
    
    def _generate_recommendations(self, skill_averages, risk_level, age):
        """Generate personalized learning recommendations"""
        recommendations = []
        
        if risk_level == 'high':
            recommendations.append({
                'priority': 'high',
                'area': 'Professional Consultation',
                'suggestion': 'Consider consulting with an educational psychologist for comprehensive assessment'
            })
        
        # Skill-specific recommendations
        for skill, score in skill_averages.items():
            if score < 40:
                recommendations.append({
                    'priority': 'high',
                    'area': self._get_skill_name(skill),
                    'suggestion': self._get_improvement_suggestion(skill, age)
                })
            elif score < 60:
                recommendations.append({
                    'priority': 'medium',
                    'area': self._get_skill_name(skill),
                    'suggestion': self._get_practice_suggestion(skill)
                })
        
        # General recommendations based on risk level
        if risk_level == 'low':
            recommendations.append({
                'priority': 'low',
                'area': 'Maintenance',
                'suggestion': 'Continue with current learning pace. Great progress!'
            })
        elif risk_level == 'moderate':
            recommendations.append({
                'priority': 'medium',
                'area': 'Parent Support',
                'suggestion': 'Consider structured breaks during study sessions'
            })
        
        return recommendations[:5]  # Limit to top 5 recommendations
    
    def _get_skill_name(self, skill):
        """Get readable skill name"""
        names = {
            'processing_speed': 'Processing Speed',
            'attention': 'Attention & Focus',
            'impulse_control': 'Impulse Control',
            'working_memory': 'Working Memory',
            'sustained_attention': 'Sustained Attention'
        }
        return names.get(skill, skill)
    
    def _get_improvement_suggestion(self, skill, age):
        """Get improvement suggestions for specific skills"""
        suggestions = {
            'processing_speed': 'Practice quick mental math games daily for 10 minutes',
            'attention': 'Use a timer for focused work sessions (Pomodoro technique)',
            'impulse_control': 'Practice "stop and think" exercises before answering',
            'working_memory': 'Play memory matching games and sequence recall activities',
            'sustained_attention': 'Gradually increase focused work time by 2 minutes each week'
        }
        return suggestions.get(skill, 'Continue practicing relevant games')
    
    def _get_practice_suggestion(self, skill):
        """Get practice suggestions for skill improvement"""
        practices = {
            'processing_speed': 'Use math flashcards for 5 minutes daily',
            'attention': 'Try mindfulness exercises before study sessions',
            'impulse_control': 'Practice waiting 3 seconds before answering questions',
            'working_memory': 'Use visualization techniques to remember information',
            'sustained_attention': 'Remove distractions during study time'
        }
        return practices.get(skill, 'Regular practice of assigned games')

class LearningRecommender:
    """AI-powered learning recommendation system"""
    
    def __init__(self):
        self.game_categories = ['Mathematics', 'Pattern Recognition', 'Memory', 'Attention']
    
    def generate_recommendations(self, test_results, learner_grade):
        """Generate personalized game recommendations"""
        if not test_results:
            return self._get_default_recommendations(learner_grade)
        
        # Analyze weak areas
        weak_areas = []
        strong_areas = []
        
        for result in test_results:
            if result.get('percentage', 0) < 50:
                weak_areas.append(result.get('game', {}).get('category', 'General'))
            elif result.get('percentage', 0) > 75:
                strong_areas.append(result.get('game', {}).get('category', 'General'))
        
        # Count frequency
        from collections import Counter
        weak_counts = Counter(weak_areas)
        strong_counts = Counter(strong_areas)
        
        # Get top weak areas
        top_weak = [area for area, count in weak_counts.most_common(2)]
        
        recommendations = []
        
        # Suggest games for weak areas
        for area in top_weak:
            recommendations.append({
                'category': area,
                'reason': f'Need improvement in {area} skills',
                'priority': 'high',
                'suggested_frequency': '3 times per week'
            })
        
        # Add variety recommendation
        if len(recommendations) < 2:
            recommendations.append({
                'category': 'Pattern Recognition',
                'reason': 'Build cognitive flexibility',
                'priority': 'medium',
                'suggested_frequency': '2 times per week'
            })
        
        return recommendations
    
    def _get_default_recommendations(self, grade):
        """Get default recommendations for new learners"""
        return [
            {
                'category': 'Mathematics',
                'reason': 'Build foundational math skills',
                'priority': 'high',
                'suggested_frequency': '3 times per week'
            },
            {
                'category': 'Memory',
                'reason': 'Develop working memory',
                'priority': 'medium',
                'suggested_frequency': '2 times per week'
            }
        ]

# Create global instances
adhd_predictor = ADHDPredictor()
learning_recommender = LearningRecommender()