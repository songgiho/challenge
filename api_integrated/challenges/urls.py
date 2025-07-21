from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ChallengeViewSet, ChallengeParticipantViewSet,
    BadgeViewSet, ChallengeProgressViewSet, TestChallengeAPIView, TestChallengeCreateAPIView, TestChallengeJoinAPIView,
    TestChallengeDetailAPIView, TestChallengeParticipantsAPIView, TestChallengeProgressAPIView
)

router = DefaultRouter()
router.register(r'challenges', ChallengeViewSet)
router.register(r'participants', ChallengeParticipantViewSet, basename='participant')
router.register(r'badges', BadgeViewSet, basename='badge')
router.register(r'progress', ChallengeProgressViewSet, basename='progress')

urlpatterns = [
    path('', include(router.urls)),
    path('api/test/', TestChallengeAPIView.as_view(), name='test-challenge-api'),
    path('api/test/create/', TestChallengeCreateAPIView.as_view(), name='test-challenge-create-api'),
    path('api/test/join/', TestChallengeJoinAPIView.as_view(), name='test-challenge-join-api'),
    path('api/test/<int:challenge_id>/', TestChallengeDetailAPIView.as_view(), name='test-challenge-detail-api'),
    path('api/test/<int:challenge_id>/participants/', TestChallengeParticipantsAPIView.as_view(), name='test-challenge-participants-api'),
    path('api/test/<int:challenge_id>/progress/', TestChallengeProgressAPIView.as_view(), name='test-challenge-progress-api'),
] 