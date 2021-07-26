import re

from adbutils.constant import ADB_INSTALL_FAILED, ADB_KEYBOARD_APK_PATH
import baseImage.exceptions
import cv2
from baseImage import Rect, IMAGE, Point

import adbutils
import subprocess
adb = adbutils.ADBDevice(device_id='emulator-5554')
print(adb.is_locked())
