# -*- coding: utf-8 -*-
import re
import time

from adbutils import ADBDevice
from adbutils.constant import ANDROID_TMP_PATH, BUSYBOX_LOCAL_PATH, BUSYBOX_REMOTE_PATH

from typing import Union, Tuple


class Top(object):
    cpu_jiffies_pattern = re.compile(r'(\d+)')

    def __init__(self, device: ADBDevice):
        self.device = device
        self._total_cpu_stat = []
        self._core_stat = []
        # self._install_busyBox()

    def _install_busyBox(self):
        """
        check if busyBox installed

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
        return self.device.shell(['cat', '/proc/stat'])

    def _pares_cpu_stat(self, cpu_stat: str):
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
