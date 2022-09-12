import cv2
from datetime import datetime
import json
from multiprocessing import Queue, Process, Manager
import os
import re
from cv2 import VideoCapture
import requests
import signal
import sys
from threading import Thread
from time import sleep, time
from typing import List

from .utils import Singleton

# instead of running all these classes on the same thread, run on separate threads....
# Then to call each method, send a command to run the comand.

VOLUME = "/app/api/vol/"
RECORD_DIR = f"{VOLUME}recordings"


def name(url: str):
    return url.split("//")[1].replace(".", "-")


class CameraFiles:
    def __init__(self, url_name: str):
        self.url_name = url_name
        self.path_re = re.compile(
            rf"{url_name}",  re.IGNORECASE | re.VERBOSE)

    def _add_date_to_filename(self, name):
        #  192-168-0-181_TYPE_1658366308.avi
        new_name = name
        try:
            under_split = name.split("_")
            dot_split = under_split[2].split(".")

            url = under_split[0]
            rec_type = under_split[1]
            fileext = dot_split[1]
            ts = dot_split[0]

            date = datetime.fromtimestamp(int(ts))
            new_name = f"{url}_{rec_type}_{date.strftime('%d-%m-%Y-%-H:%M:%S')}.{fileext}"
            print("New name: ", new_name)
        except Exception as e:
            print("Failed adding date to filename: ", e)
        return new_name

    def remove_video(self, filename) -> bool:

        # {"url":  "http://192.168.0.181", "filename": "192-168-0-181_1658374145.avi"}
        if not filename[-4:] == ".avi":
            print("Invalid filename to remove: ", filename, filename[-4:])
            return
        try:
            os.remove(f"{RECORD_DIR}/{filename}")
            return True
        except Exception as e:
            print("Failed to remove video: ", e)

        return False

    def get_videos(self):
        print("Getting video files for: ", self.path_re)
        filenames = {}
        for file in os.scandir(f"{RECORD_DIR}/"):
            if file.is_file():
                print("Found file: ", file.name)
                m = re.match(self.path_re, file.name)
                if m:
                    filenames[file.name] = (
                        self._add_date_to_filename(file.name))

        return filenames


class ManageCamera:
    CONFIG_PATH = f"{VOLUME}configs"
    DEFAULT_CONFIG = {
        'flash': False,
    }

    '''
        Management -> record   # manual start/ stop recording
        Record -> management   # started/ stopped recording
        Monitor -> record      # motion detected

    '''

    def __init__(self, url, monitor, record, record_manual, camera_files) -> None:
        self.url = url
        self.config = {}
        self.videos = []
        self.camera_files: CameraFiles = camera_files

        self.manager_queue_in = None  # Parent queue, communicate w/ CameraManagement
        self.manager_queue_out = None  # Parent queue, communicate w/ CameraManagement
        self.monitor_camera = monitor
        self.monitor = None  # Process
        self.record_camera = record
        self.record = None  # Process
        self.record_manual = record_manual
        self.manual_record_proc = None  # Process
        self.url_name = name(self.url)

        self.config_path = f'{self.CONFIG_PATH}/{self.url_name}_config.json'
        self._q_manage = Queue()  # This class's queue so children can put messages on it
        # Record class's queue so this class or monitor class can put messages on it
        self._q_record = Queue()
        self._q_manual_record = Queue()
        self._q_manage_manual = Queue()

        # Currently have no need to send message to monitor
        self._q_monitor = Queue()
        self.load_config()

    def get_info(self):
        return [self.config, self.url, self.config_path]

    def get_videos(self) -> List:
        # Fetch list of video filename from filesystem
        print("CameraManager: get_videos")
        return self.camera_files.get_videos()

    def remove_video(self, filename) -> List:
        # Fetch list of video filename from filesystem
        print("CameraManager: get_videos")
        return self.camera_files.remove_video(filename)

    def _update_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.config, f)

    def manual_record(self):
        self._q_manual_record.put("manual")
        print("Put manual")
        try:
            res = self._q_manage_manual.get(True, 2)
            print("Started recording?", res)
            return res
        except:
            print("Recorder did not respond...")
        return "Failed"

    def stop_manual_record(self):
        self._q_manual_record.put("stop_manual")
        try:
            res = self._q_manage_manual.get(True, 2)
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
        try:
            requests.get(f"{self.url}/?flash={ on_or_off }")
        except Exception as e:
            print("Failed to toggle flash: ", e)

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
            if not os.path.isdir(self.CONFIG_PATH):
                os.mkdir(self.CONFIG_PATH)

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
            target=self.record_camera.start_monitor, args=(self.url, self._q_record, self._q_manage))
        self.record.start()

        self.manual_record_proc = Process(
            target=self.record_manual.start_manual, args=(self.url, self._q_manual_record, self._q_manage_manual))
        self.manual_record_proc.start()

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
            method, data = self.manager_queue_in.get()
            if method == "get_videos":
                self.manager_queue_out.put(self.get_videos())
            elif method == "remove_video":
                self.manager_queue_out.put(self.remove_video(data))
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
        self.is_rec = False
        self.start_time_elapsed = 0  # seconds
        self.writer = None
        self.img = None
        self.url = None
        self.url_name = None
        self.record_queue = None
        self.cap: VideoCapture = None
        self.manual_rec = False
        self.manage_queue = None
        self.video_endpoint = "video.mjpg"
        # Possibly make this a setting if network conditions affect recordings...
        self.rec_fps = 4
        self.record_dir = RECORD_DIR
        self.record_type = None
        self._create_record_dir()

    def _create_record_dir(self):
        if not os.path.isdir(RECORD_DIR):
            os.mkdir(RECORD_DIR)

    def record_path(self):
        return f'{self.record_dir}/{self.url_name}_{self.record_type}_{int(time())}.avi'

    def get_writer(self):
        if self.is_rec and self.writer:
            return self.writer

        self.writer = cv2.VideoWriter(
            # f'{self._name}/output_{int(time())}.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 15, (self.img.shape[1], self.img.shape[0]))
            self.record_path(), cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), self.rec_fps, (self.img.shape[1], self.img.shape[0]))

        return self.writer

    def check_cap(self):
        ret = False

        if self.cap is None:
            self.cap = cv2.VideoCapture(f"{self.url}/{self.video_endpoint}")
            print("Checking cap ret is None: ", self.url, ret)

        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(f"{self.url}/{self.video_endpoint}")
            print("Checking cap ret is not opened: ", self.url, ret)

        ret, self.img = self.cap.read()
        if not ret:
            self.cap = cv2.VideoCapture(f"{self.url}/{self.video_endpoint}")

        ret, self.img = self.cap.read()
        return ret

    def start_monitor(self, url: str, record_queue: Queue, manage_queue: Queue):
        self.record_type = "motion"
        self.url = url
        self.url_name = name(url)
        self.record_queue = record_queue
        self.manage_queue = manage_queue
        self.check_cap()
        while True:
            # If we have a detect, start recording or reset time
            msg = self.check_detect()

            if msg == 'motion':
                print("Motion detected!!")
                self.is_rec = True
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

    def start_manual(self, url: str, record_queue: Queue, manage_queue: Queue):
        self.record_type = "manual"
        self.url = url
        self.url_name = name(url)
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

            if self.is_rec:
                self.record()

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
        self.is_rec = False


# Run on thread, when detecting motion, push msg on queue
class MonitorCamera:

    def __init__(self):
        self.avg = None
        self.video_endpoint = "video.mjpg"
        self.monitoring = False

    def resize(self, img, scale):
        width = int(img.shape[1] * scale / 100)
        height = int(img.shape[0] * scale / 100)
        dim = (width, height)
        return cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

    def start(self, queue: Queue, url: str):
        cap = cv2.VideoCapture(f"{url}/{self.video_endpoint}")

        while True:
            if not self.monitoring:
                continue

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
                queue.put("motion")

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
        self.prev_connected_cam_filename = f"{VOLUME}prev_cams.txt"
        self._get_prev_connected_cams()

        # Check config file for connected camers

    def _get_prev_connected_cams(self):
        # Open file
        print("Current working dir: ", os.getcwd())
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
        for url_name in self.cameras.keys():
            # Access the output queue of the camera and wait 2 sec max for it to put a response
            try:
                # print("List cameras: ", url_name)
                info = self.call_camera(
                    None, 'get_info', data=None, url_name=url_name)
                # dict: {flash: on/off, vid_path: ""}
                # print("Camera info: ", info)
                cams.append({
                    'url': info[1],
                    'config': info[0],
                    'videos': [info[1]],
                })
            except Exception as e:
                print(
                    f"Failed to get camera info: {url_name} ", e.with_traceback(None))
        return cams

    def add_camera(self, url) -> None:

        self._start_cam(url)

        # Write url to file
        with open(self.prev_connected_cam_filename, "a") as f:
            f.write(f"{url}\n")

    def _start_cam(self, url):
        ''' Starts the ManageCamera thread which starts the RecordCamera and MonitorCamera processess.

            camera => (input queue, output queue, ManageCamera )
            manager_queue_in => send to ManageCamera
            manager_queue_out => Coming from ManageCamera
        '''
        url_name = name(url)
        if url_name in self.cameras:
            return

        cam = ManageCamera(url, MonitorCamera(),
                           RecordCamera(), RecordCamera(), CameraFiles(url_name))
        manager_queue_in = Queue()
        manager_queue_out = Queue()
        cam_thread = Thread(target=cam.begin, args=(
            manager_queue_in, manager_queue_out,))
        cam_thread.start()
        # Send message into, read message from, instance of thread
        self.cameras[url_name] = (manager_queue_in,
                                  manager_queue_out, cam_thread)

    # instead of getting a camera and accessing its methods, send a command to its queue
    def call_camera(self, url, method, data=None, url_name=None) -> ManageCamera:
        print(f"Calling {method} for cam @ {url}")

        if url_name is None and url is not None:
            print(url)
            url_name = name(url)

        try:
            print(self.cameras)
            q_in = self.cameras[url_name][0]
            q_out = self.cameras[url_name][1]
            q_in.put((method, data))
        except Exception as e:
            print(f"Failed putting {method} on queue for cam @ {url_name}", e)

        # Todo get response...
        try:
            print(f"Waiting for {method} from cam @ {url_name}")
            x = q_out.get(True, 2)
            print(f"Recvd {x} for {method} from cam @ {url_name}")
            return x
        except:
            print(f"Failed to get call_camera res for {url_name}/{method}")

    def remove_camera(self, url) -> bool:
        info = ""
        try:
            info = self.call_camera(url, 'get_info')
            os.remove(info[2])
        except Exception as e:
            print("Failed to remove config", e, info)
            # return False

        try:
            # Overwrite prev_cams.txt
            os.remove(f"{VOLUME}prev_cams.txt")
        except Exception as e:
            print('Failed to remove prev_cams', e)
            return False

        try:
            print("Deleting url: ", url, self.cameras)
            del self.cameras[name(url)]
            camera_urls = self.cameras.keys()
            print("Wiriting new file")
            with open(f'{VOLUME}prev_cams.txt', 'w') as f:
                print("Wiriting new url: ", _url)
                for _url in camera_urls:
                    f.write(f'{_url}\n')
            return True
        except Exception as e:
            print('Failed to remove camera from class and rewrite prev_urls', e)
            return False

    def __del__(self):
        if len(self.cameras.values()) == 0:
            return
        for cam in self.cameras.values():
            print("Deleting cam thread", cam)
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
