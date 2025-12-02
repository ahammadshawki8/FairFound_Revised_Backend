"""CV and document parsing utilities"""
import re
import pdfplumber
from typing import Dict, List, Optional


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
