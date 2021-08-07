"""
python setup.py sdist
twine upload dist/*
"""
import re
import time
from loguru import logger

from adbutils import ADBExtraDevice
from adbutils.extra.performance import Performance

device = ADBExtraDevice(device_id='emulator-5554', aapt=True)
performance = Performance(device)
package_name = 'jp.co.cygames.umamusume'


# sys_memory = performance.get_system_meminfo()
# ret = performance.get_pss_by_process(sys_memory)
# total_memory = performance.get_total_ram(sys_memory)
# lost_memory = performance.get_lost_ram(sys_memory)
# using_memory = 0
# for i in ret:
#     using_memory += i[0]
#
# print(total_memory - using_memory, using_memory)
# print(f'{((total_memory - using_memory - lost_memory) / 1024):.0f}MB')
total = performance.get_app_meminfo(package_name)['total'][0]
print(f'{(total / 1024):.0f}MB')