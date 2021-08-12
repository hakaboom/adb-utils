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
for i in range(1000000):
    if app_usage := top_watcher.get_app_usage(package_name):
        print(f'{app_usage:.2f}%')

    time.sleep(.5)
# for i in range(1000):
#     if usage := top_watcher.get_cpu_usage():
#         cpu_usage, core_usage = usage
#         print('cpu={} core={}'.format(
#             f'{cpu_usage:.1f}%',
#             '\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)])
#         ))
#     #
#     # if isinstance(app_usage := top_watcher.app_cpu_usage(package_name), (int, float)):
#     #     logger.debug(f'{app_usage:.2f}%')
#     #     pass
# #     # time.sleep(1)