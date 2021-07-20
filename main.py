import adbutils
from adbutils._utils import split_cmd
import re

adb = adbutils.ADBClient(device_id='emulator-5554')
print(adb.get_available_forward_local())
