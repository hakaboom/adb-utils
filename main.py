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
print(package_name)
while True:
    cpu_stat = top_watcher.get_cpu_stat()
    app_stat = top_watcher.get_app_cpu_stat(package_name)
    # if core_usage := top_watcher.core_cpu_usage(cpu_stat):
    #     print('\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)]))
    #
    if cpu_usage := top_watcher.total_cpu_usage(cpu_stat):
        print(f'{cpu_usage:.1f}%')

    if app_usage := top_watcher.app_cpu_usage(package_name, cpu_stat, app_stat):
        print(f'{app_usage:.1f}%')
    time.sleep(1)
    # device.tap((200, 200))
