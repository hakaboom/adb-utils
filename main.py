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


device = ADBDevice(device_id='192.168.50.164:5555')
fps_watcher = Fps(device)


surfaceView = fps_watcher.get_possible_layer(f'{device.foreground_package}')[0]
fps_watcher.clear_surfaceFlinger_latency()
while True:
    if ret := fps_watcher.get_fps_surfaceView(f"'{surfaceView}'"):
        fps, fTime, jank, bigJank, _ = ret
    else:
        fps = fTime = 0
    logger.debug(f'fps={fps:.1f}, 最大延迟={fTime:.2f}ms')
    time.sleep(1)
