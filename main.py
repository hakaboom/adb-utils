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
performance = Meminfo(device)
package_name = 'jp.co.cygames.umamusume'
#


for i in range(100):
    total = performance.get_app_summary(package_name)['total']
    print(f'{(int(total)/ 1024):.0f}MB')
