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
from adbutils.extra.performance.fps import Fps

device = ADBDevice(device_id='emulator-5554')
fps = Fps(device=device)
apk = Apk(device=device, packageName=device.foreground_package)
print(device.get_app_install_path(device.foreground_package))
print(apk.xml_test())
# print(device.shell('/data/local/tmp/aapt2 dump xmltree /data/app/tv.danmaku.bili-1/base.apk --file r/81.xml'))
