from django.urls import path
from .views import (
    LeaderboardListView, 
    LeaderboardDetailView, 
    LeaderboardCreateView, 
    LeaderboardJoinView,
    LeaderboardManageView,
    LeaderboardMemberActionView,
    LeaderboardLeaveView
)
urlpatterns = [
    path('', LeaderboardListView.as_view(), name='leaderboard_list'),
    path('create/', LeaderboardCreateView.as_view(), name='leaderboard_create'),
    path('join/', LeaderboardJoinView.as_view(), name='leaderboard_join'),
    path('<int:pk>/leave/', LeaderboardLeaveView.as_view(), name='leaderboard_leave'),
    path('<int:pk>/manage/', LeaderboardManageView.as_view(), name='leaderboard_manage'),
    path('member/<int:pk>/action/', LeaderboardMemberActionView.as_view(), name='leaderboard_member_action'),
    path('<int:pk>/', LeaderboardDetailView.as_view(), name='leaderboard_detail'),
]