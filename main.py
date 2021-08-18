"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice


device = ADBDevice(device_id='emulator-5554')
device.text('asdas', enter=True)
