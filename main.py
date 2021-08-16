"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice
from adbutils.extra.performance.fps import Fps

device = ADBDevice(device_id='emulator-5554')

fps_watcher = Fps(device=device)
fps_ret = []
pack = f"'SurfaceView - {device.foreground_package}/{device.foreground_activity}'"
for i in range(600):
    fps = fps_watcher.get_fps_surfaceView(f"{pack}")
    if fps:
        fps_ret.append(fps)
    print(f'当前FPS:{fps}')
    time.sleep(1)
#
print(f'最低FPS:{min(fps_ret)}\t'
      f'最大FPS:{max(fps_ret)}\t'
      f'AvgFPS:{sum(fps_ret)/len(fps_ret)}\t'
      f'FPS>=18:{len(list(filter(lambda num: num < 18, fps_ret))) / len(fps_ret) * 100:.2f}%\t'
      f'FPS>=25:{len(list(filter(lambda num: num < 25, fps_ret))) / len(fps_ret) * 100:.2f}%')
