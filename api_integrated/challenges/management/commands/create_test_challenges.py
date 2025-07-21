from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from challenges.models import Challenge, ChallengeParticipant

class Command(BaseCommand):
    help = '테스트용 챌린지 데이터를 생성합니다.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            default='testuser',
            help='테스트 사용자명'
        )

    def handle(self, *args, **options):
        username = options['username']
        
        # 테스트 사용자 생성 또는 가져오기
        user, created = User.objects.get_or_create(
            username=username,
            defaults={
                'email': f'{username}@example.com',
                'first_name': 'Test',
                'last_name': 'User'
            }
        )
        
        if created:
            self.stdout.write(
                f'테스트 사용자 "{username}" 생성됨'
            )
        
        # 테스트 챌린지들 생성
        challenges_data = [
            {
                'name': '쉬운 다이어트 챌린지',
                'description': '하루 2500kcal 이하로 섭취하는 쉬운 챌린지입니다. (실패 가능: 10회)',
                'target_type': 'calorie',
                'target_value': 2500,
                'max_failures': 10,
                'is_active': True,
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30),
            },
            {
                'name': '보통 다이어트 챌린지',
                'description': '하루 2000kcal 이하로 섭취하는 보통 챌린지입니다. (실패 가능: 5회)',
                'target_type': 'calorie',
                'target_value': 2000,
                'max_failures': 5,
                'is_active': True,
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30),
            },
            {
                'name': '어려운 다이어트 챌린지',
                'description': '하루 1500kcal 이하로 섭취하는 어려운 챌린지입니다. (실패 가능: 3회)',
                'target_type': 'calorie',
                'target_value': 1500,
                'max_failures': 3,
                'is_active': True,
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30),
            },
            {
                'name': '극한 다이어트 챌린지',
                'description': '하루 1200kcal 이하로 섭취하는 극한 챌린지입니다. (실패 가능: 2회)',
                'target_type': 'calorie',
                'target_value': 1200,
                'max_failures': 2,
                'is_active': True,
                'start_date': timezone.now(),
                'end_date': timezone.now() + timedelta(days=30),
            }
        ]
        
        created_challenges = []
        for challenge_data in challenges_data:
            challenge, created = Challenge.objects.get_or_create(
                name=challenge_data['name'],
                defaults=challenge_data
            )
            
            if created:
                created_challenges.append(challenge)
                self.stdout.write(
                    f'챌린지 "{challenge.name}" 생성됨 (실패 가능: {challenge.max_failures}회)'
                )
            
            # 사용자를 챌린지에 참여시킴
            participant, created = ChallengeParticipant.objects.get_or_create(
                challenge=challenge,
                user=user,
                defaults={
                    'status': 'survived',
                    'current_streak': 0,
                    'max_streak': 0,
                    'failure_count': 0
                }
            )
            
            if created:
                self.stdout.write(
                    f'사용자 "{username}"이 챌린지 "{challenge.name}"에 참여함'
                )
        
        self.stdout.write(
            f'총 {len(created_challenges)}개의 테스트 챌린지가 생성되었습니다.'
        )
        
        # 생성된 챌린지 목록 출력
        self.stdout.write('\n생성된 챌린지 목록:')
        for challenge in Challenge.objects.filter(is_active=True):
            self.stdout.write(f'- {challenge.name} (목표: {challenge.target_value}{challenge.get_target_type_display()}, 실패 가능: {challenge.max_failures}회)') 