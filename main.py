import re

from adbutils.constant import ADB_INSTALL_FAILED, ADB_KEYBOARD_APK_PATH
import baseImage.exceptions
import cv2
from baseImage import Rect, IMAGE, Point

import adbutils
import subprocess
adb = adbutils.ADBDevice(device_id='emulator-5554')
# adb.install(local=ADB_KEYBOARD_APK_PATH)
# adb.shell('ime enable com.android.adbkeyboard/.AdbIME')
# adb.shell('ime set com.android.adbkeyboard/.AdbIME')
# adb.shell(f"am broadcast -a ADB_INPUT_TEXT --es msg '哈哈'")
print(adb._get_default_input_method())