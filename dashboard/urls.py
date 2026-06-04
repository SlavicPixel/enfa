from django.urls import path
from . import views

urlpatterns = [
    path("",              views.IndexView.as_view(),        name="index"),
    path("refresh/",      views.RefreshDataView.as_view(),  name="refresh_data"),
    path("<str:ticker>/", views.TickerDetailView.as_view(), name="ticker_detail"),
]