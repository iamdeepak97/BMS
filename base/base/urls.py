from django.contrib import admin
from django.urls import path , include
from core1 import views

urlpatterns = [
    path('admin/', admin.site.urls),
    
    path('', include('core1.urls')),
    
    
]
