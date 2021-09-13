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

apk._dump_icon_from_androidManifest()
s = """
 mipmap/ic_launcher
      (mdpi) "r/7-m.png"
      (hdpi) "r/7-q.png"
      (xhdpi) "r/7-u.png"
      (xxhdpi) "r/810.png"
      (xxxhdpi) "r/81b.png"
      (anydpi-v26) "r/81f.xml"
"""
pattern = re.compile(r'\((\S+)\) \"(\S+)\"')
print(pattern.findall(s))