import adbutils
from adbutils._utils import split_cmd


adb = adbutils.ADBClient('asss')
adb.get_status()