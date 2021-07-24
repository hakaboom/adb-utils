import re

import baseImage.exceptions
import cv2
from baseImage import Rect, IMAGE

import adbutils
import subprocess
#
adb = adbutils.ADBDevice(device_id='emulator-5554')
adb.install(local='arknights-hg-1540.apk')