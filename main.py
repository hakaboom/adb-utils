"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import threading
import time

from threading import Event, Thread, Timer
from queue import Queue, Empty

from loguru import logger

from adbutils import ADBDevice
from adbutils.extra.performance.meminfo import Meminfo
from adbutils.extra.performance.fps import Fps
from adbutils.extra.performance.cpu import Cpu
from adbutils.exceptions import AdbBaseError


class DeviceWatcher(object):
    def __init__(self, device: ADBDevice, package_name: str = None):
        self._package_name = package_name
        self._device = device

        self._cpu_watcher = Cpu(self._device)
        self._fps_watcher = Fps(self._device)
        self._mem_watcher = Meminfo(self._device)

        self._kill_event = Event()
        self._wait_event = Event()
        self._wait_event.set()

        self._cpu_watcher_thread: Thread = None
        self._fps_watcher_thread: Thread = None
        self._mem_watcher_thread: Thread = None

        self._cpu_usage_queue = Queue()
        self._mem_usage_queue = Queue()

        self.create_cpu_watcher()
        self.create_mem_watcher()

    def create_cpu_watcher(self):
        def _get_cpu_usage():
            try:
                total_cpu_usage, cpu_core_usage, app_usage_ret = self._cpu_watcher.get_cpu_usage(self._package_name)
                return total_cpu_usage, cpu_core_usage, app_usage_ret
            except AdbBaseError as err:
                logger.error(err)
            return None

        def _run(kill_event: Event, wait_event: Event, q: Queue):
            while not kill_event.is_set():
                if not wait_event.is_set():
                    if cpu_usage := _get_cpu_usage():
                        q.put(cpu_usage)
                    else:
                        q.put(None)

        self._cpu_watcher_thread = Thread(target=_run, name='cpu_watcher',
                                          args=(self._kill_event, self._wait_event, self._cpu_usage_queue))
        self._cpu_watcher_thread.daemon = True

    def create_mem_watcher(self):
        def _get_mem_usage():
            try:
                app_mem = self._mem_watcher.get_app_summary(self._package_name)
                return app_mem
            except AdbBaseError as err:
                logger.error(err)
            return None

        def _run(kill_event: Event, wait_event: Event, q: Queue):
            while not kill_event.is_set():
                if not wait_event.is_set():
                    if app_mem := _get_mem_usage():
                        q.put(app_mem)
                    else:
                        q.put(None)

        self._mem_watcher_thread = Thread(target=_run, name='mem_watcher',
                                          args=(self._kill_event, self._wait_event, self._mem_usage_queue))
        self._mem_watcher_thread.daemon = True

    def stop(self):
        self._kill_event.set()

    def start(self):
        if not self._cpu_watcher_thread.is_alive():
            self._cpu_watcher_thread.start()

        if not self._mem_watcher_thread.is_alive():
            self._mem_watcher_thread.start()


device = ADBDevice(device_id='emulator-5554')
a = DeviceWatcher(device)
a.start()
time.sleep(2)
