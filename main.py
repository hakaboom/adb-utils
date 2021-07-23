import re

import cv2
from baseImage import Rect, IMAGE

import adbutils
import subprocess

adb = adbutils.ADBDevice(device_id='192.168.50.109:5555')
# adb.screenshot()
print(adb.cmd('asda'))