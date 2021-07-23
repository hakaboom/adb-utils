import re
from baseImage import Rect

import adbutils
from adbutils._utils import split_cmd, get_std_encoding, NonBlockingStreamReader
import subprocess
adb = adbutils.ADBDevice(device_id='emulator-5554')
# adb.forward(local='tcp:4555', remote='tcp:133')
adb.screenshot()