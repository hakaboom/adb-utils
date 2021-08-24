# -*- coding: utf-8 -*-
import time
from threading import Thread, Event
from queue import Queue

from loguru import logger

from adbutils import ADBDevice
from adbutils.exceptions import AdbBaseError
from adbutils.extra.performance.cpu import Cpu
from adbutils.extra.performance.fps import Fps
from adbutils.extra.performance.meminfo import Meminfo

__all__ = ['DeviceWatcher']


class DeviceWatcher(object):
    def __init__(self, device: ADBDevice, package_name: str = None, surfaceView_name: str = None):
        self._surfaceView_name = surfaceView_name
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

        self._fps_usage_queue = Queue()
        self._fps_wait_event = Event()
        self._fps_wait_event.set()
        self._fps_watcher_thread: Thread = self.create_fps_watcher()

        if not self._surfaceView_name and self._package_name:
            if layers := self._fps_watcher.get_possible_activity():
                surfaceViews = self._fps_watcher.check_activity_usable(layers)
                if self._package_name in surfaceViews:
                    self._surfaceView_name = surfaceViews
            logger.debug(f'自动设置监控activity={self._surfaceView_name}')

    def create_cpu_watcher(self) -> Thread:
        """
        创建cpu监控线程

        Returns:
            cpu监控线程
        """

        def _get_cpu_usage():
            try:
                # total_cpu_usage, cpu_core_usage, app_usage_ret
                return self._cpu_watcher.get_cpu_usage(self._package_name)
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
                if self._package_name:
                    return self._mem_watcher.get_app_summary(self._package_name)
                else:
                    return None
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

        def _get_fps_usage():
            try:
                if self._surfaceView_name:
                    return self._fps_watcher.get_fps_surfaceView(f"{self._surfaceView_name}")
                return None
            except AdbBaseError as err:
                logger.error(err)
            return None

        def _run(kill_event: Event, wait_event: Event, q: Queue):
            while not kill_event.is_set():
                if not wait_event.is_set():
                    if fps_info := _get_fps_usage():
                        q.put(fps_info)
                    else:
                        q.put(None)
                    wait_event.set()

        _t = Thread(target=_run, name='mem_watcher',
                    args=(self._kill_event, self._fps_wait_event, self._fps_usage_queue))
        _t.daemon = True
        return _t

    def stop(self):
        self._kill_event.set()

    def start(self):
        if not self._cpu_watcher_thread.is_alive():
            self._cpu_watcher_thread.start()

        if not self._mem_watcher_thread.is_alive():
            self._mem_watcher_thread.start()

        if not self._fps_watcher_thread.is_alive():
            self._fps_watcher.clear_surfaceFlinger_latency()
            self._fps_watcher_thread.start()

    def get(self):
        """

        Returns:

        """
        self._mem_wait_event.clear()
        self._cpu_wait_event.clear()
        self._fps_wait_event.clear()

        cpu_usage = self._cpu_usage_queue.get()
        mem_usage = self._mem_usage_queue.get()
        fps_info = self._fps_usage_queue.get()

        return cpu_usage, mem_usage, fps_info


if __name__ == '__main__':
    from adbutils import ADBDevice
    from adbutils.extra.performance import DeviceWatcher

    device = ADBDevice(device_id='')
    a = DeviceWatcher(device, package_name=device.foreground_package)
    a.start()

    while True:
        start_time = time.time()
        cpu_usage, mem_usage, fps_info = a.get()
        delay_time = time.time() - start_time

        log = []
        if cpu_usage:
            total_cpu_usage, cpu_core_usage, app_usage_ret = cpu_usage
            log.append('cpu={} core={}, {}'.format(
                f'{total_cpu_usage:.1f}%',
                '\t'.join([f'cpu{core_index}:{usage:.1f}%' for core_index, usage in enumerate(cpu_core_usage)]),
                '\t'.join([f'{name}:{usage:.1f}%' for name, usage in app_usage_ret.items()]),
            ))

        if fps_info:
            fps, fTime, jank, bigJank, _ = fps_info
        else:
            fps = fTime = 0
        log.append(f'fps={fps:.1f}, 最大延迟={fTime:.2f}ms')

        logger.debug('\t'.join(log))
        if (sleep := (1 - delay_time)) > 0:
            time.sleep(sleep)
        else:
            time.sleep(1)
