"""
python setup.py sdist
twine upload dist/*
"""
import re
import time
from loguru import logger

from adbutils import ADBExtraDevice
from adbutils.extra.performance.meminfo import Meminfo

device = ADBExtraDevice(device_id='emulator-5554', aapt=True)
meminf_watcher = Meminfo(device)