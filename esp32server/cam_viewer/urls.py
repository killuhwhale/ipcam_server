from django.urls import include, path
from rest_framework import routers
from . import views

router = routers.DefaultRouter()
router.register(r'cameras', views.CameraViewSet, basename='camera')

urlpatterns = [
    path('', include(router.urls)),
    # path('', views.index, name='index'),
]
