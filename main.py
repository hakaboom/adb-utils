"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

import cv2
from loguru import logger

from baseImage import IMAGE

from adbutils import ADBDevice

device = ADBDevice(device_id='emulator-5554')

