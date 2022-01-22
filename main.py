"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time
import os
from loguru import logger

from adbutils import ADBDevice
from adbutils.extra.performance import DeviceWatcher
from adbutils.extra.apk import Apk


device = ADBDevice(device_id='emulator-5554')

start_time = time.time()
for pkg_name in device.app_list('-3'):
    if 'android' in pkg_name:
        continue
    apk = Apk(device=device, packageName=pkg_name)
    apk.get_icon_file(local='./test/icon/{}.png'.format(pkg_name))
    logger.debug('next')
print(time.time() - start_time)