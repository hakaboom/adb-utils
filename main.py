"""
python setup.py sdist
twine upload dist/*
"""
import re
import sys
import time

from loguru import logger

from adbutils import ADBDevice
from adbutils.extra.performance.fps import Fps
from adbutils.extra.performance.meminfo import Meminfo
from adbutils.extra.performance.cpu import Cpu

device = ADBDevice(device_id='emulator-5554')
mem_watcher = Meminfo(device)
fps_watcher = Fps(device)
cpu_watcher = Cpu(device)
fps_ret = []

package_name = device.foreground_package
package_activity = device.foreground_activity
while True:
    fps, fTime, jank, bigJank, _ = fps_watcher.get_fps_surfaceView(f"'SurfaceView - {package_name}/{package_activity}'")
    total_cpu_usage, cpu_core_usage, app_usage_ret = cpu_watcher.get_cpu_usage(package_name)
    s = 'cpu={} core={}, {} PSS={:.1f}MB'.format(
        f'{total_cpu_usage:.1f}%',
        '\t'.join([f'cpu{core_index}:{usage:.1f}%' for core_index, usage in enumerate(cpu_core_usage)]),
        '\t'.join([f'{name}:{usage:.1f}%' for name, usage in app_usage_ret.items()]),
        int(mem_watcher.get_app_summary(package_name)['total']) / 1024
    )
    logger.debug(f'当前帧数:{fps:.2f}帧\t'
                 f'最大渲染耗时:{fTime:.2f}ms\t'
                 f'Jank:{jank}\t'
                 f'BigJank:{bigJank}\n'
                 f'{s}')

    time.sleep(1)
