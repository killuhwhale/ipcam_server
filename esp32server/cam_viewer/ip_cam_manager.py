import cv2
import json
from multiprocessing import Queue, Process, Manager
import os
import requests
import signal
import sys
from threading import Thread
from time import sleep, time
from typing import List

from .utils import Singleton

# instead of running all these classes on the same thread, run on separate threads....
# Then to call each method, send a command to run the comand.


class ManageCamera:
    CONFIG_PATH = "configs"
    DEFAULT_CONFIG = {
        'flash': False,
    }

    '''
        Management -> record   # manual start/ stop recording
        Record -> management   # started/ stopped recording
        Monitor -> record      # motion detected

    '''

    def __init__(self, url, monitor, record) -> None:
        self.url = url
        self.config = {}
        self.videos = []
        self.manager_queue_in = None  # Parent queue, communicate w/ CameraManagement
        self.manager_queue_out = None  # Parent queue, communicate w/ CameraManagement
        self.monitor_camera = monitor
        self.monitor = None  # Process
        self.record_camera = record
        self.record = None  # Process

        self.config_path = f'{self.CONFIG_PATH}/{self.name()}_config.json'
        self._q_manage = Queue()  # This class's queue so children can put messages on it
        # Record class's queue so this class or monitor class can put messages on it
        self._q_record = Queue()

        # Currently have no need to send message to monitor
        self._q_monitor = Queue()
        self.load_config()

    def get_info(self):
        return [self.config, self.name(), self.config_path]

    def get_videos(self) -> List:
        # Fetch list of video filename from filesystem
        pass

    def name(self):
        return self.url.split("//")[1]

    def _update_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

    def manual_record(self):
        self._q_record.put("manual")
        print("Put manual")
        try:
            res = self._q_manage.get(True, 2)
            print("Started recording?", res)
            return res
        except:
            print("Recorder did not respond...")
        return "Failed"

    def stop_manual_record(self):
        self._q_record.put("stop_manual")
        try:
            res = self._q_manage.get(True, 2)
            print("Stopped recording?", res)
            return res
        except:
            print("Recorder did not respond...")

        return "Failed"

    def toggle_flash(self):
        self.config['flash'] = not self.config['flash']         # Toggle flash
        on_or_off = "on" if self.config['flash'] else "off"     # Prepare url
        print("Flash should be going: ", on_or_off,
              f"{self.url}/?flash={ on_or_off }")
        # Send req to ipcam
        requests.get(f"{self.url}/?flash={ on_or_off }")
        self._update_config()                                    # Update user config
        # Return the state of the flash
        return self.config['flash']

    # Cant change config, no supporting API.
    def load_config(self) -> None:
        ''' Attemps to load config from file.

            If file is not found, default config is saved and used.
        '''

        try:
            with open(self.config_path, 'r') as f:
                self.config = json.load(f)
        except:
            with open(self.config_path, "w") as f:
                json.dump(self.DEFAULT_CONFIG, f)

            self.config = self.DEFAULT_CONFIG

    def begin(self, manager_queue_in, manager_queue_out) -> None:
        self.manager_queue_in = manager_queue_in
        self.manager_queue_out = manager_queue_out
        # Start process
        self.monitor = Process(
            target=self.monitor_camera.start, args=(self._q_record, self.url))
        self.monitor.start()
        self.record = Process(
            target=self.record_camera.start, args=(self.name(), self._q_record, self._q_manage, self.url))
        self.record.start()

        # TODO refine the calling to each method .
        # When putting a message on the queue, the message can get mixed up.
        # So, we can put our message on the queue, read the message, if its the method we expect in return, we are good
        # If not, we put the message back on that queue.
        # Bad scenario:
        '''
            Two calls to call_camera
            multiple get info calls, then a call to
            start_record,
        
            the repsonse is just put on the manager thread
            so the info is returned and caught by the second call to camera
            and messes up the info call and the start_record.
            
        
        '''
        while True:
            method = self.manager_queue_in.get()
            if method == "get_videos":
                self.manager_queue_out.put(self.get_videos())
            elif method == "manual_record":
                self.manager_queue_out.put(self.manual_record())
            elif method == "stop_manual_record":
                self.manager_queue_out.put(self.stop_manual_record())
            elif method == "toggle_flash":
                print("Toggling flash")
                self.manager_queue_out.put(self.toggle_flash())
            elif method == "get_info":
                print("Getting camera info")
                self.manager_queue_out.put(self.get_info())
            method = ""

    def _sigTerm(self) -> None:
        """Sets up the handling for terminating the process.
        The signal.SIGTERM signal is used for terminating a process.
        The signal.SIGINT is an tnterrupt from keyboard (CTRL + C).
        When the script terminates or interrupted by the user,
        the handle_exit method will be invoked.
        """
        signal.signal(signal.SIGTERM, self._handle_exit)
        signal.signal(signal.SIGINT, self._handle_exit)

    def _handle_exit(self, _signum, _frame) -> None:
        print(f"Ctl-C pressed! Closing... {_signum} - {_frame}")
        self.monitor.terminate()
        self.record.terminate()
        sys.exit()


# Manage recording of camera, read from queue and start recording for a fixed amount of time. Ignore messages from queue if already recording, just reset fixed time.
class RecordCamera:
    REC_TIME = 10

    def __init__(self):
        self._name = None
        self.is_rec = False
        self.start_time_elapsed = 0  # seconds
        self.writer = None
        self.img = None
        self.url = None
        self.record_queue = None
        self.cap = None
        self.manual_rec = False
        self.manage_queue = None
        self.video_endpoint = "video.mjpg"
        # Possibly make this a setting if network conditions affect recordings...
        self.rec_fps = 2
        self.record_dir = "recordings"

    def get_writer(self):
        if self.is_rec and self.writer:
            return self.writer

        self.writer = cv2.VideoWriter(
            # f'{self._name}/output_{int(time())}.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 15, (self.img.shape[1], self.img.shape[0]))
            f'{self.record_dir}/output_{int(time())}.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), self.rec_fps, (self.img.shape[1], self.img.shape[0]))

        return self.writer

    def check_cap(self):
        ret = False
        # print("Checking cap")
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(f"{self.url}/{self.video_endpoint}")
            print("Checking cap ret is None: ", self.url, ret)

        ret, self.img = self.cap.read()
        return ret

    def start(self, name, record_queue: Queue, manage_queue: Queue,  url: str):
        self._name = name
        self.url = url
        self.record_queue = record_queue
        self.manage_queue = manage_queue
        self.check_cap()
        while True:
            # If we have a detect, start recording or reset time
            msg = self.check_detect()

            if msg == 'stop_manual':
                self.manual_rec = False
                print("Stopping due to stop_manual signal")
                self.stop_recording()
                self.manage_queue.put("stopped")

            elif msg == "manual":
                if not self.is_rec:
                    if not self.check_cap():
                        self.manage_queue.put("cam_not_opened")
                        continue
                    print("starting to record")
                    self.manual_rec = True
                    self.record()
                    self.is_rec = True
                    self.start_time_elapsed = time()
                    self.manage_queue.put("started")
                continue

            elif msg == 'motion':
                if not self.is_rec:
                    self.is_rec = True
                else:
                    print("Already recording...")
                    self.start_time_elapsed = time()

            if self.is_rec:
                self.record()

            if self.is_rec and time() - self.start_time_elapsed > self.REC_TIME:
                self.is_rec = False
                print("Stopping due to time_elapsed signal",
                      time() - self.start_time_elapsed, self.REC_TIME)
                self.stop_recording()
            if self.is_rec:
                print(f"Rec: {time() - self.start_time_elapsed}")

    def check_detect(self):
        if not self.record_queue.empty():
            # Reset time,
            detect = self.record_queue.get()
            return detect
        return None

    def record(self):
        self.check_cap()
        # print("Capturing frame")
        writer = self.get_writer()
        ret, img = self.cap.read()
        if ret:
            # print("Writing img")
            writer.write(img)

    def stop_recording(self):
        print("Stopping the record!")
        self.writer = None


# Run on thread, when detecting motion, push msg on queue
class MonitorCamera:

    def __init__(self):
        self.avg = None
        self.video_endpoint = "video.mjpg"

    def resize(self, img, scale):
        width = int(img.shape[1] * scale / 100)
        height = int(img.shape[0] * scale / 100)
        dim = (width, height)
        return cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

    def start(self, queue: Queue, url: str):
        cap = cv2.VideoCapture(f"{url}/{self.video_endpoint}")

        while True:
            ret, img = cap.read()

            # grab the raw NumPy array representing the image and initialize
            # the timestamp and occupied/unoccupied text
            if not ret:
                continue
            text = "Unoccupied"
            # resize the frame, convert it to grayscale, and blur it
            # frame = self.resize(img, 50)
            gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
            gray = cv2.GaussianBlur(gray, (41, 41), 0)
            # if the average frame is None, initialize it
            if self.avg is None:
                print("[INFO] starting background model...")
                self.avg = gray.copy().astype("float")
                continue

            # accumulate the weighted average between the current frame and
            # previous frames, then compute the difference between the current
            # frame and running average
            cv2.accumulateWeighted(gray, self.avg, 0.8)
            img_delta = cv2.absdiff(gray, cv2.convertScaleAbs(self.avg))

            # threshold the delta image, dilate the thresholded image to fill
            # in holes, then find contours on thresholded image
            thresh = cv2.threshold(img_delta, 0.95, 255, cv2.THRESH_BINARY)[1]
            thresh = cv2.dilate(thresh, None, iterations=2)
            cnts = cv2.findContours(
                thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            cnts = cnts[0]

            for c in cnts:
                # if the contour is too small
                # , ignore it
                if cv2.contourArea(c) < 3000:
                    continue
                # compute the bounding box for the contour, draw it on the frame,
                # and update the text
                # (x, y, w, h) = cv2.boundingRect(c)
                # cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                # print(f"Csize: {cv2.contourArea(c)}")
                text = "Occupied"
                queue.put("detect")

            # draw the text and timestamp on the frame
            # timestamp = time() * 1000
            # cv2.putText(img, f"Room Status: {text}", (10, 20),
            #             cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            # cv2.putText(img, str(timestamp), (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
            #             0.35, (0, 0, 255), 1)

            # cv2.imshow("Security Feed", img)
            # cv2.imshow("Security Delta", img_delta)
            # key = cv2.waitKey(1) & 0xFF
            # # if the `q` key is pressed, break from the lop
            # if key == ord("q"):
            #     break

        # cv2.destroyAllWindows()


class CameraManagement(metaclass=Singleton):
    def __init__(self):
        self.cameras = {
            # camera_url: ManageCamera(url, MonitorCamera(), RecordCamera())
        }
        '''
            To list the cameras and get the config, and config path for ea camera,
            we need to ask for it because it is not in a separate thread....
        
        '''
        self.prev_connected_cam_filename = "prev_cams.txt"
        self._get_prev_connected_cams()

        # Check config file for connected camers

    def _get_prev_connected_cams(self):
        # Open file
        urls = []
        try:
            with open(self.prev_connected_cam_filename, "r") as f:
                urls = f.readlines()
        except:
            print("No previous urls found")
            with open(self.prev_connected_cam_filename, "w") as f:
                pass

        for url in urls:
            url = url.strip("\n")
            self._start_cam(url)

    def list_cameras(self) -> List[ManageCamera]:
        # return sorted(self.cameras.keys())
        cams = []
        for url in self.cameras.keys():
            # Access the output queue of the camera and wait 2 sec max for it to put a response
            try:
                info = self.call_camera(url, 'get_info')
                # dict: {flash: on/off, vid_path: ""}
                print("Camera info: ", info)
                cams.append({
                    'url': url,
                    'config': info[0],
                    'videos': [info[1]],
                })
            except:
                print(f"Failed to get camera info: {url}")
        return cams

    def add_camera(self, url) -> None:
        if url in self.cameras:
            return
        self._start_cam(url)

        # Write url to file
        with open(self.prev_connected_cam_filename, "a") as f:
            f.write(f"{url}\n")

    def _start_cam(self, url):

        cam = ManageCamera(url, MonitorCamera(), RecordCamera())
        manager_queue_in = Queue()
        manager_queue_out = Queue()
        cam_thread = Thread(target=cam.begin, args=(
            manager_queue_in, manager_queue_out,))
        cam_thread.start()
        # Send message into, read message from, instance of thread
        self.cameras[url] = (manager_queue_in, manager_queue_out, cam_thread)

    # instead of getting a camera and accessing its methods, send a command to its queue
    def call_camera(self, url, method) -> ManageCamera:
        print(f"Calling {method} for cam @ {url}")
        q_in = self.cameras[url][0]
        q_out = self.cameras[url][1]
        q_in.put(method)
        # Todo get response...
        try:
            x = q_out.get(True, 2)
            return x
        except:
            print(f"Failed to get call_camera res for {url}/{method}")

    def remove_camera(self, url) -> bool:
        try:

            info = self.call_camera(url, 'get_info')
            os.remove(info[2])
            del self.cameras[url]
            camera_urls = self.cameras.keys()
            # Overwrite prev_cams.txt
            os.remove("prev_cams.txt")
            with open('prev_cams.txt', 'w') as f:
                for url in camera_urls:
                    f.write(f'{url}\n')
            return True
        except Exception as e:
            print(e)
            return False

    def __del__(self):
        for cam in self.cameras.values:
            cam[2].join()


if __name__ == "__main__":
    url = "http://192.168.0.181/video.mjpg"
    m = ManageCamera(url, MonitorCamera(), RecordCamera())
    m.begin()

    '''
    TODO Allow changing of URL, for different cameras OR maybe just create multiple instances based on a list of URLs
    

    Create a Management Class that will manage each camera.
        - List all network devices, ips
        - List all connected cameras,
        - Add new camera
        - Remove camera
        - Get camera (update settings)

    Django should manage the CameraManagement class, start this program when the server starts
    User is able to use the CameraManagement class to:
    - See ip addresses of network devices
    - Add new camera, via a url
    - View connected camera streams
    - Update settings on each camera
    - View downloads for each camera, (Although this is intended to live on a home computer where youd see the files somewhere else mainly) 
    - 
    
    When starting server, Runserver => start ManageCamera for each url in configz
    
    
    '''
