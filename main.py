"""
python setup.py sdist
twine upload dist/*
"""
import re
import time
from loguru import logger
from baseImage import IMAGE

from adbutils import ADBExtraDevice
from adbutils.extra.performance.top import Top
from adbutils.extra.performance.meminfo import Meminfo

device = ADBExtraDevice(device_id='emulator-5554')
top = Top(device)
# user/nice/system/idle/iowait/irq/softirq/stealstolen/guest
cpu_jiffies_pattern = re.compile(r'(\d+)')
pattern = re.compile(r'cpu\s*(.*)')


while True:
    s1 = top.get_cpu_stat()
    total_cpu_stat_1 = [int(v) for v in cpu_jiffies_pattern.findall(pattern.findall(s1)[0])]
    idle_1 = total_cpu_stat_1[3]

    time.sleep(.5)

    s2 = top.get_cpu_stat()
    total_cpu_stat_2 = [int(v) for v in cpu_jiffies_pattern.findall(pattern.findall(s2)[0])]
    idle_2 = total_cpu_stat_2[3]

    idle = idle_2 - idle_1
    totalCpuTime = sum(total_cpu_stat_2) - sum(total_cpu_stat_1)
    pcpu = 100 * (totalCpuTime-idle)/totalCpuTime
    print(f'{pcpu:.1f}%')
