"""
python setup.py sdist
twine upload dist/*
"""
import re
import time
from loguru import logger
from baseImage import IMAGE

from adbutils import ADBDevice
from adbutils.extra.performance.top import Top

device = ADBDevice(device_id='emulator-5554')
top = Top(device)