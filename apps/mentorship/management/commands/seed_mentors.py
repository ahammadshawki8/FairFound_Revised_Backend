"""
Management command to seed mentor data with senior frontend developers and reviews.
Run with: python manage.py seed_mentors
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.users.models import User, MentorProfile
from apps.mentorship.models import MentorReview
import random


class Command(BaseCommand):
    help = 'Seed database with senior frontend developer mentors and reviews'

    MENTORS_DATA = [
        {
            'username': 'sarah_chen',
            'email': 'sarah.chen@example.com',
            'title': 'Senior Frontend Engineer',
            'company': 'Google',
            'bio': 'Senior Frontend Engineer at Google with 8+ years of experience building scalable web applications. Specialized in React, TypeScript, and performance optimization. Passionate about mentoring junior developers and helping them grow their careers.',
            'specialties': ['React', 'TypeScript', 'Performance', 'System Design'],
            'rate': 150,
            'session_duration': 60,
        },
        {
            'username': 'marcus_johnson',
            'email': 'marcus.johnson@example.com',
            'title': 'Staff Frontend Developer',
            'company': 'Meta',
            'bio': 'Staff Frontend Developer at Meta with expertise in React Native and cross-platform development. 10 years in the industry, previously at Airbnb and Stripe. Love helping developers transition from junior to senior roles.',
            'specialties': ['React', 'React Native', 'GraphQL', 'Testing'],
            'rate': 175,
            'session_duration': 45,
        },
        {
            'username': 'elena_rodriguez',
            'email': 'elena.rodriguez@example.com',
            'title': 'Principal Frontend Architect',
            'company': 'Netflix',
            'bio': 'Principal Frontend Architect at Netflix. Expert in building high-performance streaming interfaces and design systems. 12 years of experience, speaker at React Conf and JSConf.',
            'specialties': ['React', 'Next.js', 'Design Systems', 'Architecture'],
            'rate': 200,
            'session_duration': 60,
        },
        {
            'username': 'david_kim',
            'email': 'david.kim@example.com',
            'title': 'Senior UI Engineer',
            'company': 'Vercel',
            'bio': 'Senior UI Engineer at Vercel working on Next.js. Previously at Shopify. Passionate about developer experience, accessibility, and modern CSS. Open source contributor.',
            'specialties': ['Next.js', 'CSS', 'Accessibility', 'DX'],
            'rate': 140,
            'session_duration': 45,
        },
        {
            'username': 'amanda_patel',
            'email': 'amanda.patel@example.com',
            'title': 'Lead Frontend Developer',
            'company': 'Stripe',
            'bio': 'Lead Frontend Developer at Stripe building payment interfaces. 7 years of experience with focus on security, UX, and clean code. Mentor at several coding bootcamps.',
            'specialties': ['React', 'Vue.js', 'Security', 'UX'],
            'rate': 160,
            'session_duration': 60,
        },
    ]

    REVIEWS_DATA = [
        # Reviews for sarah_chen
        {'mentor_idx': 0, 'reviewer_name': 'Alex Rivera', 'rating': 5, 'comment': 'Sarah is an incredible mentor! Her guidance on React architecture helped me land a senior role at a FAANG company. She breaks down complex concepts into digestible pieces and always provides actionable feedback.', 'helpful': 24},
        {'mentor_idx': 0, 'reviewer_name': 'Mike Thompson', 'rating': 5, 'comment': 'Best investment in my career. Sarah helped me improve my TypeScript skills significantly. Her code reviews are thorough and educational.', 'helpful': 18},
        {'mentor_idx': 0, 'reviewer_name': 'Jessica Wong', 'rating': 4, 'comment': 'Very knowledgeable and patient. Sessions are always productive. Would recommend for anyone looking to level up their frontend skills.', 'helpful': 12},
        {'mentor_idx': 0, 'reviewer_name': 'Ryan Cooper', 'rating': 5, 'comment': 'Sarah helped me prepare for Google interviews. Her mock interviews and feedback were invaluable. Got the offer!', 'helpful': 31},
        
        # Reviews for marcus_johnson
        {'mentor_idx': 1, 'reviewer_name': 'Taylor Swift', 'rating': 5, 'comment': 'Marcus is phenomenal! His React Native expertise helped me ship my first mobile app. Very responsive and gives detailed feedback on code reviews.', 'helpful': 22},
        {'mentor_idx': 1, 'reviewer_name': 'Jordan Lee', 'rating': 5, 'comment': 'Transitioned from junior to mid-level in just 3 months with Marcus guidance. His roadmap was spot on and he kept me accountable.', 'helpful': 28},
        {'mentor_idx': 1, 'reviewer_name': 'Chris Park', 'rating': 4, 'comment': 'Great mentor for mobile development. Helped me understand GraphQL patterns that I now use daily at work.', 'helpful': 15},
        
        # Reviews for elena_rodriguez
        {'mentor_idx': 2, 'reviewer_name': 'Sam Wilson', 'rating': 5, 'comment': 'Elena is a world-class architect. Learning design systems from her transformed how I approach frontend development. Worth every penny.', 'helpful': 35},
        {'mentor_idx': 2, 'reviewer_name': 'Lisa Brown', 'rating': 5, 'comment': 'Her architecture sessions opened my eyes to scalable frontend patterns. Now leading the design system at my company thanks to her guidance.', 'helpful': 29},
        {'mentor_idx': 2, 'reviewer_name': 'Kevin Zhang', 'rating': 5, 'comment': 'Elena helped me prepare for principal engineer interviews. Her system design knowledge is unmatched. Highly recommend for senior+ engineers.', 'helpful': 41},
        {'mentor_idx': 2, 'reviewer_name': 'Maria Garcia', 'rating': 4, 'comment': 'Excellent mentor for advanced topics. Sessions are dense with information. Best for experienced developers looking to reach staff level.', 'helpful': 19},
        
        # Reviews for david_kim
        {'mentor_idx': 3, 'reviewer_name': 'Emily Davis', 'rating': 5, 'comment': 'David taught me Next.js from scratch. His explanations of SSR vs SSG were crystal clear. My portfolio site is now blazing fast!', 'helpful': 17},
        {'mentor_idx': 3, 'reviewer_name': 'Nathan Brooks', 'rating': 5, 'comment': 'Finally understand CSS properly after sessions with David. His accessibility knowledge helped me make my apps more inclusive.', 'helpful': 21},
        {'mentor_idx': 3, 'reviewer_name': 'Sophie Turner', 'rating': 4, 'comment': 'Great for learning modern CSS and Next.js. David is patient and explains concepts well. Recommended for intermediate developers.', 'helpful': 13},
        
        # Reviews for amanda_patel
        {'mentor_idx': 4, 'reviewer_name': 'James Miller', 'rating': 5, 'comment': 'Amanda helped me understand security best practices in frontend. Her Stripe experience shows in how she approaches payment UIs.', 'helpful': 26},
        {'mentor_idx': 4, 'reviewer_name': 'Rachel Green', 'rating': 5, 'comment': 'Went from bootcamp grad to employed in 2 months with Amanda mentorship. She knows exactly what companies look for.', 'helpful': 33},
        {'mentor_idx': 4, 'reviewer_name': 'Daniel Kim', 'rating': 4, 'comment': 'Very practical advice and real-world examples. Amanda helped me improve my code quality significantly.', 'helpful': 14},
        {'mentor_idx': 4, 'reviewer_name': 'Ashley Johnson', 'rating': 5, 'comment': 'Best mentor for learning clean code practices. Amanda reviews are detailed and she always explains the why behind suggestions.', 'helpful': 20},
    ]

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write('Seeding mentors and reviews...')
        
        # Create reviewer users first
        reviewer_users = {}
        for review in self.REVIEWS_DATA:
            name = review['reviewer_name']
            if name not in reviewer_users:
                username = name.lower().replace(' ', '_')
                email = f"{username}@example.com"
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'username': username,
                        'role': 'freelancer',
                    }
                )
                if created:
                    user.set_password('password123')
                    user.save()
                reviewer_users[name] = user
        
        # Create mentors
        mentors_created = 0
        reviews_created = 0
        
        for mentor_data in self.MENTORS_DATA:
            # Create or get user
            user, user_created = User.objects.get_or_create(
                email=mentor_data['email'],
                defaults={
                    'username': mentor_data['username'],
                    'role': 'mentor',
                }
            )
            if user_created:
                user.set_password('password123')
                user.save()
            
            # Create or update mentor profile
            profile, profile_created = MentorProfile.objects.update_or_create(
                user=user,
                defaults={
                    'title': mentor_data['title'],
                    'company': mentor_data['company'],
                    'bio': mentor_data['bio'],
                    'specialties': mentor_data['specialties'],
                    'rate': mentor_data['rate'],
                    'session_duration': mentor_data['session_duration'],
                    'is_available': True,
                    'timezone': 'America/New_York',
                }
            )
            
            if profile_created:
                mentors_created += 1
                self.stdout.write(f'  Created mentor: {mentor_data["username"]}')
            else:
                self.stdout.write(f'  Updated mentor: {mentor_data["username"]}')
        
        # Create reviews
        for review_data in self.REVIEWS_DATA:
            mentor_idx = review_data['mentor_idx']
            mentor_email = self.MENTORS_DATA[mentor_idx]['email']
            mentor_user = User.objects.get(email=mentor_email)
            mentor_profile = MentorProfile.objects.get(user=mentor_user)
            reviewer = reviewer_users[review_data['reviewer_name']]
            
            review, created = MentorReview.objects.update_or_create(
                mentor=mentor_profile,
                reviewer=reviewer,
                defaults={
                    'rating': review_data['rating'],
                    'comment': review_data['comment'],
                    'helpful': review_data['helpful'],
                }
            )
            if created:
                reviews_created += 1
        
        # Update mentor ratings
        for mentor_data in self.MENTORS_DATA:
            mentor_user = User.objects.get(email=mentor_data['email'])
            mentor_profile = MentorProfile.objects.get(user=mentor_user)
            reviews = MentorReview.objects.filter(mentor=mentor_profile)
            if reviews.exists():
                avg_rating = sum(r.rating for r in reviews) / reviews.count()
                mentor_profile.rating = round(avg_rating, 2)
                mentor_profile.total_reviews = reviews.count()
                mentor_profile.save()
        
        self.stdout.write(self.style.SUCCESS(
            f'Successfully seeded {mentors_created} mentors and {reviews_created} reviews'
        ))
