import json
import signal
import sys
from time import sleep, time
from multiprocessing import Queue, Process
import cv2
from typing import List


class ManageCamera:

    DEFAULT_CONFIG = {
        'back_cam': True,
        'img_size': ['sm', 'md', 'lg'],
        'img_quality': [],
        'frame_rate': [],
        'crop': False,
        'ts': True,
        'port': 80,
        'user': "",
        'pass': "",
        'audio': False,
    }

    def __init__(self, url, monitor, record) -> None:
        self.url = url
        self.config = {}
        self.videos = []
        self.monitor_camera = monitor
        self.monitor = None  # Process
        self.record_camera = record
        self.record = None  # Process
        self._q = Queue()
        self.load_config()

    def get_videos(self) -> List:
        # Fetch list of video filename from filesystem
        pass

    def load_config(self) -> None:
        ''' Attemps to load config from file.

            If file is not found, default config is saved and used.
        '''

        try:
            with open(f'{self.url}_config.json', 'r') as f:
                self.config = json.load(f)
        except:
            with open(f"{self.url}_config.json", "w") as f:
                f.write(json.dump(self.DEFAULT_CONFIG))
            self.config = self.DEFAULT_CONFIG

    def begin(self) -> None:
        # Start process
        self.monitor = Process(
            target=self.monitor_camera.start, args=(self._q, self.url))
        self.monitor.start()
        self.record = Process(
            target=self.record_camera.start, args=(self._q, self.url))
        self.record.start()
        while True:
            pass

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
        self.queue = None
        self.cap = None

    def get_writer(self):
        if self.is_rec and self.writer:
            return self.writer

        self.writer = cv2.VideoWriter(
            f'output__{int(time())}.avi', cv2.VideoWriter_fourcc('M', 'J', 'P', 'G'), 15, (self.img.shape[1], self.img.shape[0]))
        return self.writer

    def check_cap(self):
        if self.cap is None or not self.cap.isOpened():
            self.cap = cv2.VideoCapture(self.url)
            ret, self.img = self.cap.read()

    def start(self, queue: Queue, url):
        self.url = url
        self.queue = queue
        self.check_cap()

        while True:
            # If we have a detect, start recording or reset time
            if self.check_detect():
                if not self.is_rec:
                    self.is_rec = True
                else:
                    print("Already recording...")

            if self.is_rec:
                self.record()

            if self.is_rec and time() - self.start_time_elapsed > self.REC_TIME:
                self.is_rec = False
                self.stop_recording()
            if self.is_rec:
                print(f"Rec: {time() - self.start_time_elapsed}")

    def check_detect(self):
        if not self.queue.empty():
            # Reset time,
            detect = self.queue.get()
            self.start_time_elapsed = time()
            return True
        return False

    def record(self):
        self.check_cap()
        print("Capturing frame")
        writer = self.get_writer()
        ret, img = self.cap.read()
        if ret:
            print("Writing img")
            writer.write(img)

    def stop_recording(self):
        print("Stopping the record!")
        self.writer = None


# Run on thread, when detecting motion, push msg on queue
class MonitorCamera:

    def __init__(self):
        self.avg = None

    def resize(self, img, scale):
        width = int(img.shape[1] * scale / 100)
        height = int(img.shape[0] * scale / 100)
        dim = (width, height)
        return cv2.resize(img, dim, interpolation=cv2.INTER_AREA)

    def start(self, queue: Queue, url: str):
        cap = cv2.VideoCapture(url)

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
                (x, y, w, h) = cv2.boundingRect(c)
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                print(f"Csize: {cv2.contourArea(c)}")
                text = "Occupied"
                queue.put("detect")

            # draw the text and timestamp on the frame
            timestamp = time() * 1000
            cv2.putText(img, f"Room Status: {text}", (10, 20),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
            cv2.putText(img, str(timestamp), (10, img.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX,
                        0.35, (0, 0, 255), 1)

            cv2.imshow("Security Feed", img)
            cv2.imshow("Security Delta", img_delta)
            key = cv2.waitKey(1) & 0xFF
            # if the `q` key is pressed, break from the lop
            if key == ord("q"):
                break

        cv2.destroyAllWindows()


class CameraManagement:
    def __init__(self):
        self.cameras = {
            # camera_url: ManageCamera(url, MonitorCamera(), RecordCamera())
        }
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
            self.cameras[url] = ManageCamera(
                url, MonitorCamera(), RecordCamera())

    def list_cameras(self):
        return sorted(self.cameras.keys())

    def add_camera(self, url):
        if url in self.cameras:
            return
        self.cameras[url] = ManageCamera(url, MonitorCamera(), RecordCamera())
        # Write url to file
        with open(self.prev_connected_cam_filename, "w") as f:
            f.write(f"{url}\n")

    def get_camera(self, url):
        return self.cameras[url]

    def remove_camera(self, url):
        del self.cameras[url]


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
