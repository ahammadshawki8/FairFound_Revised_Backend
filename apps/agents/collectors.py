"""External data collectors - GitHub, Portfolio, Public Web"""
import requests
from bs4 import BeautifulSoup
from typing import Dict, Optional
from django.conf import settings
import re


def fetch_github_metrics(username: str) -> Dict:
    """Fetch public GitHub metrics via API"""
    if not username:
        return {'error': 'No username provided'}
    
    headers = {'Accept': 'application/vnd.github.v3+json'}
    token = getattr(settings, 'GITHUB_TOKEN', None)
    # Only add token if it's a real token (not placeholder)
    if token and token not in ['', 'your-github-token', 'your_github_token']:
        headers['Authorization'] = f'token {token}'
    
    try:
        # Fetch user profile
        user_resp = requests.get(f'https://api.github.com/users/{username}', headers=headers, timeout=10)
        if user_resp.status_code == 401:
            # Token invalid, retry without auth
            headers.pop('Authorization', None)
            user_resp = requests.get(f'https://api.github.com/users/{username}', headers=headers, timeout=10)
        if user_resp.status_code == 404:
            return {'error': f'GitHub user "{username}" not found'}
        if user_resp.status_code == 403:
            return {'error': 'GitHub API rate limit exceeded. Try again later.'}
        if user_resp.status_code != 200:
            return {'error': f'GitHub API error: {user_resp.status_code}'}
        
        user = user_resp.json()
        
        # Fetch repositories
        repos = []
        page = 1
        while page <= 3:  # Limit to 300 repos
            repos_resp = requests.get(
                f'https://api.github.com/users/{username}/repos',
                params={'per_page': 100, 'page': page, 'sort': 'updated'},
                headers=headers, timeout=10
            )
            if repos_resp.status_code != 200:
                break
            page_repos = repos_resp.json()
            if not page_repos:
                break
            repos.extend(page_repos)
            page += 1
        
        # Calculate metrics
        total_stars = sum(r.get('stargazers_count', 0) for r in repos)
        total_forks = sum(r.get('forks_count', 0) for r in repos)
        
        # Language distribution
        languages = {}
        for repo in repos:
            lang = repo.get('language') or 'Other'
            languages[lang] = languages.get(lang, 0) + 1
        
        top_languages = sorted(languages.items(), key=lambda x: -x[1])[:5]
        
        # Recent activity (repos updated in last 90 days)
        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=90)
        recent_repos = [r for r in repos if r.get('updated_at') and 
                       datetime.fromisoformat(r['updated_at'].replace('Z', '+00:00')).replace(tzinfo=None) > cutoff]
        
        return {
            'username': username,
            'public_repos': user.get('public_repos', 0),
            'followers': user.get('followers', 0),
            'following': user.get('following', 0),
            'total_stars': total_stars,
            'total_forks': total_forks,
            'top_languages': top_languages,
            'recent_active_repos': len(recent_repos),
            'bio': user.get('bio', ''),
            'company': user.get('company', ''),
            'blog': user.get('blog', ''),
            'hireable': user.get('hireable', False),
            'created_at': user.get('created_at', ''),
            'confidence': 0.9
        }
    except Exception as e:
        return {'error': str(e), 'confidence': 0}


def fetch_portfolio_meta(url: str) -> Dict:
    """Scrape public portfolio website metadata"""
    if not url:
        return {'error': 'No URL provided'}
    
    try:
        headers = {'User-Agent': 'FairFound-Agent/1.0 (Career Analysis Bot)'}
        resp = requests.get(url, headers=headers, timeout=15)
        
        if resp.status_code != 200:
            return {'error': f'Failed to fetch: {resp.status_code}'}
        
        soup = BeautifulSoup(resp.text, 'html.parser')
        
        # Extract metadata
        title = soup.title.string if soup.title else ''
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', '') if meta_desc else ''
        
        # Count elements that indicate portfolio quality
        images = len(soup.find_all('img'))
        links = len(soup.find_all('a'))
        
        # Look for project/case study sections
        project_indicators = ['project', 'case-study', 'work', 'portfolio-item', 'card']
        project_count = 0
        for indicator in project_indicators:
            project_count += len(soup.find_all(class_=re.compile(indicator, re.I)))
        
        # Check for contact info
        has_contact = bool(soup.find(class_=re.compile('contact', re.I)) or 
                          soup.find('a', href=re.compile('mailto:')))
        
        # Check for social links
        social_links = []
        for link in soup.find_all('a', href=True):
            href = link['href'].lower()
            if 'github.com' in href:
                social_links.append('github')
            elif 'linkedin.com' in href:
                social_links.append('linkedin')
            elif 'twitter.com' in href or 'x.com' in href:
                social_links.append('twitter')
        
        # Calculate quality score
        quality_score = 0.3  # Base
        if title:
            quality_score += 0.1
        if description:
            quality_score += 0.1
        if project_count >= 3:
            quality_score += 0.2
        elif project_count >= 1:
            quality_score += 0.1
        if images >= 5:
            quality_score += 0.1
        if has_contact:
            quality_score += 0.1
        if len(social_links) >= 2:
            quality_score += 0.1
        
        return {
            'url': url,
            'title': title,
            'description': description[:500],
            'image_count': images,
            'link_count': links,
            'estimated_projects': project_count,
            'has_contact': has_contact,
            'social_links': list(set(social_links)),
            'quality_score': min(quality_score, 1.0),
            'confidence': 0.7
        }
    except Exception as e:
        return {'error': str(e), 'confidence': 0}


def fetch_public_blog_presence(urls: list) -> Dict:
    """Check presence on Medium, Dev.to, etc."""
    results = {'platforms': [], 'total_articles': 0}
    
    platform_checks = [
        ('medium.com', 'Medium'),
        ('dev.to', 'Dev.to'),
        ('hashnode.com', 'Hashnode'),
    ]
    
    for url in urls[:5]:  # Limit checks
        for domain, name in platform_checks:
            if domain in url.lower():
                results['platforms'].append(name)
                # Could fetch article count here
                break
    
    results['confidence'] = 0.6 if results['platforms'] else 0.3
    return results
