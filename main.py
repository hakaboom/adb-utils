"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice, ADBClient
from adbutils.extra.aapt import Aapt

device = ADBDevice(device_id='emulator-5554')
aapt = Aapt(device=device)

print(aapt.get_app_info(device.foreground_package))
