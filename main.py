import adbutils
from adbutils._utils import split_cmd, get_std_encoding, NonBlockingStreamReader
import subprocess
adb = adbutils.ADBShell(device_id='emulator-5554')
print(adb.sdk_version)
print(adb.abi_version)