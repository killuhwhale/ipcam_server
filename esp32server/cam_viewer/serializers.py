from rest_framework import serializers

''' What do I need to serialize?


I have 4 classes:
CameraManagement
    - ManageCamera(url, MonitorCamera(), RecordCamera())


ManageCamera
    - Runs Record and Monitor Camera in two separate processes that communicate w/ Q
MonitorCamera
    - Moniors cam @url for motion, once detected it pushes a message onto the queue
RecordCamera
    - Responds to messages on the queue, starts to record for X seconds once a message is received.
    - If a message is received from the queue while recording, the time is reset and records for another X seconds.
    - Each recording is save as: cam_name_timestamp.avi

Data:
    - List of objects representing the Camera
        - {
            url: "",
            config: {
                    back_cam: True,
                    img_size: [sm, md, lg],
                    img_quality: [],
                    frame_rate: [],
                    crop: False,
                    ts: True,
                    port: 80,
                    user: "",
                    pass: "",
                    audio: False,
            },
            videos: [
                'filename',
            ]
        } 

'''


class ManageCameraSerializer(serializers.Serializer):
    # str
    url = serializers.CharField(max_length=100)
    # 1d dict
    config = serializers.DictField()
    # list
    videos = serializers.ListField()
