from django.shortcuts import render, get_object_or_404
from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django.utils import timezone
from django.db.models import Q, Count
from datetime import date, timedelta
from .models import Challenge, ChallengeParticipant, Badge, ChallengeProgress
from .serializers import (
    ChallengeSerializer, ChallengeDetailSerializer,
    ChallengeParticipantSerializer, BadgeSerializer,
    ChallengeProgressSerializer
)
from .utils import (
    update_challenge_progress, batch_evaluate_challenges,
    get_mock_nutrition_data, get_challenge_summary,
    create_api_response, log_challenge_activity,
    get_optimized_challenge_summary, get_cached_challenge_data,
    set_cached_challenge_data, check_challenge_overlap
)

class TestChallengeAPIView(APIView):
    """인증 없이 접근 가능한 테스트용 API"""
    permission_classes = []  # 인증 없이 접근 가능
    
    def get(self, request):
        """테스트용 챌린지 목록 조회"""
        challenges = Challenge.objects.filter(is_active=True)
        serializer = ChallengeSerializer(challenges, many=True)
        return Response({
            'message': '테스트용 챌린지 목록입니다.',
            'challenges': serializer.data
        })
    
    def post(self, request):
        """테스트용 챌린지 판정 (뱃지 및 탈락 로직 포함)"""
        challenge_id = request.data.get('challenge_id')
        calories = request.data.get('calories', 1850)
        target_date_str = request.data.get('target_date')
        
        if not challenge_id:
            return Response(
                create_api_response(
                    success=False,
                    error='challenge_id가 필요합니다.',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # target_date 처리
        target_date = None
        if target_date_str:
            try:
                target_date = date.fromisoformat(target_date_str)
            except ValueError:
                return Response(
                    create_api_response(
                        success=False,
                        error='target_date 형식이 올바르지 않습니다. (YYYY-MM-DD)',
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        try:
            challenge = Challenge.objects.get(id=challenge_id, is_active=True)
            nutrition_data = get_mock_nutrition_data(calories, target_date)
            
            # 테스트용 사용자 생성 또는 가져오기
            from django.contrib.auth.models import User
            test_user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'email': 'testuser@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            
            # 참가자 생성 또는 가져오기
            participant, created = ChallengeParticipant.objects.get_or_create(
                challenge=challenge,
                user=test_user,
                defaults={'status': 'survived'}
            )
            
            # 챌린지 진행상황 업데이트 (뱃지 및 탈락 로직 포함)
            result = update_challenge_progress(
                challenge.id, test_user, nutrition_data, target_date
            )
            
            # 챌린지 요약 정보 추가
            summary = get_challenge_summary(participant)
            
            # 응답 데이터 구성
            response_data = {
                'challenge_name': challenge.name,
                'nutrition_data': nutrition_data,
                'evaluation_result': result,
                'challenge_summary': summary
            }
            
            return Response(
                create_api_response(
                    success=True,
                    data=response_data,
                    message='챌린지 평가가 완료되었습니다.',
                    status_code=200
                ),
                status=status.HTTP_200_OK
            )
            
        except Challenge.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='챌린지를 찾을 수 없습니다.',
                    status_code=404
                ),
                status=status.HTTP_404_NOT_FOUND
            )

class TestChallengeDetailAPIView(APIView):
    """인증 없이 접근 가능한 테스트용 챌린지 상세 API"""
    permission_classes = []
    
    def get(self, request, challenge_id):
        """테스트용 챌린지 상세 정보 조회"""
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            serializer = ChallengeDetailSerializer(challenge)
            return Response(serializer.data)
        except Challenge.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='챌린지를 찾을 수 없습니다.',
                    status_code=404
                ),
                status=status.HTTP_404_NOT_FOUND
            )

class TestChallengeParticipantsAPIView(APIView):
    """인증 없이 접근 가능한 테스트용 참여자 목록 API"""
    permission_classes = []
    
    def get(self, request, challenge_id):
        """테스트용 참여자 목록 조회"""
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            participants = ChallengeParticipant.objects.filter(challenge=challenge)
            
            # 참여자 데이터 구성
            participants_data = []
            for participant in participants:
                # 진행 상황 계산
                progress_records = ChallengeProgress.objects.filter(participant=participant)
                current_streak = 0
                max_streak = 0
                temp_streak = 0
                
                for record in progress_records.order_by('date'):
                    if record.target_achieved:
                        temp_streak += 1
                        current_streak = temp_streak
                        max_streak = max(max_streak, temp_streak)
                    else:
                        temp_streak = 0
                
                participants_data.append({
                    'id': participant.id,
                    'user_id': participant.user.id,
                    'username': participant.user.username,
                    'status': participant.status,
                    'current_streak': current_streak,
                    'max_streak': max_streak,
                    'joined_at': participant.joined_at.isoformat(),
                    'eliminated_at': participant.elimination_date.isoformat() if participant.elimination_date else None,
                    'last_activity': progress_records.order_by('-date').first().created_at.isoformat() if progress_records.exists() else None
                })
            
            return Response(participants_data)
        except Challenge.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='챌린지를 찾을 수 없습니다.',
                    status_code=404
                ),
                status=status.HTTP_404_NOT_FOUND
            )

class TestChallengeProgressAPIView(APIView):
    """인증 없이 접근 가능한 테스트용 진행 상황 API"""
    permission_classes = []
    
    def get(self, request, challenge_id):
        """테스트용 내 진행 상황 조회"""
        try:
            challenge = Challenge.objects.get(id=challenge_id)
            
            # 테스트용 사용자
            from django.contrib.auth.models import User
            test_user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'email': 'testuser@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            
            # 참가자 정보
            participant, created = ChallengeParticipant.objects.get_or_create(
                challenge=challenge,
                user=test_user,
                defaults={'status': 'active'}
            )
            
            # 진행 상황 계산
            progress_records = ChallengeProgress.objects.filter(participant=participant).order_by('date')
            
            current_streak = 0
            max_streak = 0
            temp_streak = 0
            success_days = 0
            failure_days = 0
            
            daily_progress = []
            for record in progress_records:
                if record.target_achieved:
                    temp_streak += 1
                    success_days += 1
                else:
                    temp_streak = 0
                    failure_days += 1
                
                max_streak = max(max_streak, temp_streak)
                
                daily_progress.append({
                    'date': record.date.isoformat(),
                    'actual_value': float(record.actual_value) if record.actual_value else None,
                    'is_success': record.target_achieved,
                    'notes': record.notes
                })
            
            # 현재 연속 기록 계산
            current_streak = temp_streak
            
            # 남은 실패 횟수 계산
            remaining_failures = challenge.max_failures - failure_days
            
            progress_data = {
                'current_streak': current_streak,
                'max_streak': max_streak,
                'total_days': progress_records.count(),
                'success_days': success_days,
                'failure_days': failure_days,
                'remaining_failures': max(0, remaining_failures),
                'daily_progress': daily_progress
            }
            
            return Response(progress_data)
        except Challenge.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='챌린지를 찾을 수 없습니다.',
                    status_code=404
                ),
                status=status.HTTP_404_NOT_FOUND
            )

class TestChallengeJoinAPIView(APIView):
    """인증 없이 접근 가능한 테스트용 챌린지 참여/포기 API"""
    permission_classes = []  # 인증 없이 접근 가능
    
    def post(self, request):
        """테스트용 챌린지 참여/포기"""
        action = request.data.get('action')  # 'join' 또는 'give_up'
        challenge_id = request.data.get('challenge_id')
        
        if not action or not challenge_id:
            return Response(
                create_api_response(
                    success=False,
                    error='action과 challenge_id가 필요합니다.',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            challenge = Challenge.objects.get(id=challenge_id, is_active=True)
            
            # 테스트용 사용자 생성 또는 가져오기
            from django.contrib.auth.models import User
            test_user, created = User.objects.get_or_create(
                username='testuser',
                defaults={
                    'email': 'testuser@example.com',
                    'first_name': 'Test',
                    'last_name': 'User'
                }
            )
            
            if action == 'join':
                # 챌린지 시작 여부 확인 (시작 후에는 참여 불가)
                from datetime import date
                today = date.today()
                if today >= challenge.start_date:
                    return Response(
                        create_api_response(
                            success=False,
                            error='챌린지가 이미 시작되어 참여할 수 없습니다. 시작 전에만 참여 가능합니다.',
                            status_code=400
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 기간 중복 확인
                has_overlap, overlapping_challenge = check_challenge_overlap(test_user, challenge)
                if has_overlap:
                    return Response(
                        create_api_response(
                            success=False,
                            error=f'같은 기간에 진행 중인 챌린지가 있습니다: {overlapping_challenge.name}',
                            status_code=400
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 이미 참여 중인지 확인
                if ChallengeParticipant.objects.filter(challenge=challenge, user=test_user).exists():
                    return Response(
                        create_api_response(
                            success=False,
                            error='이미 참여 중인 챌린지입니다.',
                            status_code=400
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 참가자 수 제한 확인
                if challenge.is_full:
                    return Response(
                        create_api_response(
                            success=False,
                            error='참가자 수가 가득 찼습니다.',
                            status_code=400
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # 참여자 생성
                participant = ChallengeParticipant.objects.create(
                    challenge=challenge,
                    user=test_user
                )
                
                return Response(
                    create_api_response(
                        success=True,
                        message='챌린지에 성공적으로 참여했습니다.',
                        status_code=201
                    ),
                    status=status.HTTP_201_CREATED
                )
                
            elif action == 'give_up':
                try:
                    participant = ChallengeParticipant.objects.get(
                        challenge=challenge,
                        user=test_user
                    )
                    participant.delete()
                    return Response(
                        create_api_response(
                            success=True,
                            message='챌린지를 포기했습니다.',
                            status_code=200
                        ),
                        status=status.HTTP_200_OK
                    )
                except ChallengeParticipant.DoesNotExist:
                    return Response(
                        create_api_response(
                            success=False,
                            error='참여 중인 챌린지가 아닙니다.',
                            status_code=400
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            else:
                return Response(
                    create_api_response(
                        success=False,
                        error='잘못된 action입니다. (join 또는 give_up)',
                        status_code=400
                    ),
                    status=status.HTTP_400_BAD_REQUEST
                )
                
        except Challenge.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='챌린지를 찾을 수 없습니다.',
                    status_code=404
                ),
                status=status.HTTP_404_NOT_FOUND
            )

class TestChallengeCreateAPIView(APIView):
    """인증 없이 접근 가능한 테스트용 챌린지 생성 API"""
    permission_classes = []  # 인증 없이 접근 가능
    
    def post(self, request):
        """테스트용 챌린지 생성"""
        try:
            # 요청 데이터 검증
            required_fields = ['name', 'description', 'target_type', 'target_value', 'start_date', 'end_date']
            for field in required_fields:
                if field not in request.data:
                    return Response(
                        create_api_response(
                            success=False,
                            error=f'{field} 필드가 필요합니다.',
                            status_code=400
                        ),
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            # 날짜 형식 변환
            from datetime import datetime
            start_date = datetime.fromisoformat(request.data['start_date'].replace('Z', '+00:00'))
            end_date = datetime.fromisoformat(request.data['end_date'].replace('Z', '+00:00'))
            
            # 챌린지 생성
            challenge_data = {
                'name': request.data['name'],
                'description': request.data['description'],
                'target_type': request.data['target_type'],
                'target_value': request.data['target_value'],
                'start_date': start_date,
                'end_date': end_date,
                'is_active': True,
                'max_participants': request.data.get('max_participants'),
                'max_failures': request.data.get('max_failures', 5)
            }
            
            challenge = Challenge.objects.create(**challenge_data)
            
            # 챌린지 생성자를 자동으로 참여자로 추가
            test_user = User.objects.get(username='testuser')
            ChallengeParticipant.objects.create(
                challenge=challenge,
                user=test_user,
                status='survived',
                current_streak=0,
                max_streak=0,
                failure_count=0
            )
            
            serializer = ChallengeSerializer(challenge)
            
            return Response(
                create_api_response(
                    success=True,
                    data=serializer.data,
                    message='챌린지가 성공적으로 생성되었습니다. 생성자가 자동으로 참여자로 추가되었습니다.',
                    status_code=201
                ),
                status=status.HTTP_201_CREATED
            )
            
        except ValueError as e:
            return Response(
                create_api_response(
                    success=False,
                    error=f'날짜 형식이 올바르지 않습니다: {str(e)}',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                create_api_response(
                    success=False,
                    error=f'챌린지 생성 중 오류가 발생했습니다: {str(e)}',
                    status_code=500
                ),
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ChallengeViewSet(viewsets.ModelViewSet):
    """
    챌린지 API 뷰셋
    
    제공 기능:
    - 챌린지 목록 조회 (GET /api/challenges/)
    - 챌린지 상세 조회 (GET /api/challenges/{id}/)
    - 챌린지 참여 (POST /api/challenges/{id}/join/)
    - 챌린지 탈퇴 (POST /api/challenges/{id}/leave/)
    - 내 챌린지 목록 (GET /api/challenges/my_challenges/)
    - 챌린지 테스트 평가 (POST /api/challenges/{id}/test_evaluate/)
    - 챌린지 요약 (GET /api/challenges/{id}/summary/)
    - 챌린지 통계 (GET /api/challenges/{id}/statistics/)
    """
    queryset = Challenge.objects.all()
    serializer_class = ChallengeSerializer
    permission_classes = []  # 임시로 인증 없이 접근 가능
    
    def get_queryset(self):
        """활성화된 챌린지만 반환"""
        return Challenge.objects.filter(is_active=True)
    
    def get_serializer_class(self):
        """액션에 따라 다른 시리얼라이저 사용"""
        if self.action == 'retrieve':
            return ChallengeDetailSerializer
        return ChallengeSerializer
    
    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """챌린지 참여"""
        challenge = self.get_object()
        user = request.user
        
        # 기간 중복 확인
        has_overlap, overlapping_challenge = check_challenge_overlap(user, challenge)
        if has_overlap:
            return Response(
                create_api_response(
                    success=False,
                    error=f'같은 기간에 진행 중인 챌린지가 있습니다: {overlapping_challenge.name}',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 이미 참여 중인지 확인
        if ChallengeParticipant.objects.filter(challenge=challenge, user=user).exists():
            return Response(
                create_api_response(
                    success=False,
                    error='이미 참여 중인 챌린지입니다.',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 참가자 수 제한 확인
        if challenge.is_full:
            return Response(
                create_api_response(
                    success=False,
                    error='참가자 수가 가득 찼습니다.',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 참여자 생성
        participant = ChallengeParticipant.objects.create(
            challenge=challenge,
            user=user
        )
        
        log_challenge_activity(participant, 'joined')
        
        serializer = ChallengeParticipantSerializer(participant)
        return Response(
            create_api_response(
                success=True,
                data=serializer.data,
                message='챌린지에 성공적으로 참여했습니다.',
                status_code=201
            ),
            status=status.HTTP_201_CREATED
        )
    
    @action(detail=True, methods=['post'])
    def give_up(self, request, pk=None):
        """챌린지 포기"""
        challenge = self.get_object()
        user = request.user
        
        try:
            participant = ChallengeParticipant.objects.get(
                challenge=challenge,
                user=user
            )
            log_challenge_activity(participant, 'gave_up')
            participant.delete()
            return Response(
                create_api_response(
                    success=True,
                    message='챌린지를 포기했습니다.',
                    status_code=200
                ),
                status=status.HTTP_200_OK
            )
        except ChallengeParticipant.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='참여 중인 챌린지가 아닙니다.',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def leave(self, request, pk=None):
        """챌린지 탈퇴 (기존 호환성 유지)"""
        return self.give_up(request, pk)
    
    @action(detail=False, methods=['get'], permission_classes=[])
    def my_challenges(self, request):
        """내가 참여 중인 챌린지 목록"""
        # 임시로 testuser 사용
        from django.contrib.auth.models import User
        test_user = User.objects.get(username='testuser')
        
        participations = ChallengeParticipant.objects.filter(user=test_user)
        challenges = [p.challenge for p in participations]
        
        serializer = ChallengeSerializer(challenges, many=True)
        return Response(
            create_api_response(
                success=True,
                data=serializer.data,
                message=f'참여 중인 챌린지 {len(challenges)}개를 조회했습니다.',
                status_code=200
            )
        )
    
    @action(detail=True, methods=['post'])
    def test_evaluate(self, request, pk=None):
        """챌린지 성공/실패 판정 테스트 (뱃지 및 탈락 로직 포함)"""
        challenge = self.get_object()
        user = request.user
        
        # Mock 영양정보 데이터 생성
        calories = request.data.get('calories', 1850)
        nutrition_data = get_mock_nutrition_data(calories)
        
        # 챌린지 진행상황 업데이트
        result = update_challenge_progress(
            challenge.id, user, nutrition_data
        )
        
        return Response(result, status=status.HTTP_200_OK)
    
    @action(detail=True, methods=['get'])
    def summary(self, request, pk=None):
        """챌린지 요약 정보 조회"""
        challenge = self.get_object()
        user = request.user
        
        try:
            participant = ChallengeParticipant.objects.get(
                challenge=challenge,
                user=user
            )
            # 최적화된 요약 정보 사용
            summary = get_optimized_challenge_summary(participant)
            return Response(
                create_api_response(
                    success=True,
                    data=summary,
                    message='챌린지 요약 정보를 조회했습니다.',
                    status_code=200
                )
            )
        except ChallengeParticipant.DoesNotExist:
            return Response(
                create_api_response(
                    success=False,
                    error='해당 챌린지에 참여 중이 아닙니다.',
                    status_code=404
                ),
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['get'])
    def statistics(self, request, pk=None):
        """챌린지 통계 정보 조회"""
        challenge = self.get_object()
        
        # 캐시에서 통계 데이터 조회
        cached_stats = get_cached_challenge_data(challenge.id, 'statistics')
        if cached_stats:
            return Response(
                create_api_response(
                    success=True,
                    data=cached_stats,
                    message='챌린지 통계 정보를 조회했습니다. (캐시)',
                    status_code=200
                )
            )
        
        # 참가자 통계 (최적화된 쿼리)
        participants_stats = ChallengeParticipant.objects.filter(
            challenge=challenge
        ).aggregate(
            total=Count('id'),
            active=Count('id', filter=Q(status='survived')),
            eliminated=Count('id', filter=Q(status='eliminated'))
        )
        
        # 성공률 통계 (최적화된 쿼리)
        evaluations_stats = ChallengeProgress.objects.filter(
            participant__challenge=challenge
        ).aggregate(
            total=Count('id'),
            successful=Count('id', filter=Q(target_achieved=True))
        )
        
        total_evaluations = evaluations_stats['total'] or 0
        successful_evaluations = evaluations_stats['successful'] or 0
        success_rate = (successful_evaluations / total_evaluations * 100) if total_evaluations > 0 else 0
        
        # 뱃지 통계
        total_badges = Badge.objects.filter(challenge=challenge).count()
        
        statistics_data = {
            'challenge_name': challenge.name,
            'participants': {
                'total': participants_stats['total'] or 0,
                'active': participants_stats['active'] or 0,
                'eliminated': participants_stats['eliminated'] or 0
            },
            'evaluations': {
                'total': total_evaluations,
                'successful': successful_evaluations,
                'success_rate': round(success_rate, 1)
            },
            'badges': {
                'total_awarded': total_badges
            }
        }
        
        # 캐시에 저장 (10분)
        set_cached_challenge_data(challenge.id, statistics_data, 600, 'statistics')
        
        return Response(
            create_api_response(
                success=True,
                data=statistics_data,
                message='챌린지 통계 정보를 조회했습니다.',
                status_code=200
            )
        )
    
    @action(detail=True, methods=['post'])
    def test_multiple_days(self, request, pk=None):
        """여러 날짜에 대한 챌린지 테스트"""
        challenge = self.get_object()
        user = request.user
        
        # 요청 데이터 파싱
        start_date_str = request.data.get('start_date')
        end_date_str = request.data.get('end_date')
        calories = request.data.get('calories', 1850)
        
        if not start_date_str or not end_date_str:
            return Response(
                create_api_response(
                    success=False,
                    error='start_date와 end_date가 필요합니다.',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            start_date = date.fromisoformat(start_date_str)
            end_date = date.fromisoformat(end_date_str)
        except ValueError:
            return Response(
                create_api_response(
                    success=False,
                    error='날짜 형식이 올바르지 않습니다. (YYYY-MM-DD)',
                    status_code=400
                ),
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # 여러 날짜에 대한 테스트 실행
        results = []
        current_date = start_date
        
        while current_date <= end_date:
            nutrition_data = get_mock_nutrition_data(calories, current_date)
            result = update_challenge_progress(
                challenge.id, user, nutrition_data, current_date
            )
            
            results.append({
                'date': current_date.isoformat(),
                'result': result
            })
            
            current_date += timedelta(days=1)
        
        return Response(
            create_api_response(
                success=True,
                data={
                    'challenge_name': challenge.name,
                    'test_period': {
                        'start_date': start_date_str,
                        'end_date': end_date_str
                    },
                    'results': results
                },
                message=f'{len(results)}일간의 챌린지 테스트가 완료되었습니다.',
                status_code=200
            )
        )

class ChallengeParticipantViewSet(viewsets.ModelViewSet):
    """챌린지 참가자 API 뷰셋"""
    queryset = ChallengeParticipant.objects.all()
    serializer_class = ChallengeParticipantSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 참여 정보만 반환"""
        return ChallengeParticipant.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def eliminate(self, request, pk=None):
        """참가자 탈락 처리 (관리자용)"""
        participant = self.get_object()
        participant.eliminate()
        serializer = self.get_serializer(participant)
        return Response(serializer.data)

class BadgeViewSet(viewsets.ModelViewSet):
    """뱃지 API 뷰셋"""
    queryset = Badge.objects.all()
    serializer_class = BadgeSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 뱃지만 반환"""
        return Badge.objects.filter(user=self.request.user)
    
    @action(detail=True, methods=['post'])
    def award(self, request, pk=None):
        """뱃지 획득 처리"""
        badge = self.get_object()
        badge.award()
        serializer = self.get_serializer(badge)
        return Response(serializer.data)

class ChallengeProgressViewSet(viewsets.ModelViewSet):
    """챌린지 진행 상황 API 뷰셋"""
    queryset = ChallengeProgress.objects.all()
    serializer_class = ChallengeProgressSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """현재 사용자의 진행 상황만 반환"""
        return ChallengeProgress.objects.filter(
            participant__user=self.request.user
        )
    
    def perform_create(self, serializer):
        """진행 상황 생성 시 참가자 자동 설정"""
        challenge_id = self.request.data.get('challenge_id')
        challenge = get_object_or_404(Challenge, id=challenge_id)
        participant = get_object_or_404(
            ChallengeParticipant,
            challenge=challenge,
            user=self.request.user
        )
        serializer.save(participant=participant)
    
    @action(detail=False, methods=['get'])
    def challenge_progress(self, request):
        """특정 챌린지의 진행 상황"""
        challenge_id = request.query_params.get('challenge_id')
        if not challenge_id:
            return Response(
                {'error': 'challenge_id 파라미터가 필요합니다.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            participant = ChallengeParticipant.objects.get(
                challenge_id=challenge_id,
                user=request.user
            )
            progress_records = ChallengeProgress.objects.filter(participant=participant)
            serializer = self.get_serializer(progress_records, many=True)
            return Response(serializer.data)
        except ChallengeParticipant.DoesNotExist:
            return Response(
                {'error': '해당 챌린지에 참여 중이 아닙니다.'},
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=False, methods=['post'])
    def test_batch_evaluate(self, request):
        """모든 참여 챌린지 일괄 평가 테스트 (뱃지 및 탈락 로직 포함)"""
        user = request.user
        
        # Mock 영양정보 데이터 생성
        calories = request.data.get('calories', 1850)
        nutrition_data = get_mock_nutrition_data(calories)
        
        # 모든 챌린지 일괄 평가
        results = batch_evaluate_challenges(user, nutrition_data)
        
        return Response({
            'nutrition_data': nutrition_data,
            'evaluation_results': results
        })
