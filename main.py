"""
python setup.py sdist
twine upload dist/*
"""
import re
from loguru import logger

from adbutils import ADBDevice
from adbutils.extra.performance.top import Top

device = ADBDevice(device_id='emulator-5554')
top_watcher = Top(device)

cmd = ['ps']
ret = device.shell(cmd)
if ret:
    ret = ret.splitlines()
else:
    exit()
ps_head = ['user', 'pid', 'ppid', 'vsize', 'rss', '', 'wchan', 'pc', 'name']

process = []
process_pattern = re.compile('(\S+)')
for i in ret[1:]:
    if p := process_pattern.findall(i):
        print(p)









# print(device.shell(['cat', '/proc/stat']))
# while True:
#     cpu_stat = top_watcher.get_cpu_stat()
#     if core_usage := top_watcher.core_cpu_usage(cpu_stat):
#         print('\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)]))
#
#     if cpu_usage := top_watcher.total_cpu_usage(cpu_stat):
#         print(f'{cpu_usage:.1f}%')
#
#     device.tap((200, 200))
