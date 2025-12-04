"""
CV and Document Parsing Utilities
Extracts structured information from PDF resumes using rule-based and AI methods.
"""
import re
import json
from typing import Dict, List, Optional
from django.conf import settings

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False


# Skill keywords database
SKILL_KEYWORDS = {
    'frontend': ['react', 'vue', 'angular', 'javascript', 'typescript', 'html', 'css', 'sass', 'tailwind', 'next.js', 'gatsby'],
    'backend': ['python', 'django', 'flask', 'fastapi', 'node', 'express', 'java', 'spring', 'go', 'rust', 'php', 'laravel', 'ruby', 'rails'],
    'database': ['postgresql', 'mysql', 'mongodb', 'redis', 'elasticsearch', 'sqlite', 'oracle', 'dynamodb'],
    'devops': ['docker', 'kubernetes', 'aws', 'gcp', 'azure', 'terraform', 'jenkins', 'ci/cd', 'github actions'],
    'mobile': ['react native', 'flutter', 'swift', 'kotlin', 'ios', 'android'],
    'data': ['pandas', 'numpy', 'tensorflow', 'pytorch', 'scikit-learn', 'machine learning', 'data science', 'sql'],
    'design': ['figma', 'sketch', 'adobe xd', 'photoshop', 'illustrator', 'ui/ux']
}

EMAIL_PATTERN = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
PHONE_PATTERN = r'[\+]?[(]?[0-9]{1,3}[)]?[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,4}[-\s\.]?[0-9]{1,9}'
URL_PATTERN = r'https?://[^\s<>"{}|\\^`\[\]]+'
YEAR_PATTERN = r'(19|20)\d{2}'


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract text from PDF file"""
    if not PDFPLUMBER_AVAILABLE:
        return "Error: pdfplumber not installed. Run: pip install pdfplumber"
    
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text_parts.append(page_text)
    except Exception as e:
        return f"Error extracting PDF: {str(e)}"
    return "\n\n".join(text_parts)


def extract_skills(text: str) -> Dict[str, List[str]]:
    """Extract skills from text by category"""
    text_lower = text.lower()
    found_skills = {}
    
    for category, skills in SKILL_KEYWORDS.items():
        matched = [skill for skill in skills if skill in text_lower]
        if matched:
            found_skills[category] = matched
    
    return found_skills


def extract_contact_info(text: str) -> Dict:
    """Extract emails, phones, URLs from text"""
    emails = list(set(re.findall(EMAIL_PATTERN, text)))
    phones = list(set(re.findall(PHONE_PATTERN, text)))
    urls = list(set(re.findall(URL_PATTERN, text)))
    
    # Filter URLs for portfolio/github
    github_urls = [u for u in urls if 'github.com' in u]
    linkedin_urls = [u for u in urls if 'linkedin.com' in u]
    portfolio_urls = [u for u in urls if 'github.com' not in u and 'linkedin.com' not in u]
    
    return {
        'emails': emails[:3],
        'phones': phones[:2],
        'github_urls': github_urls,
        'linkedin_urls': linkedin_urls,
        'portfolio_urls': portfolio_urls[:3]
    }


def extract_experience_years(text: str) -> Optional[int]:
    """Estimate years of experience from CV text"""
    years = re.findall(YEAR_PATTERN, text)
    if len(years) >= 2:
        years_int = [int(y) for y in years]
        return max(years_int) - min(years_int)
    
    # Look for explicit mentions
    exp_patterns = [
        r'(\d+)\+?\s*years?\s*(?:of\s*)?experience',
        r'experience[:\s]*(\d+)\s*years?',
    ]
    for pattern in exp_patterns:
        match = re.search(pattern, text.lower())
        if match:
            return int(match.group(1))
    return None


def extract_job_titles(text: str) -> List[str]:
    """Extract job titles from CV"""
    title_keywords = [
        'developer', 'engineer', 'designer', 'architect', 'manager', 'lead',
        'consultant', 'analyst', 'specialist', 'freelancer', 'contractor'
    ]
    lines = text.split('\n')
    titles = []
    
    for line in lines:
        line_lower = line.lower().strip()
        if any(kw in line_lower for kw in title_keywords) and len(line) < 100:
            titles.append(line.strip())
    
    return titles[:5]


def parse_cv_complete(pdf_path: str) -> Dict:
    """Complete CV parsing pipeline"""
    text = extract_text_from_pdf(pdf_path)
    
    if text.startswith("Error"):
        return {'error': text, 'confidence': 0}
    
    skills = extract_skills(text)
    contact = extract_contact_info(text)
    experience_years = extract_experience_years(text)
    titles = extract_job_titles(text)
    
    # Calculate confidence based on data completeness
    confidence = 0.5
    if skills:
        confidence += 0.15
    if contact.get('emails'):
        confidence += 0.1
    if experience_years:
        confidence += 0.15
    if titles:
        confidence += 0.1
    
    return {
        'raw_text': text[:5000],  # Truncate for storage
        'skills_by_category': skills,
        'all_skills': [s for cat in skills.values() for s in cat],
        'contact_info': contact,
        'experience_years': experience_years,
        'job_titles': titles,
        'confidence': min(confidence, 1.0)
    }


# ============================================
# AI-ENHANCED CV PARSING WITH GEMINI
# ============================================

CV_EXTRACTION_PROMPT = """
You are an expert CV/Resume parser. Extract structured information from the following resume text.

Resume Text:
{cv_text}

Extract and return a JSON object with the following structure:
{{
  "personal_info": {{
    "name": "Full name",
    "email": "email@example.com",
    "phone": "phone number",
    "location": "City, Country",
    "linkedin": "LinkedIn URL if found",
    "github": "GitHub URL if found",
    "portfolio": "Portfolio URL if found"
  }},
  "summary": "Professional summary or objective (1-2 sentences)",
  "skills": {{
    "frontend": ["react", "typescript", "css"],
    "backend": ["python", "node"],
    "database": ["postgresql", "mongodb"],
    "tools": ["git", "docker"],
    "other": ["agile", "communication"]
  }},
  "experience": [
    {{
      "title": "Job Title",
      "company": "Company Name",
      "duration": "Jan 2022 - Present",
      "years": 2,
      "description": "Brief description of responsibilities",
      "technologies": ["react", "typescript"]
    }}
  ],
  "education": [
    {{
      "degree": "Bachelor's in Computer Science",
      "institution": "University Name",
      "year": 2020
    }}
  ],
  "projects": [
    {{
      "name": "Project Name",
      "description": "Brief description",
      "technologies": ["react", "node"],
      "url": "project URL if available"
    }}
  ],
  "certifications": ["AWS Certified", "Google Cloud"],
  "languages": ["English", "Spanish"],
  "total_experience_years": 3,
  "current_title": "Frontend Developer",
  "seniority_level": "junior/mid/senior"
}}

Important:
- Extract ALL skills mentioned, categorize them appropriately
- Calculate total_experience_years from work history
- Determine seniority_level based on experience and skills
- If information is not found, use null or empty arrays
- Return ONLY valid JSON, no markdown or extra text
"""


def get_gemini_client():
    """Initialize Gemini client if available"""
    if not GEMINI_AVAILABLE:
        return None
    
    api_key = getattr(settings, 'GEMINI_API_KEY', None)
    if api_key and api_key not in ['', 'your-gemini-api-key']:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel('gemini-2.0-flash')
    return None


def parse_cv_with_ai(pdf_path: str) -> Dict:
    """
    Parse CV using Gemini AI for enhanced extraction.
    Falls back to rule-based parsing if AI is unavailable.
    """
    print("\n[CV PARSER] Starting AI-enhanced CV parsing...")
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    
    if text.startswith("Error"):
        return {'error': text, 'confidence': 0, 'method': 'failed'}
    
    # Try AI extraction first
    model = get_gemini_client()
    
    if model:
        print("[CV PARSER] Using Gemini AI for extraction...")
        try:
            ai_result = _extract_with_gemini(model, text)
            if ai_result and not ai_result.get('error'):
                ai_result['method'] = 'ai'
                ai_result['raw_text'] = text[:3000]
                print(f"[CV PARSER] ✅ AI extraction successful (confidence: {ai_result.get('confidence', 0):.2f})")
                return ai_result
        except Exception as e:
            print(f"[CV PARSER] ⚠️ AI extraction failed: {e}")
    
    # Fallback to rule-based parsing
    print("[CV PARSER] Using rule-based extraction...")
    result = parse_cv_complete(pdf_path)
    result['method'] = 'rule_based'
    
    return result


def _extract_with_gemini(model, cv_text: str) -> Dict:
    """Extract CV information using Gemini"""
    prompt = CV_EXTRACTION_PROMPT.format(cv_text=cv_text[:8000])  # Limit text length
    
    response = model.generate_content(prompt)
    response_text = response.text.strip()
    
    # Parse JSON response
    if response_text.startswith('```json'):
        response_text = response_text[7:]
    if response_text.startswith('```'):
        response_text = response_text[3:]
    if response_text.endswith('```'):
        response_text = response_text[:-3]
    
    data = json.loads(response_text.strip())
    
    # Flatten skills for compatibility
    all_skills = []
    skills_by_category = data.get('skills', {})
    for category_skills in skills_by_category.values():
        if isinstance(category_skills, list):
            all_skills.extend(category_skills)
    
    # Calculate confidence based on extracted data
    confidence = 0.6  # Base confidence for AI extraction
    if data.get('personal_info', {}).get('name'):
        confidence += 0.1
    if all_skills:
        confidence += 0.1
    if data.get('experience'):
        confidence += 0.1
    if data.get('total_experience_years'):
        confidence += 0.1
    
    return {
        'personal_info': data.get('personal_info', {}),
        'summary': data.get('summary', ''),
        'skills_by_category': skills_by_category,
        'all_skills': all_skills,
        'experience': data.get('experience', []),
        'education': data.get('education', []),
        'projects': data.get('projects', []),
        'certifications': data.get('certifications', []),
        'languages': data.get('languages', []),
        'experience_years': data.get('total_experience_years'),
        'current_title': data.get('current_title', ''),
        'seniority_level': data.get('seniority_level', 'junior'),
        'contact_info': {
            'emails': [data.get('personal_info', {}).get('email')] if data.get('personal_info', {}).get('email') else [],
            'phones': [data.get('personal_info', {}).get('phone')] if data.get('personal_info', {}).get('phone') else [],
            'github_urls': [data.get('personal_info', {}).get('github')] if data.get('personal_info', {}).get('github') else [],
            'linkedin_urls': [data.get('personal_info', {}).get('linkedin')] if data.get('personal_info', {}).get('linkedin') else [],
            'portfolio_urls': [data.get('personal_info', {}).get('portfolio')] if data.get('personal_info', {}).get('portfolio') else [],
        },
        'confidence': min(confidence, 1.0)
    }


def extract_skills_from_text(text: str) -> Dict:
    """
    Extract skills from any text (not just CV).
    Useful for parsing job descriptions or project descriptions.
    """
    return extract_skills(text)
