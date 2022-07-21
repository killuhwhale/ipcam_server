import json
from asgiref.sync import sync_to_async
from django.http import FileResponse
from django.shortcuts import render
# Create your views here.
import requests
from time import time
import cv2

from rest_framework import renderers, viewsets
from rest_framework import permissions
from rest_framework.response import Response
from rest_framework.request import Request
from rest_framework.decorators import action


from .serializers import ManageCameraSerializer
from .ip_cam_manager import CameraManagement, RECORD_DIR

'''
url: used to connect to  stream
url_name: this is the camera name,  used in self.cameras and filenames

Incoming urls should be: url and not url_name


'''


'''
To implement a custom renderer, you should override BaseRenderer, set the .media_type and .format properties, and implement the .render(self, data, accepted_media_type=None, renderer_context=None) method.

The method should return a bytestring, which will be used as the body of the HTTP response.

'''


class PassthroughRenderer(renderers.BaseRenderer):
    """
        Return data as-is. View should supply a Response.
    """
    media_type = '*/*'
    format = ''

    def render(self, data, accepted_media_type="", renderer_context=None):
        return data


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
        print(f"Destroying ", request.data)
        res = CameraManagement().remove_camera(request.data)
        return Response(f"Camera successfully destroyed: {res}")

    @action(detail=False, methods=['post'])
    def toggle_flash(self, request, pk=None):
        print(f'Toggling {request.data}')
        toggle_state = CameraManagement().call_camera(request.data, 'toggle_flash')
        print("Viewset, toggle flash res: ", toggle_state)
        return Response(toggle_state if toggle_state else False)

    @action(detail=False, methods=['post'])
    def start_recording(self, request, pk=None):
        print(f'Recording {request.data}')
        res = CameraManagement().call_camera(request.data, 'manual_record')
        print("RES: ", res)
        return Response(res)

    @action(detail=False, methods=['post'])
    def stop_recording(self, request, pk=None):
        print(f'Stopped recording {request.data}')
        res = CameraManagement().call_camera(request.data, 'stop_manual_record')
        return Response(res)

    @action(detail=False, methods=['get'])
    def get_videos(self, request: Request, pk=None):
        print(f'Getting files for {request.query_params}')
        try:
            url = request.query_params['url']
            print("da url ", url)
            res = CameraManagement().call_camera(url, 'get_videos')
            return Response(res)
        except Exception as e:
            print(f"Can't find files w/ params: {request.query_params}")
            print("Error: ", e.with_traceback())

        return Response([])

    @action(detail=False, methods=['post'])
    def remove_videos(self, request: Request, pk=None):
        print(f'Removing files for {request.data}')
        try:
            filename = request.data['filename']
            url = request.data['url']
            res = CameraManagement().call_camera(url, 'remove_video',  data=filename)
            return Response(res)
        except Exception as e:
            print(f"Failed to remove w/ data: {request.data}")
            print("Error: ", e)

        return Response("Failed to remove video")

    @action(detail=False, methods=['get'], renderer_classes=(PassthroughRenderer,))
    def download_video(self, request: Request, pk=None):
        print(f'Downloading files for {request.query_params}')
        try:
            filename = request.query_params['filename']
            video_path = f"{RECORD_DIR}/{filename}"
            print(f"Path: {video_path}")
            video = open(video_path, "rb")
            video.seek(0, 2)
            l = video.tell()
            print(video)
            video.seek(0, 0)
            response = FileResponse(video, content_type='video/x-msvideo')
            response['Content-Length'] = l
            response['Content-Disposition'] = f'attachment; filename="{filename}"'

            return response
        except Exception as e:
            print(f"Failed to download w/ data: {request.query_params}")
            print("Error: ", e)

        return Response("Failed to remove video")
