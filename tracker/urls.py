from django.urls import path
from . import views

urlpatterns = [
    path('', views.login_view, name='login'),
    path('register/', views.register_view, name='register'),
    path('logout/', views.logout_view, name='logout'),
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('add-expense/', views.add_expense_view, name='add_expense'),
    path('set-budget/', views.set_budget_view, name='set_budget'),
    path('monthly-summary/', views.monthly_summary_view, name='monthly_summary'),
    path('export-csv/', views.export_csv_view, name='export_csv'),
]