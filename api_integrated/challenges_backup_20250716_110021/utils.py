import logging
from django.core.cache import cache
from django.db.models import Prefetch, Count, Avg
from django.utils import timezone
from datetime import date, timedelta, datetime
from .models import Challenge, ChallengeParticipant, ChallengeProgress, Badge

# 로거 설정
logger = logging.getLogger(__name__)

# 시간대별 식사 정의
MEAL_TIME_RANGES = {
    'breakfast': {
        'name': '아침',
        'start_time': '06:00',
        'end_time': '10:00',
        'order': 1
    },
    'lunch': {
        'name': '점심',
        'start_time': '11:00',
        'end_time': '14:00',
        'order': 2
    },
    'dinner': {
        'name': '저녁',
        'start_time': '17:00',
        'end_time': '21:00',
        'order': 3
    },
    'snack': {
        'name': '간식',
        'start_time': '10:00',
        'end_time': '11:00',
        'order': 4
    },
    'late_snack': {
        'name': '야식',
        'start_time': '21:00',
        'end_time': '06:00',
        'order': 5
    }
}

def get_meal_type_by_time(meal_time: datetime) -> str:
    """식사 시간을 기반으로 식사 타입을 반환"""
    time_str = meal_time.strftime('%H:%M')

    for meal_type, config in MEAL_TIME_RANGES.items():
        start_time = config['start_time']
        end_time = config['end_time']

        # 야식의 경우 자정을 넘어가는 경우 처리
        if meal_type == 'late_snack':
            if time_str >= '21:00' or time_str < '06:00':
                return meal_type
        else:
            if start_time <= time_str <= end_time:
                return meal_type

    return 'unknown'

def validate_meal_count(challenge: Challenge, meal_records: list, target_date: date) -> dict:
    """식사 횟수 검증"""
    required_meals = challenge.meal_count
    actual_meals = len(meal_records)

    # 기본 3끼 식사 검증 (아침, 점심, 저녁)
    required_meal_types = ['breakfast', 'lunch', 'dinner']
    actual_meal_types = [get_meal_type_by_time(record['meal_time']) for record in meal_records]

    missing_meals = []
    for required_type in required_meal_types:
        if required_type not in actual_meal_types:
            missing_meals.append(MEAL_TIME_RANGES[required_type]['name'])

    is_valid = len(missing_meals) == 0 and actual_meals >= required_meals

    return {
        'is_valid': is_valid,
        'required_meals': required_meals,
        'actual_meals': actual_meals,
        'missing_meals': missing_meals,
        'meal_types': actual_meal_types
    }

def check_challenge_overlap(user, new_challenge):
    """
    사용자가 같은 기간에 다른 챌린지에 참여 중인지 확인
    
    Args:
        user: User 모델 인스턴스
        new_challenge: 참여하려는 새로운 챌린지
        
    Returns:
        tuple: (겹침 여부, 겹치는 챌린지)
    """
    existing_participations = ChallengeParticipant.objects.filter(
        user=user,
        status='survived',
        challenge__is_active=True
    ).select_related('challenge')
    
    for participation in existing_participations:
        existing_challenge = participation.challenge
        
        # 기간 겹침 확인 (시작일과 종료일이 겹치는 경우)
        if (new_challenge.start_date <= existing_challenge.end_date and 
            new_challenge.end_date >= existing_challenge.start_date):
            return True, existing_challenge
    
    return False, None

def get_cached_challenge_data(challenge_id, cache_key_suffix=''):
    """
    캐시된 챌린지 데이터 조회

    Args:
        challenge_id: 챌린지 ID
        cache_key_suffix: 캐시 키 접미사

    Returns:
        dict: 캐시된 데이터 또는 None
    """
    cache_key = f'challenge_data_{challenge_id}_{cache_key_suffix}'
    return cache.get(cache_key)

def set_cached_challenge_data(challenge_id, data, timeout=300, cache_key_suffix=''):
    """
    챌린지 데이터 캐시 저장

    Args:
        challenge_id: 챌린지 ID
        data: 캐시할 데이터
        timeout: 캐시 만료 시간 (초)
        cache_key_suffix: 캐시 키 접미사
    """
    cache_key = f'challenge_data_{challenge_id}_{cache_key_suffix}'
    cache.set(cache_key, data, timeout)

def invalidate_challenge_cache(challenge_id):
    """
    챌린지 관련 캐시 무효화

    Args:
        challenge_id: 챌린지 ID
    """
    cache_keys = [
        f'challenge_data_{challenge_id}_summary',
        f'challenge_data_{challenge_id}_statistics',
        f'challenge_data_{challenge_id}_participants'
    ]

    for key in cache_keys:
        cache.delete(key)

def get_optimized_challenge_summary(participant):
    """
    최적화된 챌린지 요약 정보 반환 (캐싱 포함)

    Args:
        participant: ChallengeParticipant 모델 인스턴스

    Returns:
        dict: 챌린지 요약 정보
    """
    challenge_id = participant.challenge.id
    cache_key = f'summary_{participant.user.id}_{challenge_id}'

    # 캐시에서 조회
    cached_summary = cache.get(cache_key)
    if cached_summary:
        return cached_summary

    # 데이터베이스에서 조회 (최적화된 쿼리)
    progress_records = ChallengeProgress.objects.filter(
        participant=participant
    ).select_related('participant')

    total_days = progress_records.count()
    success_days = progress_records.filter(target_achieved=True).count()
    success_rate = (success_days / total_days * 100) if total_days > 0 else 0

    summary = {
        'challenge_name': participant.challenge.name,
        'total_days': total_days,
        'success_days': success_days,
        'success_rate': round(success_rate, 1),
        'current_streak': participant.current_streak,
        'max_streak': participant.max_streak,
        'failure_count': participant.failure_count,
        'max_failures': participant.challenge.max_failures,
        'status': participant.status,
        'elimination_date': participant.elimination_date
    }

    # 캐시에 저장 (5분)
    cache.set(cache_key, summary, 300)

    return summary

def create_api_response(success=True, data=None, message=None, error=None, status_code=200):
    """
    표준화된 API 응답 생성

    Args:
        success: 성공 여부
        data: 응답 데이터
        message: 성공 메시지
        error: 에러 메시지
        status_code: HTTP 상태 코드

    Returns:
        dict: 표준화된 응답
    """
    response = {
        'success': success,
        'timestamp': timezone.now().isoformat(),
        'status_code': status_code
    }

    if data is not None:
        response['data'] = data

    if message:
        response['message'] = message

    if error:
        response['error'] = error

    return response

def log_challenge_activity(participant, action, details=None):
    """
    챌린지 활동 로깅

    Args:
        participant: ChallengeParticipant 모델 인스턴스
        action: 수행된 액션
        details: 추가 세부사항
    """
    log_data = {
        'user_id': participant.user.id,
        'username': participant.user.username,
        'challenge_id': participant.challenge.id,
        'challenge_name': participant.challenge.name,
        'action': action,
        'timestamp': timezone.now().isoformat()
    }

    if details:
        log_data.update(details)

    logger.info(f"Challenge Activity: {log_data}")

def evaluate_challenge_success(challenge, nutrition_data, meal_records=None):
    """
    챌린지 성공/실패 판정 (식사 횟수 검증 포함)

    Args:
        challenge: Challenge 모델 인스턴스
        nutrition_data: 영양정보 딕셔너리 (예: {'total_calories': 1850})
        meal_records: 식사 기록 리스트 (예: [{'meal_time': datetime, 'calories': 500}])

    Returns:
        dict: {'success': bool, 'actual_value': float, 'target_value': float, 'meal_validation': dict}
    """
    if challenge.target_type == 'calorie':
        actual_calories = nutrition_data.get('total_calories', 0)
        target_calories = float(challenge.target_value)

        # 기본 칼로리 검증
        calorie_success = actual_calories <= target_calories
        
        # 식사 횟수 검증 (meal_records가 제공된 경우)
        meal_validation = None
        if meal_records:
            meal_validation = validate_meal_count(challenge, meal_records, nutrition_data.get('date', date.today()))
            # 칼로리와 식사 횟수 모두 만족해야 성공
            success = calorie_success and meal_validation['is_valid']
        else:
            # meal_records가 없으면 칼로리만 검증
            success = calorie_success
            meal_validation = {
                'is_valid': True,
                'required_meals': challenge.meal_count,
                'actual_meals': 0,
                'missing_meals': [],
                'meal_types': []
            }

        message = f"목표: {target_calories}kcal, 실제: {actual_calories}kcal"
        if meal_validation and not meal_validation['is_valid']:
            missing_meals_str = ', '.join(meal_validation['missing_meals'])
            message += f" | 누락된 식사: {missing_meals_str}"

        return {
            'success': success,
            'actual_value': actual_calories,
            'target_value': target_calories,
            'meal_validation': meal_validation,
            'message': message
        }

    # 다른 타입의 챌린지가 추가될 경우 여기에 확장
    return {
        'success': False,
        'actual_value': 0,
        'target_value': 0,
        'meal_validation': None,
        'message': '지원하지 않는 챌린지 타입입니다.'
    }

def create_badge_for_success(participant, challenge):
    """
    챌린지 성공 시 뱃지 생성

    Args:
        participant: ChallengeParticipant 모델 인스턴스
        challenge: Challenge 모델 인스턴스

    Returns:
        Badge: 생성된 뱃지 또는 None
    """
    # 이미 뱃지를 획득했는지 확인
    if Badge.objects.filter(user=participant.user, challenge=challenge).exists():
        return None

    # 성공률에 따른 뱃지 등급 결정
    success_rate = calculate_success_rate(participant)

    if success_rate >= 0.9:
        badge_name = "완벽한 다이어터"
        badge_description = "90% 이상의 성공률을 달성한 완벽한 다이어터입니다!"
        icon_url = "/badges/perfect_dieter.png"
    elif success_rate >= 0.7:
        badge_name = "성실한 다이어터"
        badge_description = "70% 이상의 성공률을 달성한 성실한 다이어터입니다!"
        icon_url = "/badges/diligent_dieter.png"
    elif success_rate >= 0.5:
        badge_name = "노력하는 다이어터"
        badge_description = "50% 이상의 성공률을 달성한 노력하는 다이어터입니다!"
        icon_url = "/badges/trying_dieter.png"
    else:
        badge_name = "시작하는 다이어터"
        badge_description = "챌린지에 참여하여 첫 발걸음을 내딛은 다이어터입니다!"
        icon_url = "/badges/beginner_dieter.png"

    # 뱃지 생성
    badge = Badge.objects.create(
        name=badge_name,
        description=badge_description,
        icon_url=icon_url,
        user=participant.user,
        challenge=challenge,
        is_acquired=True,
        acquired_date=timezone.now()
    )

    return badge

def calculate_success_rate(participant):
    """
    참가자의 성공률 계산

    Args:
        participant: ChallengeParticipant 모델 인스턴스

    Returns:
        float: 성공률 (0.0 ~ 1.0)
    """
    progress_records = ChallengeProgress.objects.filter(participant=participant)

    if not progress_records.exists():
        return 0.0

    total_days = progress_records.count()
    success_days = progress_records.filter(target_achieved=True).count()

    return success_days / total_days

def check_elimination_conditions(participant):
    """
    탈락 조건 확인 및 처리 (총 실패 횟수 기반)

    Args:
        participant: ChallengeParticipant 모델 인스턴스

    Returns:
        bool: 탈락 여부
    """
    # 실패 횟수가 최대 허용 횟수를 초과했는지 확인
    if participant.failure_count > participant.challenge.max_failures:
        participant.eliminate()
        return True

    return False

def update_challenge_progress(challenge_id, user, nutrition_data, target_date=None):
    """
    챌린지 진행상황 업데이트 (뱃지 및 탈락 로직 포함)

    Args:
        challenge_id: 챌린지 ID
        user: User 모델 인스턴스
        nutrition_data: 영양정보 딕셔너리
        target_date: 평가할 날짜 (기본값: 오늘)

    Returns:
        dict: 표준화된 API 응답
    """
    if target_date is None:
        target_date = date.today()

    try:
        # 챌린지와 참가자 확인
        challenge = Challenge.objects.get(id=challenge_id, is_active=True)
        participant = ChallengeParticipant.objects.get(
            challenge=challenge,
            user=user,
            status='survived'
        )

        # 챌린지 성공/실패 판정
        evaluation = evaluate_challenge_success(challenge, nutrition_data)

        # ChallengeProgress 생성 또는 업데이트
        progress, created = ChallengeProgress.objects.get_or_create(
            participant=participant,
            date=target_date,
            defaults={
                'target_achieved': evaluation['success'],
                'actual_value': evaluation['actual_value'],
                'notes': evaluation['message']
            }
        )

        if not created:
            # 기존 기록이 있으면 업데이트
            progress.target_achieved = evaluation['success']
            progress.actual_value = evaluation['actual_value']
            progress.notes = evaluation['message']
            progress.save()

        # 연속 성공 횟수 업데이트
        update_streak(participant, target_date)

        # 실패 시 실패 횟수 증가
        eliminated = False
        if not evaluation['success']:
            eliminated = participant.increment_failure_count()
            log_challenge_activity(participant, 'failure_incremented', {
                'failure_count': participant.failure_count,
                'max_failures': challenge.max_failures
            })

        # 성공 시 뱃지 획득 시도
        badge_acquired = None
        if evaluation['success']:
            badge_acquired = create_badge_for_success(participant, challenge)
            if badge_acquired:
                log_challenge_activity(participant, 'badge_acquired', {
                    'badge_name': badge_acquired.name
                })

        # 탈락 처리
        if eliminated:
            log_challenge_activity(participant, 'eliminated', {
                'failure_count': participant.failure_count,
                'max_failures': challenge.max_failures
            })

        # 캐시 무효화
        invalidate_challenge_cache(challenge.id)

        result_data = {
            'challenge_name': challenge.name,
            'evaluation': evaluation,
            'progress_updated': True,
            'badge_acquired': badge_acquired.name if badge_acquired else None,
            'eliminated': eliminated,
            'target_date': target_date.isoformat(),
            'failure_count': participant.failure_count,
            'max_failures': challenge.max_failures
        }

        message = None
        if eliminated:
            message = f'총 실패 횟수({participant.failure_count}회)가 최대 허용 횟수({challenge.max_failures}회)를 초과하여 탈락했습니다.'
        elif evaluation['success']:
            message = '챌린지 목표를 달성했습니다!'
        else:
            message = '챌린지 목표를 달성하지 못했습니다.'

        return create_api_response(
            success=True,
            data=result_data,
            message=message,
            status_code=200
        )

    except Challenge.DoesNotExist:
        logger.warning(f"Challenge not found: challenge_id={challenge_id}, user_id={user.id}")
        return create_api_response(
            success=False,
            error='챌린지를 찾을 수 없습니다.',
            status_code=404
        )
    except ChallengeParticipant.DoesNotExist:
        logger.warning(f"Participant not found: challenge_id={challenge_id}, user_id={user.id}")
        return create_api_response(
            success=False,
            error='해당 챌린지에 참여 중이 아닙니다.',
            status_code=404
        )
    except Exception as e:
        logger.error(f"Error updating challenge progress: {str(e)}", exc_info=True)
        return create_api_response(
            success=False,
            error='챌린지 진행상황 업데이트 중 오류가 발생했습니다.',
            status_code=500
        )

def update_streak(participant, target_date):
    """
    연속 성공 횟수 업데이트

    Args:
        participant: ChallengeParticipant 모델 인스턴스
        target_date: 평가할 날짜
    """
    # 최근 7일간의 진행상황 조회
    recent_progress = ChallengeProgress.objects.filter(
        participant=participant,
        date__gte=target_date - timedelta(days=7),
        date__lte=target_date
    ).order_by('date')

    current_streak = 0
    max_streak = participant.max_streak

    # 최근 날짜부터 역순으로 연속 성공 횟수 계산
    for progress in reversed(recent_progress):
        if progress.target_achieved:
            current_streak += 1
        else:
            break

    # 최대 연속 성공 횟수 업데이트
    if current_streak > max_streak:
        max_streak = current_streak

    participant.current_streak = current_streak
    participant.max_streak = max_streak
    participant.save()

def get_mock_nutrition_data(calories=1850, target_date=None):
    """
    테스트용 Mock 영양정보 데이터 생성

    Args:
        calories: 총 칼로리 (기본값: 1850)
        target_date: 대상 날짜 (기본값: 오늘)

    Returns:
        dict: Mock 영양정보
    """
    if target_date is None:
        target_date = date.today()

    return {
        'total_calories': calories,
        'total_carbs': 220,
        'total_protein': 90,
        'total_fat': 60,
        'date': target_date.isoformat()
    }

def batch_evaluate_challenges(user, nutrition_data, target_date=None):
    """
    사용자가 참여 중인 모든 챌린지에 대해 일괄 평가

    Args:
        user: User 모델 인스턴스
        nutrition_data: 영양정보 딕셔너리
        target_date: 평가할 날짜 (기본값: 오늘)

    Returns:
        list: 각 챌린지별 평가 결과
    """
    if target_date is None:
        target_date = date.today()

    results = []
    participations = ChallengeParticipant.objects.filter(
        user=user,
        status='survived'
    ).select_related('challenge')

    for participation in participations:
        challenge = participation.challenge
        if challenge.is_active and challenge.start_date <= timezone.now() <= challenge.end_date:
            result = update_challenge_progress(
                challenge.id, user, nutrition_data, target_date
            )
            results.append({
                'challenge_id': challenge.id,
                'challenge_name': challenge.name,
                'result': result
            })

    return results

def get_challenge_summary(participant):
    """
    챌린지 요약 정보 반환

    Args:
        participant: ChallengeParticipant 모델 인스턴스

    Returns:
        dict: 챌린지 요약 정보
    """
    progress_records = ChallengeProgress.objects.filter(participant=participant)
    total_days = progress_records.count()
    success_days = progress_records.filter(target_achieved=True).count()
    success_rate = calculate_success_rate(participant)

    return {
        'challenge_name': participant.challenge.name,
        'total_days': total_days,
        'success_days': success_days,
        'success_rate': round(success_rate * 100, 1),
        'current_streak': participant.current_streak,
        'max_streak': participant.max_streak,
        'failure_count': participant.failure_count,
        'max_failures': participant.challenge.max_failures,
        'status': participant.status,
        'elimination_date': participant.elimination_date
    } 