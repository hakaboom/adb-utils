# -*- coding: utf-8 -*-
import re
import time
from typing import Union, Tuple, List, Optional, Dict

from adbutils import ADBDevice
from adbutils.constant import ANDROID_TMP_PATH, BUSYBOX_LOCAL_PATH, BUSYBOX_REMOTE_PATH
from adbutils._utils import get_std_encoding
from adbutils.extra.performance.exceptions import AdbNoInfoReturn

from loguru import logger


class Cpu(object):
    # user/nice/system/idle/iowait/irq/softirq/stealstolen/guest
    cpu_jiffies_pattern = re.compile(r'(\d+)')
    total_cpu_pattern = re.compile(r'cpu\s+(.*)')
    core_stat_pattern = re.compile(r'cpu(\d+)\s*(.*)')
    app_stat_pattern = re.compile(r'((\d+)\s*\(\S+\)(\s+\S+){50})+')

    def __init__(self, device: ADBDevice):
        self.device = device
        self._total_cpu_stat = []
        self._core_cpu_stat = []
        self._app_cpu_stat = {}

    def get_cpu_usage(self, name: Union[str, int, List[Union[int, str]], Tuple[Union[str, int], ...], None] = None):
        """
        获取设备cpu使用率

        Args:
            name: 根据name中的值查找对应pid的cpu使用率

        Returns:
            (total_cpu_usage, core_cpu_usage, app_cpu_usage)
            app_cpu_usage: 是一个以pid为索引的字典
            core_cpu_usage: 是一个列表,索引对应cpu核心
            total_cpu_usage: 一个float或int
        """
        # step1: 转换name为pid
        if isinstance(name, (str, int)):
            name = [name]
        pid_list = name and self._transform_name_to_pid(name) or []

        # step2: 运行命令,获得cpu信息
        try:
            total_cpu_stat, core_cpu_stat, app_cpu_stat = self._get_cpu_stat(pid_list)
        except AdbNoInfoReturn as err:
            logger.warning(err)
            return self.get_cpu_usage(name)

        _return_flag = 0
        if not self._total_cpu_stat or not self._core_cpu_stat:
            self._total_cpu_stat = total_cpu_stat
            self._core_cpu_stat = core_cpu_stat
            _return_flag = 1

        for _name in pid_list:
            if not self._app_cpu_stat.get(_name):
                if app_stat := app_cpu_stat.get(_name):
                    self._app_cpu_stat[_name] = app_stat
                    _return_flag = 2

        if _return_flag > 0:
            return self.get_cpu_usage(name)

        # step3: 计算总使用率
        total_idle = total_cpu_stat[3] - self._total_cpu_stat[3]
        total_cpu_time = sum(total_cpu_stat) - sum(self._total_cpu_stat)
        total_cpu_usage = 100 * (total_cpu_time - total_idle) / total_cpu_time

        # step4: 计算各核心使用率
        cpu_core_usage = []
        for cpu_index, core_stat in enumerate(core_cpu_stat):
            idle = core_stat[3] - self._core_cpu_stat[cpu_index][3]
            core_cpu_time = sum(core_stat) - sum(self._core_cpu_stat[cpu_index])
            cpu_core_usage.append(100 * (core_cpu_time - idle) / core_cpu_time)

        self._total_cpu_stat = total_cpu_stat
        self._core_cpu_stat = core_cpu_stat

        # step5: 计算各pid使用率
        app_usage_ret = {}

        for pid, app_stat in app_cpu_stat.items():
            if app_stat:
                app_cpu_time = sum([int(v) for v in app_stat[13:15]]) - \
                               sum([int(v) for v in self._app_cpu_stat[pid][13:15]])
                app_usage = 100 * (app_cpu_time / total_cpu_time)
                app_usage_ret[name[pid_list.index(pid)]] = app_usage
                self._app_cpu_stat[pid] = app_stat

        return total_cpu_usage, cpu_core_usage, app_usage_ret

    def _get_cpu_stat(self, name: Optional[List[int]] = None) -> \
            Tuple[List[int], List[List[int]], Dict[int, Optional[List[str]]]]:
        cmds = self._create_command(name)
        proc = self.device.start_shell(cmds)

        stdout, stderr = proc.communicate()

        stdout = stdout.decode(get_std_encoding(stdout))
        stderr = stderr.decode(get_std_encoding(stdout))

        app_cpu_stat = name and {pid: None for pid in name} or {}
        if ret := self.app_stat_pattern.findall(stdout):
            pattern = re.compile(r'(\S+)\s*')
            for v in ret:
                pid = int(v[1])
                app_cpu_stat[pid] = pattern.findall(v[0])
                stdout = stdout.replace(v[0], '')

        if not stdout:
            raise AdbNoInfoReturn(f'cpu信息获取异常')

        total_cpu_stat, core_cpu_stat = self._pares_cpu_stat(stdout)

        if not total_cpu_stat or not core_cpu_stat:
            return self._get_cpu_stat(name)

        return total_cpu_stat, core_cpu_stat, app_cpu_stat

    def _install_busyBox(self) -> None:
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

    def _pares_cpu_stat(self, stat: str) -> Tuple[List[int], List[List[int]]]:
        """
        处理cpu信息数据

        Args:
            stat: cpu数据

        Returns:
            总cpu数据和每个核心的数据
        """
        total_cpu_stat = None
        core_cpu_stat = []

        if total_stat := self.total_cpu_pattern.findall(stat):
            total_stat = self.cpu_jiffies_pattern.findall(total_stat[0])
            total_cpu_stat = [int(v) for v in total_stat]

        if core_stat_list := self.core_stat_pattern.findall(stat):
            for core_stat in core_stat_list:
                _core_stat = self.cpu_jiffies_pattern.findall(core_stat[1].strip())
                core_cpu_stat.append([int(v) for v in _core_stat])

        if not total_cpu_stat or not core_cpu_stat:
            raise AdbNoInfoReturn('cpu信息获取异常')

        return total_cpu_stat, core_cpu_stat

    @staticmethod
    def _create_command(name: Optional[List[int]] = None):
        """
        根据pid创建cmd命令

        Args:
            name: 包含pid的列表

        Returns:
            cmd命令
        """
        cmds = ['cat /proc/stat']
        if name:
            for pid in name:
                cmds += [f'cat /proc/{pid}/stat']

        return '&'.join(cmds)

    def _transform_name_to_pid(self, name: Union[List, Tuple]) -> Optional[List[int]]:
        """
        处理传参,将包名更改为pid

        Args:
            name: 需要处理的包名或pid

        Returns:
            只包含pid的列表
        """
        ret = []
        for _name in name:
            if isinstance(_name, str):
                if pid := self.device.get_pid_by_name(_name):
                    pid = pid[0][0]
                else:
                    logger.warning(f"应用:'{_name}'未运行")
                    pid = None
            elif isinstance(_name, int):
                pid = _name
            else:
                pid = None
            ret.append(pid)
        return ret


if __name__ == '__main__':
    from adbutils import ADBDevice
    from adbutils.extra.performance.cpu import Cpu

    device_id = ''
    device = ADBDevice(device_id=device_id)
    top_watcher = Cpu(device)

    while True:
        total_cpu_usage, cpu_core_usage, app_usage_ret = top_watcher.get_cpu_usage(device.foreground_package)
        print('cpu={} core={}, {}'.format(
            f'{total_cpu_usage:.1f}%',
            '\t'.join([f'cpu{core_index}:{usage:.1f}%' for core_index, usage in enumerate(cpu_core_usage)]),
            '\t'.join([f'{name}:{usage:.1f}%' for name, usage in app_usage_ret.items()])
        ))
        time.sleep(.5)
