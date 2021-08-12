"""
python setup.py sdist
twine upload dist/*
"""
import re
import time

from loguru import logger

from adbutils import ADBDevice
from adbutils.extra.performance.top import Top

device = ADBDevice(device_id='emulator-5554')
top_watcher = Top(device)

#
package_name = device.foreground_package

# while True:
#     # if core_usage := top_watcher.core_cpu_usage(cpu_stat):
#     #     print('\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)]))
#     #
#     if usage := top_watcher.cpu_usage():
#         cpu_usage, core_usage = usage[0], usage[1]
#         print(f'{cpu_usage:.1f}%')
#         print('\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)]))
#
#     # if app_usage := top_watcher.app_cpu_usage(package_name):
#     #     print(f'{app_usage:.1f}%')
#     time.sleep(1)
#     # device.tap((200, 200))
print(device.shell(['ls', '/data/local/tm']))