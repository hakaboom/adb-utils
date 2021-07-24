import re

from adbutils.constant import ADB_INSTALL_FAILED
import baseImage.exceptions
import cv2
from baseImage import Rect, IMAGE

import adbutils
import subprocess
# #
adb = adbutils.ADBDevice(device_id='emulator-5554')
print(adb.running_activities())
