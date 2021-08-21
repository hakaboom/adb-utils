# -*- coding: utf-8 -*-
from threading import Thread, Event
from queue import Queue

from loguru import logger

from adbutils import ADBDevice
from adbutils.exceptions import AdbBaseError
from adbutils.extra.performance.cpu import Cpu
from adbutils.extra.performance.fps import Fps
from adbutils.extra.performance.meminfo import Meminfo


class DeviceWatcher(object):
    def __init__(self, device: ADBDevice, package_name: str = None):
        self._package_name = package_name
        self._device = device

        self._cpu_watcher = Cpu(self._device)
        self._fps_watcher = Fps(self._device)
        self._mem_watcher = Meminfo(self._device)

        self._kill_event = Event()

        self._cpu_usage_queue = Queue()
        self._cpu_wait_event = Event()
        self._cpu_wait_event.set()
        self._cpu_watcher_thread: Thread = self.create_cpu_watcher()

        self._mem_usage_queue = Queue()
        self._mem_wait_event = Event()
        self._mem_wait_event.set()
        self._mem_watcher_thread: Thread = self.create_mem_watcher()

        self._fps_watcher_thread: Thread = None

        self.create_cpu_watcher()
        self.create_mem_watcher()

    def create_cpu_watcher(self) -> Thread:
        """
        创建cpu监控线程

        Returns:
            cpu监控线程
        """
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
                    logger.debug('put cpu')
                    if cpu_usage := _get_cpu_usage():
                        q.put(cpu_usage)
                    else:
                        q.put(None)
                    wait_event.set()

        _t = Thread(target=_run, name='cpu_watcher',
                    args=(self._kill_event, self._cpu_wait_event, self._cpu_usage_queue))
        _t.daemon = True
        return _t

    def create_mem_watcher(self) -> Thread:
        """
        创建内存监控线程

        Returns:
            内存监控线程
        """
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
                    logger.debug('put mem')
                    if app_mem := _get_mem_usage():
                        q.put(app_mem)
                    else:
                        q.put(None)
                    wait_event.set()

        _t = Thread(target=_run, name='mem_watcher',
                    args=(self._kill_event, self._mem_wait_event, self._mem_usage_queue))
        _t.daemon = True
        return _t

    def create_fps_watcher(self) -> Thread:
        """
        创建fps监控线程

        Returns:
            fps监控线程
        """

    def stop(self):
        self._kill_event.set()

    def start(self):
        if not self._cpu_watcher_thread.is_alive():
            self._cpu_watcher_thread.start()

        if not self._mem_watcher_thread.is_alive():
            self._mem_watcher_thread.start()

    def get_usage(self):
        """

        Returns:

        """
        self._mem_wait_event.clear()
        self._cpu_wait_event.clear()

        cpu_usage = self._cpu_usage_queue.get()
        mem_usage = self._mem_usage_queue.get()

        return cpu_usage, mem_usage
