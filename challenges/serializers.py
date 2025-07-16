from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Challenge, ChallengeParticipant, Badge, ChallengeProgress

class UserSerializer(serializers.ModelSerializer):
    """사용자 시리얼라이저"""
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']

class ChallengeSerializer(serializers.ModelSerializer):
    """챌린지 시리얼라이저"""
    current_participants_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'target_type', 'target_value', 'is_active', 'max_participants',
            'current_participants_count', 'is_full', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']

class ChallengeParticipantSerializer(serializers.ModelSerializer):
    """챌린지 참가자 시리얼라이저"""
    user = UserSerializer(read_only=True)
    challenge = ChallengeSerializer(read_only=True)
    challenge_id = serializers.IntegerField(write_only=True)
    
    class Meta:
        model = ChallengeParticipant
        fields = [
            'id', 'challenge', 'challenge_id', 'user', 'status',
            'elimination_date', 'current_streak', 'max_streak',
            'joined_at', 'updated_at'
        ]
        read_only_fields = ['user', 'status', 'elimination_date', 'current_streak', 'max_streak', 'joined_at', 'updated_at']
    
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
    
    class Meta:
        model = Badge
        fields = [
            'id', 'name', 'description', 'icon_url', 'is_acquired',
            'acquired_date', 'user', 'challenge', 'created_at'
        ]
        read_only_fields = ['user', 'is_acquired', 'acquired_date', 'created_at']

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
    participants = ChallengeParticipantSerializer(many=True, read_only=True)
    current_participants_count = serializers.ReadOnlyField()
    is_full = serializers.ReadOnlyField()
    user_participation = serializers.SerializerMethodField()
    
    class Meta:
        model = Challenge
        fields = [
            'id', 'name', 'description', 'start_date', 'end_date',
            'target_type', 'target_value', 'is_active', 'max_participants',
            'current_participants_count', 'is_full', 'participants',
            'user_participation', 'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']
    
    def get_user_participation(self, obj):
        """현재 사용자의 참여 정보 반환"""
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            try:
                participation = obj.participants.get(user=request.user)
                return ChallengeParticipantSerializer(participation).data
            except ChallengeParticipant.DoesNotExist:
                return None
        return None 