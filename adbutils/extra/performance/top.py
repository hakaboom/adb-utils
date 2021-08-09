# -*- coding: utf-8 -*-
import re
import time

from adbutils import ADBDevice
from adbutils.constant import ANDROID_TMP_PATH, BUSYBOX_LOCAL_PATH, BUSYBOX_REMOTE_PATH

from typing import Union, Tuple


class Top(object):
    def __init__(self, device: ADBDevice):
        self.device = device
        self._install_busyBox()

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
