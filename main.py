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
from adbutils.extra.apk import Apk
from adbutils.extra.performance.fps import Fps

device = ADBDevice(device_id='emulator-5554')
