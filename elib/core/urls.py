from django.contrib import admin
from django.urls import path, include# <-- import views from your library app
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('library.urls')),  
]
