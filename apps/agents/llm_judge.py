"""
LLM Judge for Junior Frontend Developer evaluation
Uses Google Gemini for AI-powered assessment with iterative confidence threshold loop.

The system implements an LLM-as-a-Judge pattern with:
1. Initial evaluation generation
2. Confidence scoring (0-1 scale)
3. Iterative refinement if confidence < 0.8 threshold
4. Self-reflection and consistency checks
"""
import json
from typing import Dict, Tuple, Optional
from django.conf import settings

# Confidence threshold for accepting evaluation
CONFIDENCE_THRESHOLD = 0.8
MAX_ITERATIONS = 3

# Try to import Gemini
try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


def get_gemini_client():
    """Initialize Gemini client if API key is available"""
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if api_key and api_key not in ['', 'your-gemini-api-key'] and GEMINI_AVAILABLE:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    return None


EVALUATION_PROMPT = """
You are evaluating a junior frontend developer (0-2 years experience).

Profile Data:
- Skills: {skills}
- Experience: {experience_years} years
- GitHub: {github_info}
- Portfolio: {portfolio_info}

Scores:
- Overall: {overall_score}% ({tier} tier)
- Skills: {skill_score}% ({skill_level})
- GitHub: {github_score}% ({github_level})
- Portfolio: {portfolio_score}% ({portfolio_level})
- Experience: {exp_score}% ({exp_level})

Benchmark Position: {percentile}th percentile among junior frontend developers

Provide a JSON response with:
{{
  "summary": "2-3 sentence assessment",
  "strengths": ["strength1", "strength2", "strength3"],
  "areas_for_improvement": ["area1", "area2"],
  "recommendations": ["specific action 1", "specific action 2", "specific action 3"],
  "market_position": {{
    "rate_position": "entry level/market rate/above average/premium",
    "suggested_hourly_rate": number,
    "market_outlook": "brief market insight"
  }},
  "self_assessment": {{
    "confidence": 0.0-1.0,
    "reasoning": "brief explanation of confidence level",
    "data_quality": "high/medium/low",
    "potential_biases": ["any identified biases"]
  }}
}}

IMPORTANT: Include a self_assessment with your confidence score (0.0-1.0) based on:
- Data completeness (are all fields provided?)
- Score consistency (do scores align with profile data?)
- Recommendation specificity (are recommendations actionable?)

Keep the tone supportive and constructive. Focus on actionable advice.
Return ONLY valid JSON, no markdown or extra text.
"""

REFINEMENT_PROMPT = """
You previously evaluated a junior frontend developer but your confidence was {prev_confidence:.2f}.
The confidence threshold is {threshold}.

Previous evaluation:
{previous_evaluation}

Issues identified:
{issues}

Profile Data (unchanged):
- Skills: {skills}
- Experience: {experience_years} years
- GitHub: {github_info}
- Portfolio: {portfolio_info}
- Overall Score: {overall_score}% ({tier} tier)
- Percentile: {percentile}th

Please provide a REFINED evaluation addressing the identified issues.
Focus on:
1. More specific, actionable recommendations
2. Better alignment between scores and feedback
3. More nuanced market position analysis

Return the same JSON structure with improved content and a higher confidence score.
Return ONLY valid JSON, no markdown or extra text.
"""

CONSISTENCY_CHECK_PROMPT = """
Review this evaluation for internal consistency:

Evaluation:
{evaluation}

Profile Scores:
- Overall: {overall_score}%
- Tier: {tier}
- Percentile: {percentile}th

Check for:
1. Do strengths align with high scores?
2. Do weaknesses align with low scores?
3. Are recommendations relevant to identified gaps?
4. Is the suggested rate appropriate for the percentile?

Return JSON:
{{
  "is_consistent": true/false,
  "consistency_score": 0.0-1.0,
  "issues": ["issue1", "issue2"],
  "suggested_fixes": ["fix1", "fix2"]
}}

Return ONLY valid JSON.
"""


def evaluate_junior_frontend(structured_data: Dict, score_result: Dict, benchmark: Dict) -> Dict:
    """
    Generate LLM evaluation for junior frontend developer using iterative confidence loop.
    
    The system:
    1. Generates initial evaluation with self-assessed confidence
    2. If confidence < 0.8 threshold, iterates with refinement prompts
    3. Performs consistency check to validate evaluation
    4. Falls back to rule-based evaluation if LLM unavailable
    
    Uses Gemini if available, falls back to rule-based evaluation.
    """
    print("\n      [LLM JUDGE] Initializing iterative evaluation...")
    print(f"      Confidence threshold: {CONFIDENCE_THRESHOLD}")
    print(f"      Max iterations: {MAX_ITERATIONS}")
    
    model = get_gemini_client()
    
    if model:
        print("      ✅ Gemini API key found - using LLM-as-Judge evaluation")
        print("      Model: gemini-2.0-flash")
        try:
            result = iterative_gemini_evaluation(model, structured_data, score_result, benchmark)
            print("      ✅ Iterative evaluation complete")
            return result
        except Exception as e:
            print(f"      ⚠️ Gemini evaluation failed: {e}")
            print("      → Falling back to rule-based evaluation")
            return generate_rule_based_evaluation(structured_data, score_result, benchmark)
    
    print("      ⚠️ No Gemini API key - using rule-based evaluation")
    print("      [RUBRIC] Applying rule-based evaluation rubrics...")
    return generate_rule_based_evaluation(structured_data, score_result, benchmark)


def iterative_gemini_evaluation(model, structured_data: Dict, score_result: Dict, benchmark: Dict) -> Dict:
    """
    Iterative LLM-as-a-Judge evaluation with confidence threshold loop.
    
    Continues refining evaluation until:
    - Confidence >= CONFIDENCE_THRESHOLD (0.8)
    - Or MAX_ITERATIONS reached
    """
    print("\n      [ITERATIVE] Starting confidence threshold loop...")
    
    # Prepare context data for prompts
    context = prepare_evaluation_context(structured_data, score_result, benchmark)
    
    # Initial evaluation
    print(f"\n      [ITERATION 1/{MAX_ITERATIONS}] Generating initial evaluation...")
    current_eval = generate_single_evaluation(model, context)
    
    if not current_eval:
        print("      ⚠️ Initial evaluation failed, using rule-based")
        return generate_rule_based_evaluation(structured_data, score_result, benchmark)
    
    confidence = extract_confidence(current_eval)
    print(f"      Initial confidence: {confidence:.2f}")
    
    iteration = 1
    
    # Iterative refinement loop
    while confidence < CONFIDENCE_THRESHOLD and iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"\n      [ITERATION {iteration}/{MAX_ITERATIONS}] Confidence {confidence:.2f} < {CONFIDENCE_THRESHOLD}, refining...")
        
        # Check consistency to identify issues
        consistency_result = check_evaluation_consistency(model, current_eval, context)
        issues = consistency_result.get('issues', ['General refinement needed'])
        
        print(f"      Consistency score: {consistency_result.get('consistency_score', 0):.2f}")
        print(f"      Issues identified: {len(issues)}")
        
        # Generate refined evaluation
        refined_eval = generate_refined_evaluation(
            model, context, current_eval, confidence, issues
        )
        
        if refined_eval:
            new_confidence = extract_confidence(refined_eval)
            print(f"      Refined confidence: {new_confidence:.2f}")
            
            # Only accept if confidence improved
            if new_confidence > confidence:
                current_eval = refined_eval
                confidence = new_confidence
            else:
                print(f"      ⚠️ Confidence did not improve, keeping previous evaluation")
                break
        else:
            print(f"      ⚠️ Refinement failed, keeping previous evaluation")
            break
    
    # Final consistency check
    print(f"\n      [FINAL] Running final consistency check...")
    final_consistency = check_evaluation_consistency(model, current_eval, context)
    
    # Add metadata
    current_eval['evaluation_metadata'] = {
        'iterations': iteration,
        'final_confidence': confidence,
        'threshold': CONFIDENCE_THRESHOLD,
        'threshold_met': confidence >= CONFIDENCE_THRESHOLD,
        'consistency_score': final_consistency.get('consistency_score', 0),
        'evaluation_type': 'iterative_llm_judge'
    }
    
    # Ensure required fields exist
    current_eval['confidence'] = confidence
    current_eval['evaluation_type'] = 'iterative_llm_judge'
    
    # Add tier assessment
    current_eval['tier_assessment'] = {
        'tier': score_result.get('tier', 'Unknown'),
        'percentile': benchmark.get('user_percentile', 50),
        'interpretation': get_tier_interpretation(score_result.get('tier', 'Unknown'))
    }
    
    print(f"\n      [COMPLETE] Final confidence: {confidence:.2f} after {iteration} iteration(s)")
    print(f"      Threshold met: {confidence >= CONFIDENCE_THRESHOLD}")
    
    return current_eval


def prepare_evaluation_context(structured_data: Dict, score_result: Dict, benchmark: Dict) -> Dict:
    """Prepare context data for evaluation prompts"""
    breakdown = score_result.get('breakdown', {})
    form_data = structured_data.get('form', {})
    github_data = structured_data.get('github', {})
    
    return {
        'skills': ', '.join(form_data.get('skills', [])) or 'Not provided',
        'experience_years': form_data.get('experience_years', 0),
        'github_info': f"Repos: {github_data.get('public_repos', 'N/A')}, Stars: {github_data.get('total_stars', 'N/A')}" if github_data else 'Not provided',
        'portfolio_info': 'Provided' if structured_data.get('portfolio') else 'Not provided',
        'overall_score': round(score_result.get('overall_score', 0) * 100),
        'tier': score_result.get('tier', 'Unknown'),
        'skill_score': round(breakdown.get('skill_strength', {}).get('raw_score', 0) * 100),
        'skill_level': breakdown.get('skill_strength', {}).get('level', 'unknown'),
        'github_score': round(breakdown.get('github_activity', {}).get('raw_score', 0) * 100),
        'github_level': breakdown.get('github_activity', {}).get('level', 'unknown'),
        'portfolio_score': round(breakdown.get('portfolio_quality', {}).get('raw_score', 0) * 100),
        'portfolio_level': breakdown.get('portfolio_quality', {}).get('level', 'unknown'),
        'exp_score': round(breakdown.get('experience_depth', {}).get('raw_score', 0) * 100),
        'exp_level': breakdown.get('experience_depth', {}).get('level', 'unknown'),
        'percentile': benchmark.get('user_percentile', 50),
        'breakdown': breakdown,
        'benchmark': benchmark,
    }


def generate_single_evaluation(model, context: Dict) -> Optional[Dict]:
    """Generate a single evaluation with self-assessed confidence"""
    prompt = EVALUATION_PROMPT.format(**context)
    
    try:
        response = model.generate_content(prompt)
        return parse_json_response(response.text)
    except Exception as e:
        print(f"      ⚠️ Evaluation generation error: {e}")
        return None


def generate_refined_evaluation(model, context: Dict, previous_eval: Dict, 
                                prev_confidence: float, issues: list) -> Optional[Dict]:
    """Generate a refined evaluation addressing identified issues"""
    prompt = REFINEMENT_PROMPT.format(
        prev_confidence=prev_confidence,
        threshold=CONFIDENCE_THRESHOLD,
        previous_evaluation=json.dumps(previous_eval, indent=2),
        issues='\n'.join(f"- {issue}" for issue in issues),
        **context
    )
    
    try:
        response = model.generate_content(prompt)
        return parse_json_response(response.text)
    except Exception as e:
        print(f"      ⚠️ Refinement error: {e}")
        return None


def check_evaluation_consistency(model, evaluation: Dict, context: Dict) -> Dict:
    """Check evaluation for internal consistency"""
    prompt = CONSISTENCY_CHECK_PROMPT.format(
        evaluation=json.dumps(evaluation, indent=2),
        overall_score=context['overall_score'],
        tier=context['tier'],
        percentile=context['percentile']
    )
    
    try:
        response = model.generate_content(prompt)
        result = parse_json_response(response.text)
        return result if result else {'is_consistent': True, 'consistency_score': 0.7, 'issues': []}
    except Exception as e:
        print(f"      ⚠️ Consistency check error: {e}")
        return {'is_consistent': True, 'consistency_score': 0.7, 'issues': []}


def extract_confidence(evaluation: Dict) -> float:
    """Extract confidence score from evaluation"""
    # Try self_assessment first
    self_assessment = evaluation.get('self_assessment', {})
    if isinstance(self_assessment, dict):
        conf = self_assessment.get('confidence', 0)
        if isinstance(conf, (int, float)) and 0 <= conf <= 1:
            return float(conf)
    
    # Fall back to top-level confidence
    conf = evaluation.get('confidence', 0.5)
    if isinstance(conf, (int, float)) and 0 <= conf <= 1:
        return float(conf)
    
    return 0.5


def parse_json_response(text: str) -> Optional[Dict]:
    """Parse JSON from LLM response, handling markdown code blocks"""
    try:
        text = text.strip()
        if text.startswith('```json'):
            text = text[7:]
        if text.startswith('```'):
            text = text[3:]
        if text.endswith('```'):
            text = text[:-3]
        return json.loads(text.strip())
    except json.JSONDecodeError:
        return None





def generate_rule_based_evaluation(structured_data: Dict, score_result: Dict, benchmark: Dict) -> Dict:
    """
    Generate evaluation using rules when LLM is not available.
    Provides consistent, helpful feedback for junior developers.
    """
    print("\n      [RULE-BASED] Applying evaluation rubrics...")
    overall = score_result.get('overall_score', 0.5)
    breakdown = score_result.get('breakdown', {})
    tier = score_result.get('tier', 'Developing')
    percentile = benchmark.get('user_percentile', 50)
    
    print(f"      Input: overall={overall:.3f}, tier={tier}, percentile={percentile}")
    
    # Extract component scores
    skill_data = breakdown.get('skill_strength', {})
    github_data = breakdown.get('github_activity', {})
    portfolio_data = breakdown.get('portfolio_quality', {})
    
    skill_score = skill_data.get('raw_score', 0.5)
    github_score = github_data.get('raw_score', 0.3)
    portfolio_score = portfolio_data.get('raw_score', 0.3)
    
    # Generate strengths
    strengths = []
    if skill_score >= 0.6:
        strengths.append("Strong technical foundation with modern frontend skills")
    if github_score >= 0.5:
        strengths.append("Active GitHub presence showing consistent coding practice")
    if portfolio_score >= 0.5:
        strengths.append("Good portfolio demonstrating practical project experience")
    if overall >= 0.6:
        strengths.append("Well-rounded profile competitive in the junior market")
    
    if not strengths:
        form_data = structured_data.get('form', {})
        skills = form_data.get('skills', [])
        if 'react' in [s.lower() for s in skills]:
            strengths.append("Learning React - the most in-demand frontend framework")
        if 'javascript' in [s.lower() for s in skills]:
            strengths.append("JavaScript knowledge - essential for frontend development")
        strengths.append("Taking initiative to assess and improve your skills")
    
    # Generate weaknesses
    weaknesses = []
    if skill_score < 0.5:
        weaknesses.append("Skill set needs expansion - focus on TypeScript and testing")
    if github_score < 0.4:
        weaknesses.append("GitHub activity is low - regular commits help build credibility")
    if portfolio_score < 0.4:
        weaknesses.append("Portfolio needs more polished projects with live demos")
    
    if not weaknesses:
        weaknesses.append("Continue building momentum - consistency is key")
    
    # Generate recommendations
    recommendations = get_tier_recommendations(tier, skill_score, github_score, portfolio_score)
    
    # Generate summary
    summary = generate_summary(tier, percentile, overall)
    
    # Market insights
    market_position = get_market_position(percentile, benchmark)
    
    print(f"      [RULE-BASED] Generated {len(strengths)} strengths, {len(weaknesses)} weaknesses")
    print(f"      [RULE-BASED] Generated {len(recommendations)} recommendations")
    print(f"      [RULE-BASED] Market position: {market_position.get('rate_position')}")
    
    return {
        'summary': summary,
        'strengths': strengths[:3],
        'areas_for_improvement': weaknesses[:3],
        'recommendations': recommendations[:4],
        'market_position': market_position,
        'tier_assessment': {
            'tier': tier,
            'percentile': percentile,
            'interpretation': get_tier_interpretation(tier)
        },
        'confidence': 0.85,
        'evaluation_type': 'rule_based'
    }


def get_tier_recommendations(tier: str, skill: float, github: float, portfolio: float) -> list:
    """Get specific recommendations based on tier and scores"""
    recommendations = []
    
    if tier == 'Early Stage':
        recommendations = [
            "Complete a structured React course (freeCodeCamp, Scrimba)",
            "Build your first 3 projects: Todo app, Weather app, Portfolio site",
            "Set up GitHub and commit code daily, even small changes",
            "Join frontend communities on Discord or Twitter for support"
        ]
    elif tier == 'Developing':
        recommendations = [
            "Learn TypeScript - it's becoming essential for frontend roles",
            "Add testing to your projects using Jest and React Testing Library",
            "Create detailed READMEs for your GitHub projects",
            "Build one complex project (e.g., e-commerce site, dashboard)"
        ]
    elif tier == 'Competent':
        recommendations = [
            "Learn Next.js for server-side rendering and better SEO",
            "Contribute to open source projects to gain visibility",
            "Write technical blog posts about what you're learning",
            "Start applying for junior frontend positions"
        ]
    elif tier == 'Strong Junior':
        recommendations = [
            "Consider learning backend basics (Node.js, APIs)",
            "Mentor other beginners to solidify your knowledge",
            "Build a complex full-stack project for your portfolio",
            "Network with senior developers for career guidance"
        ]
    
    # Add specific recommendations based on low scores
    if skill < 0.5 and "TypeScript" not in str(recommendations):
        recommendations.insert(0, "Priority: Learn TypeScript - most job postings require it")
    if github < 0.3:
        recommendations.insert(0, "Priority: Increase GitHub activity - aim for daily commits")
    if portfolio < 0.3:
        recommendations.insert(0, "Priority: Build 2-3 polished projects with live demos")
    
    return recommendations[:4]


def generate_summary(tier: str, percentile: int, overall: float) -> str:
    """Generate a personalized summary"""
    if tier == 'Strong Junior':
        return f"Excellent progress! You're in the top {100-percentile}% of junior frontend developers. Your profile shows strong fundamentals and you're well-positioned for junior roles. Focus on gaining real-world experience now."
    elif tier == 'Competent':
        return f"You're doing well! At the {percentile}th percentile, you have a solid foundation. With some targeted improvements in your weaker areas, you'll be very competitive for junior positions."
    elif tier == 'Developing':
        return f"You're on the right track! At the {percentile}th percentile, you're building good habits. Focus on the recommended improvements to accelerate your growth and stand out to employers."
    else:
        return f"Welcome to your frontend journey! Everyone starts somewhere, and you're taking the right step by assessing your skills. Follow the recommendations to build a strong foundation."


def get_tier_interpretation(tier: str) -> str:
    """Get interpretation of what the tier means"""
    interpretations = {
        'Strong Junior': "Ready for junior roles, competitive candidate",
        'Competent': "Solid foundation, close to job-ready",
        'Developing': "Building skills, needs focused practice",
        'Early Stage': "Just starting, focus on fundamentals"
    }
    return interpretations.get(tier, "Building skills")


def get_market_position(percentile: int, benchmark: Dict) -> Dict:
    """Get market position insights"""
    avg_rate = benchmark.get('avg_rate', 35)
    in_demand = benchmark.get('in_demand_skills', ['react', 'typescript', 'tailwind'])
    
    if percentile >= 75:
        rate_position = "above average"
        suggested_rate = round(avg_rate * 1.2)
    elif percentile >= 50:
        rate_position = "market rate"
        suggested_rate = round(avg_rate)
    elif percentile >= 25:
        rate_position = "entry level"
        suggested_rate = round(avg_rate * 0.8)
    else:
        rate_position = "building experience"
        suggested_rate = round(avg_rate * 0.6)
    
    return {
        'rate_position': rate_position,
        'suggested_hourly_rate': suggested_rate,
        'in_demand_skills': in_demand[:5],
        'market_outlook': "Frontend development remains in high demand. React and TypeScript skills are particularly valuable."
    }
