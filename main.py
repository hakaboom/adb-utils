import adbutils
from adbutils._utils import split_cmd
import re

adb = adbutils.ADBClient(device_id='emulator-5554')
adb.install(local='C:\\Users\\Administrator.hzq\\Downloads\\com.tencent.qnet.2.3.1_rel.apk',
            install_options=['-r'])
