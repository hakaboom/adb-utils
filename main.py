"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice, ADBClient
from adbutils.extra.performance.meminfo import Meminfo

device = ADBDevice('emulator-5554')
meminfo = Meminfo(device)
print(meminfo.get_app_meminfo(device.foreground_package))