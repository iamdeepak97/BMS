from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('simulation/<int:simulation_id>/', views.simulation_results, name='simulation_results'),
    path('api/cell-specs/', views.get_cell_specs, name='get_cell_specs'),
]