from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import MealLogViewSet, AICoachTipViewSet, AnalyzeImageView, MonthlyLogView, DailyReportView, RecommendedChallengesView, MyChallengesView, UserBadgesView, RegisterView, LoginView, UserProfileStatsView, UserStatisticsView

router = DefaultRouter()
router.register(r'logs', MealLogViewSet)
router.register(r'ai/coaching-tip', AICoachTipViewSet, basename='aicoachtip') # basename 추가

urlpatterns = [
    # 커스텀 analyze-image 엔드포인트를 router보다 먼저 등록
    path('logs/analyze-image/', AnalyzeImageView.as_view(), name='analyze-image'),

    # router는 그 다음에
    path('', include(router.urls)),
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logs/monthly', MonthlyLogView.as_view(), name='monthly-logs'),
    path('logs/daily', DailyReportView.as_view(), name='daily-report'),
    path('challenges/recommended', RecommendedChallengesView.as_view(), name='recommended-challenges'),
    path('challenges/my-list', MyChallengesView.as_view(), name='my-challenges'),
    path('users/<str:username>/badges', UserBadgesView.as_view(), name='user-badges'),
    path('users/profile/stats', UserProfileStatsView.as_view(), name='user-profile-stats'),
    path('users/statistics', UserStatisticsView.as_view(), name='user-statistics'),
    # Custom API views will be added here
    path('challenge-main/', include('api.challenges.urls')),
]