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
from adbutils.extra.performance import DeviceWatcher

from adbutils import ADBDevice
from adbutils.extra.performance.meminfo import Meminfo

device = ADBDevice(device_id='emulator-5554')
performance = Meminfo(device)

performance.get_system_meminfo()

for i in range(100):
    package_name = device.foreground_package
    total = performance.get_app_summary(package_name)['total']
    # 打印package_name对应app的内存占用
    print(f'{(int(total) / 1024):.0f}MB')
