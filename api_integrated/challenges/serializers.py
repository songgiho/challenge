from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Challenge, ChallengeParticipant, Badge, ChallengeProgress

class UserSerializer(serializers.ModelSerializer):
    """사용자 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class NestedChallengeParticipantSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    eliminationDate = serializers.DateTimeField(source='elimination_date', required=False)
    currentStreak = serializers.IntegerField(source='current_streak', required=False)
    maxStreak = serializers.IntegerField(source='max_streak', required=False)
    joinedAt = serializers.DateTimeField(source='joined_at', required=False)
    updatedAt = serializers.DateTimeField(source='updated_at', required=False)

    class Meta:
        model = ChallengeParticipant
        fields = [
            'id', 'user', 'status',
            'eliminationDate', 'currentStreak', 'maxStreak',
            'joinedAt', 'updatedAt'
        ]
        read_only_fields = ['user', 'status', 'eliminationDate', 'currentStreak', 'maxStreak', 'joinedAt', 'updatedAt']

class ChallengeSerializer(serializers.ModelSerializer):
    """챌린지 시리얼라이저"""
    startDate = serializers.DateField(source='start_date')
    endDate = serializers.DateField(source='end_date')
    targetType = serializers.CharField(source='target_type')
    targetValue = serializers.DecimalField(source='target_value', max_digits=10, decimal_places=2)
    isActive = serializers.BooleanField(source='is_active')
    maxParticipants = serializers.IntegerField(source='max_participants', required=False)
    currentParticipantsCount = serializers.IntegerField(source='current_participants_count', read_only=True)
    isFull = serializers.BooleanField(source='is_full', read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    participants = serializers.SerializerMethodField(read_only=True)

    class Meta:
        model = Challenge
        fields = [
            'id', 'name', 'description', 'startDate', 'endDate',
            'targetType', 'targetValue', 'isActive', 'maxParticipants',
            'currentParticipantsCount', 'isFull', 'createdAt', 'updatedAt',
            'participants'
        ]
        read_only_fields = ['createdAt', 'updatedAt']

    def get_participants(self, obj):
        participants = obj.participants.all() if hasattr(obj, 'participants') else []
        return NestedChallengeParticipantSerializer(participants, many=True).data if participants else []

class ChallengeParticipantSerializer(serializers.ModelSerializer):
    """챌린지 참가자 시리얼라이저"""
    user = UserSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)
    challengeId = serializers.IntegerField(source='challenge_id', write_only=True)
    eliminationDate = serializers.DateTimeField(source='elimination_date', required=False)
    currentStreak = serializers.IntegerField(source='current_streak', required=False)
    maxStreak = serializers.IntegerField(source='max_streak', required=False)
    joinedAt = serializers.DateTimeField(source='joined_at', required=False)
    updatedAt = serializers.DateTimeField(source='updated_at', required=False)

    class Meta:
        model = ChallengeParticipant
        fields = [
            'id', 'challenge', 'challengeId', 'user', 'status',
            'eliminationDate', 'currentStreak', 'maxStreak',
            'joinedAt', 'updatedAt'
        ]
        read_only_fields = ['user', 'status', 'eliminationDate', 'currentStreak', 'maxStreak', 'joinedAt', 'updatedAt']
    
    def create(self, validated_data):
        """참가자 생성 시 현재 사용자를 자동으로 설정"""
        challenge_id = validated_data.pop('challenge_id')
        validated_data['challenge_id'] = challenge_id
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class BadgeSerializer(serializers.ModelSerializer):
    """뱃지 시리얼라이저"""
    user = UserSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)
    iconUrl = serializers.URLField(source='icon_url')
    isAcquired = serializers.BooleanField(source='is_acquired')
    acquiredDate = serializers.DateTimeField(source='acquired_date', required=False)
    createdAt = serializers.DateTimeField(source='created_at', required=False)

    class Meta:
        model = Badge
        fields = [
            'id', 'name', 'description', 'iconUrl', 'isAcquired',
            'acquiredDate', 'user', 'challenge', 'createdAt'
        ]
        read_only_fields = ['user', 'isAcquired', 'acquiredDate', 'createdAt']

class ChallengeProgressSerializer(serializers.ModelSerializer):
    """챌린지 진행 상황 시리얼라이저"""
    participant = ChallengeParticipantSerializer(read_only=True)
    
    class Meta:
        model = ChallengeProgress
        fields = [
            'id', 'participant', 'date', 'target_achieved',
            'actual_value', 'notes', 'created_at'
        ]
        read_only_fields = ['created_at']

class ChallengeDetailSerializer(serializers.ModelSerializer):
    """챌린지 상세 정보 시리얼라이저"""
    startDate = serializers.DateField(source='start_date')
    endDate = serializers.DateField(source='end_date')
    targetType = serializers.CharField(source='target_type')
    targetValue = serializers.DecimalField(source='target_value', max_digits=10, decimal_places=2)
    isActive = serializers.BooleanField(source='is_active')
    maxParticipants = serializers.IntegerField(source='max_participants', required=False)
    currentParticipantsCount = serializers.IntegerField(source='current_participants_count', read_only=True)
    isFull = serializers.BooleanField(source='is_full', read_only=True)
    participants = ChallengeParticipantSerializer(many=True, read_only=True)
    createdAt = serializers.DateTimeField(source='created_at', read_only=True)
    updatedAt = serializers.DateTimeField(source='updated_at', read_only=True)
    userParticipation = serializers.SerializerMethodField()

    class Meta:
        model = Challenge
        fields = [
            'id', 'name', 'description', 'startDate', 'endDate',
            'targetType', 'targetValue', 'isActive', 'maxParticipants',
            'currentParticipantsCount', 'isFull', 'participants',
            'userParticipation', 'createdAt', 'updatedAt'
        ]
        read_only_fields = ['createdAt', 'updatedAt']

    def get_userParticipation(self, obj):
        """현재 사용자의 참여 정보 반환"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                participation = obj.participants.get(user=request.user)
                return ChallengeParticipantSerializer(participation).data
            except ChallengeParticipant.DoesNotExist:
                return None
        return None 