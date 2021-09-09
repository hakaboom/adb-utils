"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time
import os
from loguru import logger

from adbutils import ADBDevice, ADBClient
from adbutils.extra.aapt import Aapt
from adbutils.extra.performance.fps import Fps

device = ADBDevice(device_id='emulator-5554')
fps = Fps(device=device)
aapt = Aapt(device=device)

print(aapt._get_app_icon(name=device.foreground_package))

