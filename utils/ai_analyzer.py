import json
from datetime import datetime

class AIAnalyzer:
    """Analyzes game results to generate cognitive and ADHD reports"""
    
    def __init__(self, learner, game_results):
        self.learner = learner
        self.results = game_results
        self.age = learner.age
        
    def analyze(self):
        """Main analysis method"""
        return {
            'cognitive_scores': self._calculate_cognitive_scores(),
            'adhd_indicators': self._calculate_adhd_indicators(),
            'strengths': self._identify_strengths(),
            'concerns': self._identify_concerns(),
            'recommendations': self._generate_recommendations(),
            'summary': self._generate_summary(),
            'benchmarks': self._get_age_benchmarks()
        }
    
    def _calculate_cognitive_scores(self):
        """Calculate scores for each cognitive domain"""
        scores = {
            'attention': 0,
            'impulse_control': 0,
            'working_memory': 0,
            'processing_speed': 0,
            'problem_solving': 0,
            'language': 0
        }
        
        count = {'attention': 0, 'impulse_control': 0, 'working_memory': 0, 
                 'processing_speed': 0, 'problem_solving': 0, 'language': 0}
        
        for result in self.results:
            game_name = result.get('game_name', '').lower()
            score = result.get('percentage', 0)
            
            # Map games to cognitive domains
            if 'penguin' in game_name or 'simon' in game_name:
                scores['impulse_control'] += score
                count['impulse_control'] += 1
            elif 'memory' in game_name or 'recall' in game_name:
                scores['working_memory'] += score
                count['working_memory'] += 1
            elif 'attention' in game_name or 'vigilance' in game_name:
                scores['attention'] += score
                count['attention'] += 1
            elif 'math' in game_name or 'number' in game_name:
                scores['processing_speed'] += score
                count['processing_speed'] += 1
            elif 'puzzle' in game_name or 'tower' in game_name or 'maze' in game_name:
                scores['problem_solving'] += score
                count['problem_solving'] += 1
            elif 'word' in game_name or 'rhyme' in game_name or 'builder' in game_name:
                scores['language'] += score
                count['language'] += 1
        
        # Calculate averages
        for key in scores:
            if count[key] > 0:
                scores[key] = round(scores[key] / count[key], 1)
            else:
                scores[key] = None
                
        return scores
    
    def _calculate_adhd_indicators(self):
        """Calculate ADHD risk scores based on performance patterns"""
        indicators = {
            'attention_deficit': 0,
            'hyperactivity': 0,
            'impulsivity': 0
        }
        
        weight_count = {'attention_deficit': 0, 'hyperactivity': 0, 'impulsivity': 0}
        
        for result in self.results:
            score = result.get('percentage', 0)
            reaction_time = result.get('reaction_time', 500)  # milliseconds
            errors = result.get('errors', 0)
            game_name = result.get('game_name', '').lower()
            
            # Attention deficit indicators (low scores on sustained attention games)
            if 'attention' in game_name or 'vigilance' in game_name:
                if score < 60:
                    indicators['attention_deficit'] += (60 - score)
                weight_count['attention_deficit'] += 1
            
            # Hyperactivity indicators (high error rates on "no" responses)
            if 'penguin' in game_name or 'go/no-go' in game_name:
                if errors > 3:
                    indicators['hyperactivity'] += errors * 5
                weight_count['hyperactivity'] += 1
            
            # Impulsivity indicators (fast reaction times with errors)
            if reaction_time < 300 and errors > 0:
                indicators['impulsivity'] += (300 - reaction_time) / 10
                weight_count['impulsivity'] += 1
        
        # Normalize to 0-100 scale
        for key in indicators:
            if weight_count[key] > 0:
                indicators[key] = min(100, round(indicators[key] / weight_count[key], 1))
            else:
                indicators[key] = 0
        
        # Overall ADHD risk (weighted average)
        overall = (
            indicators['attention_deficit'] * 0.4 +
            indicators['hyperactivity'] * 0.3 +
            indicators['impulsivity'] * 0.3
        )
        
        return {
            'overall_risk': round(overall, 1),
            'attention_deficit_risk': indicators['attention_deficit'],
            'hyperactivity_risk': indicators['hyperactivity'],
            'impulsivity_risk': indicators['impulsivity']
        }
    
    def _identify_strengths(self):
        """Identify cognitive strengths based on scores"""
        scores = self._calculate_cognitive_scores()
        strengths = []
        
        for domain, score in scores.items():
            if score and score >= 70:
                strengths.append({
                    'domain': domain.replace('_', ' ').title(),
                    'score': score,
                    'message': self._get_strength_message(domain)
                })
        
        if not strengths:
            strengths.append({
                'domain': 'Getting Started',
                'score': 0,
                'message': 'Complete more games to identify strengths.'
            })
        
        return strengths
    
    def _identify_concerns(self):
        """Identify areas needing support"""
        scores = self._calculate_cognitive_scores()
        adhd = self._calculate_adhd_indicators()
        concerns = []
        
        for domain, score in scores.items():
            if score and score < 50:
                concerns.append({
                    'domain': domain.replace('_', ' ').title(),
                    'score': score,
                    'severity': 'High' if score < 30 else 'Moderate',
                    'message': self._get_concern_message(domain)
                })
        
        if adhd['overall_risk'] > 60:
            concerns.append({
                'domain': 'ADHD Indicators',
                'score': adhd['overall_risk'],
                'severity': 'High',
                'message': 'Multiple indicators suggest further evaluation may be beneficial.'
            })
        
        return concerns
    
    def _generate_recommendations(self):
        """Generate personalized recommendations"""
        scores = self._calculate_cognitive_scores()
        adhd = self._calculate_adhd_indicators()
        recommendations = []
        
        # Attention recommendations
        if scores.get('attention', 100) < 55:
            recommendations.append({
                'priority': 'High',
                'area': 'Attention',
                'recommendation': 'Practice with short, focused activities. Start with 5-minute sessions.',
                'suggested_games': ['Space Signal Keeper', 'Lookout Keeper'],
                'expected_improvement': 'Increased sustained attention'
            })
        
        # Impulse control recommendations
        if scores.get('impulse_control', 100) < 55 or adhd['impulsivity_risk'] > 50:
            recommendations.append({
                'priority': 'High',
                'area': 'Impulse Control',
                'recommendation': 'Practice "stop and think" strategies before responding.',
                'suggested_games': ['Penguin Says', 'Red Light, Green Light'],
                'expected_improvement': 'Better response inhibition'
            })
        
        # Memory recommendations
        if scores.get('working_memory', 100) < 55:
            recommendations.append({
                'priority': 'Medium',
                'area': 'Working Memory',
                'recommendation': 'Use visual aids and repetition. Break tasks into smaller steps.',
                'suggested_games': ['Memory Match', 'Grocery Run'],
                'expected_improvement': 'Improved recall and retention'
            })
        
        # Processing speed recommendations
        if scores.get('processing_speed', 100) < 55:
            recommendations.append({
                'priority': 'Medium',
                'area': 'Processing Speed',
                'recommendation': 'Allow extra time for tasks. Use timers for practice.',
                'suggested_games': ['Number Slice', 'Fruit Shop Math'],
                'expected_improvement': 'Faster processing with practice'
            })
        
        # Problem-solving recommendations
        if scores.get('problem_solving', 100) < 55:
            recommendations.append({
                'priority': 'Low',
                'area': 'Problem Solving',
                'recommendation': 'Encourage step-by-step thinking and verbalizing solutions.',
                'suggested_games': ['Tower of Hanoi', 'Find the Cheese'],
                'expected_improvement': 'Better strategic planning'
            })
        
        if not recommendations:
            recommendations.append({
                'priority': 'Low',
                'area': 'Maintenance',
                'recommendation': 'Continue regular practice to maintain current skill levels.',
                'suggested_games': ['All games'],
                'expected_improvement': 'Continued progress'
            })
        
        return recommendations
    
    def _generate_summary(self):
        """Generate a readable summary report"""
        scores = self._calculate_cognitive_scores()
        adhd = self._calculate_adhd_indicators()
        
        # Determine overall level
        avg_score = sum([s for s in scores.values() if s]) / len([s for s in scores.values() if s]) if scores else 0
        
        if avg_score >= 75:
            level = "Strong"
            message = "performing well above expectations"
        elif avg_score >= 55:
            level = "Developing"
            message = "meeting expected milestones"
        else:
            level = "Support Needed"
            message = "would benefit from additional support"
        
        summary = f"""
        Based on {len(self.results)} completed games, this learner is {message} for their age ({self.age} years).
        
        Cognitive Profile:
        - Attention: {scores.get('attention', 'Not enough data')}%
        - Impulse Control: {scores.get('impulse_control', 'Not enough data')}%
        - Working Memory: {scores.get('working_memory', 'Not enough data')}%
        - Processing Speed: {scores.get('processing_speed', 'Not enough data')}%
        - Problem Solving: {scores.get('problem_solving', 'Not enough data')}%
        - Language: {scores.get('language', 'Not enough data')}%
        
        ADHD Indicators: {adhd['overall_risk']}% risk level
        - Attention Deficit Indicators: {adhd['attention_deficit_risk']}%
        - Hyperactivity Indicators: {adhd['hyperactivity_risk']}%
        - Impulsivity Indicators: {adhd['impulsivity_risk']}%
        
        Note: This is an AI-generated screening based on game performance.
        For clinical diagnosis, please consult a qualified healthcare professional.
        """
        
        return summary.strip()
    
    def _get_age_benchmarks(self):
        """Get age-appropriate benchmarks"""
        benchmarks = {
            6: {'attention': 55, 'memory': 50, 'processing': 45},
            7: {'attention': 60, 'memory': 55, 'processing': 50},
            8: {'attention': 65, 'memory': 60, 'processing': 55},
            9: {'attention': 70, 'memory': 65, 'processing': 60},
            10: {'attention': 75, 'memory': 70, 'processing': 65}
        }
        return benchmarks.get(self.age, benchmarks.get(8, {'attention': 60, 'memory': 55, 'processing': 50}))
    
    def _get_strength_message(self, domain):
        messages = {
            'attention': 'Strong ability to focus and sustain attention.',
            'impulse_control': 'Excellent self-control and response inhibition.',
            'working_memory': 'Good at holding and manipulating information.',
            'processing_speed': 'Quick and efficient information processing.',
            'problem_solving': 'Strong analytical and strategic thinking skills.',
            'language': 'Excellent verbal and language processing abilities.'
        }
        return messages.get(domain, 'Notable strength in this area.')
    
    def _get_concern_message(self, domain):
        messages = {
            'attention': 'May benefit from strategies to improve focus and reduce distractions.',
            'impulse_control': 'May benefit from practicing pause-and-think strategies.',
            'working_memory': 'May benefit from using visual aids and repetition.',
            'processing_speed': 'May benefit from extra time and breaking tasks into steps.',
            'problem_solving': 'May benefit from guided practice and verbalizing solutions.',
            'language': 'May benefit from additional language-rich activities.'
        }
        return messages.get(domain, 'May benefit from targeted support in this area.')