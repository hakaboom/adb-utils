"""
python setup.py sdist
twine upload dist/*
"""
import re
import time
from loguru import logger
from baseImage import IMAGE

from adbutils import ADBExtraDevice
from adbutils.extra.performance.top import Top
from adbutils.extra.performance.meminfo import Meminfo

device = ADBExtraDevice(device_id='192.168.0.106:5555')
