from django.urls import path
from .views import PlacementStatisticAPIView, PlacementSearchAPIView

app_name = 'placement_api'

urlpatterns = [
    path('statistics/', PlacementStatisticAPIView.as_view(), name='placement_statistics_api'),
    path('search/', PlacementSearchAPIView.as_view(), name='placement_search_api'),
]
