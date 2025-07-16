from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Challenge(models.Model):
    """챌린지 모델"""
    TARGET_TYPE_CHOICES = [
        ('weight', '체중'),
        ('calorie', '칼로리'),
        ('macro', '영양소'),
    ]
    
    name = models.CharField(max_length=100, verbose_name="챌린지명")
    description = models.TextField(verbose_name="설명")
    start_date = models.DateTimeField(verbose_name="시작일")
    end_date = models.DateTimeField(verbose_name="종료일")
    target_type = models.CharField(
        max_length=10, 
        choices=TARGET_TYPE_CHOICES,
        verbose_name="목표 타입"
    )
    target_value = models.DecimalField(
        max_digits=10, 
        decimal_places=2,
        verbose_name="목표값"
    )
    is_active = models.BooleanField(default=True, verbose_name="활성화 여부")
    max_participants = models.PositiveIntegerField(
        null=True, 
        blank=True,
        verbose_name="최대 참가자 수"
    )
    max_failures = models.PositiveIntegerField(
        default=5,
        verbose_name="최대 실패 가능 횟수"
    )
    meal_count = models.PositiveIntegerField(
        default=3,
        verbose_name="하루 식사 횟수"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "챌린지"
        verbose_name_plural = "챌린지들"
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    @property
    def current_participants_count(self):
        """현재 참가자 수"""
        return self.participants.filter(status='survived').count()
    
    @property
    def is_full(self):
        """참가자 수가 가득 찼는지 확인"""
        if self.max_participants is None:
            return False
        return self.current_participants_count >= self.max_participants

class ChallengeParticipant(models.Model):
    """챌린지 참가자 모델"""
    STATUS_CHOICES = [
        ('survived', '생존'),
        ('eliminated', '탈락'),
    ]
    
    challenge = models.ForeignKey(
        Challenge, 
        on_delete=models.CASCADE,
        related_name='participants',
        verbose_name="챌린지"
    )
    user = models.ForeignKey(
        User, 
        on_delete=models.CASCADE,
        related_name='challenge_participations',
        verbose_name="사용자"
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default='survived',
        verbose_name="상태"
    )
    elimination_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="탈락일"
    )
    current_streak = models.PositiveIntegerField(
        default=0,
        verbose_name="현재 연속 성공 횟수"
    )
    max_streak = models.PositiveIntegerField(
        default=0,
        verbose_name="최대 연속 성공 횟수"
    )
    failure_count = models.PositiveIntegerField(
        default=0,
        verbose_name="총 실패 횟수"
    )
    joined_at = models.DateTimeField(auto_now_add=True, verbose_name="참가일")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="수정일")
    
    class Meta:
        verbose_name = "챌린지 참가자"
        verbose_name_plural = "챌린지 참가자들"
        unique_together = ['challenge', 'user']
        ordering = ['-joined_at']
    
    def __str__(self):
        return f"{self.user.username} - {self.challenge.name}"
    
    def eliminate(self):
        """참가자를 탈락 처리"""
        from django.utils import timezone
        self.status = 'eliminated'
        self.elimination_date = timezone.now()
        self.save()
    
    def update_streak(self, success_count):
        """연속 성공 횟수 업데이트"""
        self.current_streak = success_count
        if success_count > self.max_streak:
            self.max_streak = success_count
        self.save()
    
    def increment_failure_count(self):
        """실패 횟수 증가"""
        self.failure_count = self.failure_count + 1
        self.save()
        
        # 실패 횟수가 최대 허용 횟수를 초과하면 탈락
        if self.failure_count > self.challenge.max_failures:
            self.eliminate()
            return True
        return False

class Badge(models.Model):
    """뱃지 모델"""
    name = models.CharField(max_length=100, verbose_name="뱃지명")
    description = models.TextField(verbose_name="설명")
    icon_url = models.URLField(verbose_name="아이콘 URL")
    is_acquired = models.BooleanField(default=False, verbose_name="획득 여부")
    acquired_date = models.DateTimeField(
        null=True, 
        blank=True,
        verbose_name="획득일"
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='badges',
        verbose_name="사용자"
    )
    challenge = models.ForeignKey(
        Challenge,
        on_delete=models.CASCADE,
        related_name='badges',
        verbose_name="챌린지"
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        verbose_name = "뱃지"
        verbose_name_plural = "뱃지들"
        ordering = ['-acquired_date']
    
    def __str__(self):
        return f"{self.user.username} - {self.name}"
    
    def award(self):
        """뱃지 획득 처리"""
        from django.utils import timezone
        self.is_acquired = True
        self.acquired_date = timezone.now()
        self.save()

class ChallengeProgress(models.Model):
    """챌린지 진행 상황 모델"""
    participant = models.ForeignKey(
        ChallengeParticipant,
        on_delete=models.CASCADE,
        related_name='progress_records',
        verbose_name="참가자"
    )
    date = models.DateField(verbose_name="날짜")
    target_achieved = models.BooleanField(default=False, verbose_name="목표 달성 여부")
    actual_value = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        verbose_name="실제 달성값"
    )
    notes = models.TextField(blank=True, verbose_name="메모")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="생성일")
    
    class Meta:
        verbose_name = "챌린지 진행 상황"
        verbose_name_plural = "챌린지 진행 상황들"
        unique_together = ['participant', 'date']
        ordering = ['-date']
    
    def __str__(self):
        return f"{self.participant} - {self.date}"
