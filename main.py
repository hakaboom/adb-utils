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


device = ADBDevice(device_id='192.168.1.8:5555')
fps_watcher = Fps(device)
package = f'{device.foreground_package}/{device.foreground_activity}'
while True:
    fps, fTime, jank, bigJank, _ = fps_watcher.get_fps_surfaceView(f"'SurfaceView - {package}#1'")
    logger.debug(f'fps={fps:.1f}, 最大延迟={fTime:.2f}ms')
    time.sleep(1)
