"""
Celery tasks for Junior Frontend Developer analysis pipeline
End-to-end processing without portfolio/sentiment dependencies
"""
from typing import Dict
from celery import shared_task
from django.contrib.auth import get_user_model
from .models import IngestionJob, Evidence, ScoreSnapshot
from .parsers import parse_cv_complete
from .collectors import fetch_github_metrics
from .scoring import (
    calculate_skill_score, calculate_github_score, 
    calculate_portfolio_score, calculate_experience_score,
    compute_overall_score, generate_improvements
)
from .llm_judge import evaluate_junior_frontend
from .synthetic_data import get_junior_frontend_benchmark

User = get_user_model()


def print_separator(title: str, char: str = "="):
    """Print a formatted separator for logging"""
    print(f"\n{char * 60}")
    print(f"  {title}")
    print(f"{char * 60}")


@shared_task(bind=True, max_retries=3)
def run_junior_frontend_pipeline(self, job_id: int):
    """
    Main pipeline for analyzing junior frontend developers.
    Simplified flow: CV/Form -> GitHub -> Scoring -> Benchmark -> Results
    """
    try:
        print_separator("AGENTIC AI PIPELINE STARTED", "🚀")
        print(f"  Job ID: {job_id}")
        print(f"  Pipeline: Junior Frontend Developer Analysis")
        
        job = IngestionJob.objects.get(id=job_id)
        job.status = 'running'
        job.save()
        
        input_data = job.input_data
        structured_data = {}
        
        # ============================================
        # PHASE 1: Data Collection
        # ============================================
        print_separator("PHASE 1: DATA COLLECTION AGENTS", "-")
        
        # 1a. CV Parsing (if provided)
        cv_data = None
        if input_data.get('cv_file_path'):
            print("\n📄 [AGENT 1a] CV Parser Agent")
            print(f"   Input: {input_data.get('cv_file_path')}")
            try:
                cv_data = parse_cv_complete(input_data['cv_file_path'])
                Evidence.objects.create(
                    job=job,
                    source='cv',
                    raw_content=cv_data.get('raw_text', '')[:2000],
                    extracted_data=cv_data,
                    confidence=cv_data.get('confidence', 0.7)
                )
                structured_data['cv'] = cv_data
                print(f"   ✅ CV parsed successfully")
                print(f"   Skills found: {cv_data.get('skills_by_category', {})}")
                print(f"   Confidence: {cv_data.get('confidence', 0.7)}")
            except Exception as e:
                structured_data['cv_error'] = str(e)
                print(f"   ❌ CV parsing failed: {e}")
        else:
            print("\n📄 [AGENT 1a] CV Parser Agent - SKIPPED (no CV provided)")
        
        # 1b. Form Data (always present)
        print("\n📝 [AGENT 1b] Form Data Collector Agent")
        form_data = input_data.get('form_fields', {})
        Evidence.objects.create(
            job=job,
            source='form',
            raw_content=str(form_data),
            extracted_data=form_data,
            confidence=1.0  # User-provided data is trusted
        )
        structured_data['form'] = form_data
        print(f"   ✅ Form data collected")
        print(f"   Name: {form_data.get('name', 'N/A')}")
        print(f"   Skills: {form_data.get('skills', [])}")
        print(f"   Experience: {form_data.get('experience_years', 0)} years")
        print(f"   Confidence: 1.0 (user-provided)")
        
        # 1c. GitHub Data Collection
        github_data = None
        github_username = input_data.get('github_username')
        
        # Try to extract from CV if not provided
        if not github_username and cv_data:
            github_urls = cv_data.get('contact_info', {}).get('github_urls', [])
            if github_urls:
                github_username = github_urls[0].split('github.com/')[-1].strip('/')
        
        print("\n🐙 [AGENT 1c] GitHub Collector Agent")
        if github_username:
            print(f"   Username: {github_username}")
            github_data = fetch_github_metrics(github_username)
            Evidence.objects.create(
                job=job,
                source='github',
                raw_content=str(github_data)[:2000],
                extracted_data=github_data,
                confidence=github_data.get('confidence', 0.8) if not github_data.get('error') else 0.3
            )
            structured_data['github'] = github_data
            if not github_data.get('error'):
                print(f"   ✅ GitHub data collected")
                print(f"   Public repos: {github_data.get('public_repos', 0)}")
                print(f"   Total stars: {github_data.get('total_stars', 0)}")
                print(f"   Recent active repos: {github_data.get('recent_active_repos', 0)}")
            else:
                print(f"   ⚠️ GitHub fetch warning: {github_data.get('error')}")
        else:
            print("   SKIPPED (no GitHub username provided)")
        
        # ============================================
        # PHASE 2: Feature Extraction & Scoring
        # ============================================
        print_separator("PHASE 2: SCORING AGENTS (Rubric-Based)", "-")
        
        # Merge skills from all sources
        all_skills = set()
        
        # From CV
        if cv_data:
            cv_skills = cv_data.get('skills_by_category', {})
            for cat_skills in cv_skills.values():
                if isinstance(cat_skills, list):
                    all_skills.update([s.lower() for s in cat_skills])
        
        # From form
        form_skills = form_data.get('skills', [])
        if form_skills:
            all_skills.update([s.lower() for s in form_skills])
        
        skills_data = {'all_skills': list(all_skills)}
        print(f"\n📊 Merged skills from all sources: {list(all_skills)}")
        
        # Calculate individual scores
        print("\n🎯 [AGENT 2a] Skill Scoring Agent (Rubric-Based)")
        skill_result = calculate_skill_score(skills_data)
        print(f"   Score: {skill_result[0]:.3f} ({skill_result[0]*100:.1f}%)")
        print(f"   Level: {skill_result[1]}")
        print(f"   Matched skills: {skill_result[2].get('matched_skills', {})}")
        print(f"   Missing important: {skill_result[2].get('missing_important', [])}")
        
        print("\n🐙 [AGENT 2b] GitHub Scoring Agent (Rubric-Based)")
        github_result = calculate_github_score(github_data or {})
        print(f"   Score: {github_result[0]:.3f} ({github_result[0]*100:.1f}%)")
        print(f"   Level: {github_result[1]}")
        print(f"   Details: {github_result[2]}")
        
        # Portfolio score from form or default
        portfolio_data = {
            'has_projects': bool(form_data.get('portfolio_url')),
            'project_count': form_data.get('project_count', 0),
            'has_live_demos': form_data.get('has_live_demos', False),
            'has_code_links': bool(github_username),
            'quality_score': 0.4 if form_data.get('portfolio_url') else 0.2
        }
        print("\n🖼️ [AGENT 2c] Portfolio Scoring Agent (Rubric-Based)")
        portfolio_result = calculate_portfolio_score(portfolio_data)
        print(f"   Score: {portfolio_result[0]:.3f} ({portfolio_result[0]*100:.1f}%)")
        print(f"   Level: {portfolio_result[1]}")
        print(f"   Has live demos: {portfolio_data.get('has_live_demos')}")
        
        # Experience score
        exp_years = form_data.get('experience_years', 0)
        if cv_data and cv_data.get('experience_years'):
            exp_years = max(exp_years, cv_data.get('experience_years', 0))
        print("\n⏱️ [AGENT 2d] Experience Scoring Agent (Rubric-Based)")
        experience_result = calculate_experience_score(exp_years)
        print(f"   Experience years: {exp_years}")
        print(f"   Score: {experience_result[0]:.3f} ({experience_result[0]*100:.1f}%)")
        print(f"   Level: {experience_result[1]}")
        
        # Learning momentum (based on recent activity)
        momentum = 0.5
        if github_data and not github_data.get('error'):
            recent = github_data.get('recent_active_repos', 0)
            momentum = min(0.9, 0.3 + (recent * 0.1))
        print("\n📈 [AGENT 2e] Learning Momentum Agent")
        print(f"   Momentum score: {momentum:.3f} ({momentum*100:.1f}%)")
        
        # ============================================
        # PHASE 3: Overall Score Computation
        # ============================================
        print_separator("PHASE 3: OVERALL SCORE COMPUTATION", "-")
        
        features = {
            'skill': skill_result,
            'github': github_result,
            'portfolio': portfolio_result,
            'experience': experience_result,
            'learning_momentum': momentum
        }
        
        print("\n🧮 [AGENT 3] Score Aggregation Agent")
        print("   Weights used:")
        print("   - Skill strength: 35%")
        print("   - GitHub activity: 25%")
        print("   - Portfolio quality: 20%")
        print("   - Experience depth: 15%")
        print("   - Learning momentum: 5%")
        
        score_result = compute_overall_score(features)
        
        print(f"\n   ✅ OVERALL SCORE: {score_result['overall_score']:.3f} ({score_result['overall_score']*100:.1f}%)")
        print(f"   TIER: {score_result['tier']} ({score_result['tier_color']})")
        print("\n   Breakdown:")
        for component, data in score_result['breakdown'].items():
            print(f"   - {component}: {data['raw_score']:.3f} × {data['weight']} = {data['weighted']:.4f}")
        
        # ============================================
        # PHASE 4: Benchmark Comparison
        # ============================================
        print_separator("PHASE 4: SYNTHETIC DATA BENCHMARK", "-")
        
        print("\n📊 [AGENT 4] Benchmark Comparison Agent")
        print("   Using synthetic dataset: 200 junior frontend developer profiles")
        print("   Data source: Kaggle-inspired + Stack Overflow Survey 2024")
        
        benchmark = get_junior_frontend_benchmark(score_result['overall_score'], list(all_skills))
        
        print(f"\n   ✅ BENCHMARK RESULTS:")
        print(f"   User percentile: {benchmark.get('user_percentile')}th")
        print(f"   Benchmark tier: {benchmark.get('tier')}")
        print(f"   Tier description: {benchmark.get('tier_description')}")
        print(f"   Average market rate: ${benchmark.get('avg_rate')}/hr")
        print(f"   Sample size: {benchmark.get('sample_size')} profiles")
        print(f"   In-demand skills: {benchmark.get('in_demand_skills', [])[:5]}")
        print(f"   Personalized skill gaps: {benchmark.get('market_insights', {}).get('skill_gaps', [])}")
        
        # ============================================
        # PHASE 5: LLM Evaluation (if available)
        # ============================================
        print_separator("PHASE 5: LLM JUDGE (Gemini 2.0 Flash)", "-")
        
        print("\n🤖 [AGENT 5] LLM Judge Agent")
        print("   Model: Gemini 2.0 Flash")
        print("   Task: Evaluate profile and provide personalized feedback")
        
        llm_evaluation = evaluate_junior_frontend(
            structured_data, 
            score_result,
            benchmark
        )
        
        print(f"\n   ✅ LLM EVALUATION COMPLETE:")
        print(f"   Evaluation type: {llm_evaluation.get('evaluation_type', 'unknown')}")
        print(f"   Confidence: {llm_evaluation.get('confidence', 0):.2f}")
        print(f"   Summary: {llm_evaluation.get('summary', 'N/A')[:100]}...")
        print(f"   Strengths: {llm_evaluation.get('strengths', [])}")
        print(f"   Areas for improvement: {llm_evaluation.get('areas_for_improvement', [])}")
        
        # ============================================
        # PHASE 6: Generate Improvements
        # ============================================
        print_separator("PHASE 6: IMPROVEMENT GENERATION", "-")
        
        print("\n💡 [AGENT 6] Improvement Generator Agent")
        improvements = generate_improvements(score_result['breakdown'])
        
        print(f"   ✅ Generated {len(improvements)} improvement suggestions:")
        for i, imp in enumerate(improvements, 1):
            print(f"   {i}. [{imp['area']}] {imp['action']}")
            print(f"      Impact: {imp['impact']}, Time: {imp.get('time_estimate', 'N/A')}")
        
        # ============================================
        # PHASE 7: Compile Final Results
        # ============================================
        print_separator("PHASE 7: HUMAN-IN-THE-LOOP CHECK", "-")
        
        final_result = {
            'category': 'junior_frontend',
            'structured_data': structured_data,
            'score_result': score_result,
            'benchmark': benchmark,
            'llm_evaluation': llm_evaluation,
            'improvements': improvements,
            'skills_detected': list(all_skills),
            'data_sources': list(structured_data.keys())
        }
        
        # Calculate confidence
        evidences = job.evidence.all()
        confidences = [e.confidence for e in evidences]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.5
        
        print("\n👤 [AGENT 7] Human-in-the-Loop Review Agent")
        print(f"   Average confidence: {avg_confidence:.2f}")
        print(f"   Overall score: {score_result['overall_score']:.3f}")
        print(f"   Skills detected: {len(all_skills)}")
        
        # Flag for review if needed
        flagged = (
            avg_confidence < 0.5 or 
            score_result['overall_score'] < 0.2 or 
            score_result['overall_score'] > 0.85 or
            len(all_skills) < 2
        )
        
        print(f"\n   Review criteria check:")
        print(f"   - Low confidence (<0.5): {avg_confidence < 0.5}")
        print(f"   - Very low score (<0.2): {score_result['overall_score'] < 0.2}")
        print(f"   - Very high score (>0.85): {score_result['overall_score'] > 0.85}")
        print(f"   - Few skills (<2): {len(all_skills) < 2}")
        print(f"\n   ✅ FLAGGED FOR HUMAN REVIEW: {flagged}")
        
        # Save score snapshot
        ScoreSnapshot.objects.create(
            job=job,
            overall_score=score_result['overall_score'],
            breakdown=score_result['breakdown'],
            llm_rationale=llm_evaluation.get('summary', ''),
            improvements=[imp['action'] for imp in improvements],
            confidence=avg_confidence,
            flagged_for_human=flagged
        )
        
        # Update job
        job.result = final_result
        job.status = 'review' if flagged else 'done'
        job.save()
        
        # Final summary
        print_separator("PIPELINE COMPLETE", "🎉")
        print(f"\n   Job ID: {job_id}")
        print(f"   Status: {job.status}")
        print(f"   Overall Score: {score_result['overall_score']:.3f} ({score_result['overall_score']*100:.1f}%)")
        print(f"   Tier: {score_result['tier']}")
        print(f"   Percentile: {benchmark.get('user_percentile', 0)}th")
        print(f"   Flagged for review: {flagged}")
        print(f"\n   Data sources used: {list(structured_data.keys())}")
        print(f"   Skills detected: {len(all_skills)}")
        print(f"   Improvements generated: {len(improvements)}")
        print("\n" + "=" * 60 + "\n")
        
        return {
            'status': 'success',
            'job_id': job_id,
            'overall_score': score_result['overall_score'],
            'tier': score_result['tier'],
            'percentile': benchmark.get('user_percentile', 0),
            'flagged': flagged
        }
        
    except Exception as e:
        if job:
            job.status = 'error'
            job.error_message = str(e)
            job.save()
        raise self.retry(exc=e, countdown=60)


@shared_task
def seed_benchmarks_task():
    """Task to seed benchmark data"""
    from .synthetic_data import seed_junior_frontend_benchmarks
    count = seed_junior_frontend_benchmarks()
    return f'Seeded {count} junior frontend profiles'


@shared_task
def cleanup_old_jobs():
    """Clean up old completed jobs"""
    from datetime import datetime, timedelta
    from django.utils import timezone
    
    cutoff = timezone.now() - timedelta(days=30)
    old_jobs = IngestionJob.objects.filter(
        created_at__lt=cutoff,
        status__in=['done', 'error']
    )
    count = old_jobs.count()
    old_jobs.delete()
    return f'Cleaned up {count} old jobs'


# Synchronous version for testing without Celery
def run_pipeline_sync(job_id: int) -> Dict:
    """Synchronous pipeline for testing"""
    return run_junior_frontend_pipeline(job_id)
