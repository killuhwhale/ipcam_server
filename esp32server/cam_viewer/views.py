import json
from django.shortcuts import render
# Create your views here.
import requests
from time import time
import cv2

from rest_framework import viewsets
from rest_framework import permissions
from rest_framework.response import Response

from .serializers import ManageCameraSerializer
from .ip_cam_manager import CameraManagement
''' Home Assistant Esp 32 cams, not very reliable. 
    cams = [
        "camera.no_home_iphone",
        "camera.cam1"
    ]
    endpoints = [
        "camera_proxy_stream",
        "camera_proxy"
    ]
    api_token = "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJjYTU0NmIxNmIwMzc0ODFmYTYzOWRhNjk4ODY3MWQ2MyIsImlhdCI6MTY1NzYxMTExMywiZXhwIjoxOTcyOTcxMTEzfQ.jl1_fqUzpZHajYb2VKvn-GJ6NIDedNct09CLpwT_N3s"
    headers = {
        "Authorization": f"Bearer {api_token}",
        "content-type": "application/json",
    }
    endpoint = f"/api/{endpoints[0]}/{cams[0]}?time={int(time()*1000)}"
'''


class CameraViewSet(viewsets.ViewSet):
    def list(self, request):
        # This gets the data returns a serialized response
        # Get all cameras and extract the information
        # return response
        for c in CameraManagement().list_cameras():
            print(c)

        cameras = [ManageCameraSerializer(
            c).data for c in CameraManagement().list_cameras()]
        return Response(cameras)

    def create(self, request):
        print("Creating new cam with data: ", request.data)
        print(request.data['url'])

        CameraManagement().add_camera(request.data['url'])
        return Response(f"Loud and clear: {request.data}")

    def retrieve(self, request, pk=None):
        pass

    def update(self, request, pk=None):
        pass

    def partial_update(self, request, pk=None):
        pass

    def destroy(self, request, pk=None):
        pass


# def index(request):
#     context = {
#         'vars_for_template': True,
#         "cam_urls": ["testURL1", "testURL2", "testURL3"],
#         "cam_settings": {
#             'testURL1': {
#                 'h_flip': False,
#             },
#             'testURL2': {
#                 'h_flip': False,
#             },
#             'testURL3': {
#                 'h_flip': False,
#             },
#         }
#     }

#     # TODO Get camera urls,
#     # TODO Get Settings for each camera

#     return render(request, 'cam_viewer/index.html', context)
