from django.urls import path
from .views import CompetitionListView, CompetitionDetailView, CompetitionLeaveView

urlpatterns = [
    path('', CompetitionListView.as_view(), name='competition_list'),
    path('<str:code>/leave/', CompetitionLeaveView.as_view(), name='competition_leave'),
    path('<str:code>/', CompetitionDetailView.as_view(), name='competition_detail')
]