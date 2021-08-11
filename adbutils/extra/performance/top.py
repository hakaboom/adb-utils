# -*- coding: utf-8 -*-
import re
import time

from adbutils import ADBDevice
from adbutils.constant import ANDROID_TMP_PATH, BUSYBOX_LOCAL_PATH, BUSYBOX_REMOTE_PATH

from typing import Union, Tuple, List


class Top(object):
    # user/nice/system/idle/iowait/irq/softirq/stealstolen/guest
    cpu_jiffies_pattern = re.compile(r'(\d+)')

    def __init__(self, device: ADBDevice):
        self.device = device
        self._total_cpu_stat = []
        self._core_cpu_stat = []

    def total_cpu_usage(self, _cpu_stat: str = None) -> Union[float]:
        """
        获取总cpu使用率

        Args:
            _cpu_stat: cpu数据

        Returns:
            总cpu使用率
        """
        cpu_stat = _cpu_stat or self.get_cpu_stat()
        total_cpu_stat, cpu_core_stat = self._pares_cpu_stat(cpu_stat)
        if not self._total_cpu_stat:
            self._total_cpu_stat = total_cpu_stat
            # self._core_cpu_stat = cpu_core_stat
            return self.total_cpu_usage()

        idle = total_cpu_stat[3] - self._total_cpu_stat[3]
        total_cpu_time = sum(total_cpu_stat) - sum(self._total_cpu_stat)
        cpu_usage = 100 * (total_cpu_time - idle) / total_cpu_time

        self._total_cpu_stat = total_cpu_stat
        # self._core_cpu_stat = cpu_core_stat
        return cpu_usage

    def core_cpu_usage(self, _cpu_stat: str = None) -> List[float]:
        """
        获取每个核心的使用率

        Args:
            _cpu_stat: cpu信息

        Returns:
            每个核心的使用率
        """
        cpu_stat = _cpu_stat or self.get_cpu_stat()
        total_cpu_stat, cpu_core_stat = self._pares_cpu_stat(cpu_stat)
        if not self._core_cpu_stat:
            # self._total_cpu_stat = total_cpu_stat
            self._core_cpu_stat = cpu_core_stat
            return self.core_cpu_usage()

        core_usage = []
        for cpu_index, core_stat in enumerate(cpu_core_stat):
            idle = core_stat[3] - self._core_cpu_stat[cpu_index][3]
            total_cpu_time = sum(core_stat) - sum(self._core_cpu_stat[cpu_index])
            core_usage.append(100 * (total_cpu_time - idle) / total_cpu_time)

        # self._total_cpu_stat = total_cpu_stat
        self._core_cpu_stat = cpu_core_stat
        return core_usage

    def _install_busyBox(self):
        """
        check if busybox installed

        Returns:
            None
        """
        if not self.device.check_file(ANDROID_TMP_PATH, 'busybox'):
            if 'v8' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v8l')
            elif 'v7r' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v7r')
            elif 'v7m' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v7m')
            elif 'v7l' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v7l')
            elif 'v5' in self.device.abi_version:
                local = BUSYBOX_LOCAL_PATH.format('v5l')
            else:
                local = BUSYBOX_LOCAL_PATH.format('v8l')

            self.device.push(local=local, remote=BUSYBOX_REMOTE_PATH)
            time.sleep(1)
            self.device.shell(['chmod', '755', BUSYBOX_REMOTE_PATH])

    def get_cpu_stat(self):
        """
        command 'adb shell cat /proc/stat

        Returns:

        """
        if ret := self.device.shell(['cat', '/proc/stat']):
            return ret
        return self.get_cpu_stat()

    def _pares_cpu_stat(self, cpu_stat: str) -> Tuple[List[int], List[List[int]]]:
        """
        处理cpu信息数据

        Args:
            cpu_stat: cpu数据

        Returns:
            总cpu数据和每个核心的数据
        """
        total_cpu_pattern = re.compile(r'cpu\s*(.*)')
        core_stat_pattern = re.compile(r'cpu(\d+)\s*(.*)')

        total_cpu_stat = None
        cpu_core_stat = []

        if total_stat := total_cpu_pattern.findall(cpu_stat):
            total_stat = self.cpu_jiffies_pattern.findall(total_stat[0])
            if isinstance(total_stat, list):
                total_cpu_stat = [int(v) for v in total_stat]

        if core_stat_list := core_stat_pattern.findall(cpu_stat):
            for core_stat in core_stat_list:
                _core_stat = self.cpu_jiffies_pattern.findall(core_stat[1].strip())
                if isinstance(_core_stat, list):
                    cpu_core_stat.append([int(v) for v in _core_stat])

        return total_cpu_stat, cpu_core_stat


if __name__ == '__main__':
    from adbutils import ADBDevice
    from adbutils.extra.performance.top import Top

    device_id = ''
    device = ADBDevice(device_id=device_id)
    top_watcher = Top(device)

    while True:
        cpu_stat = top_watcher.get_cpu_stat()
        if core_usage := top_watcher.core_cpu_usage():
            print('\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)]))

        if cpu_usage := top_watcher.total_cpu_usage():
            print(f'{cpu_usage:.1f}%')
        time.sleep(.5)
