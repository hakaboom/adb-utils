# -*- coding: utf-8 -*-
import re
import time
from typing import Union, Tuple, List

from adbutils import ADBDevice
from adbutils.constant import ANDROID_TMP_PATH, BUSYBOX_LOCAL_PATH, BUSYBOX_REMOTE_PATH
from adbutils.exceptions import AdbShellError

from loguru import logger


# TODO: _total_cpu_stat, _core_cpu_stat, _app_cpu_stat的保存需要重写


class Top(object):
    # user/nice/system/idle/iowait/irq/softirq/stealstolen/guest
    cpu_jiffies_pattern = re.compile(r'(\d+)')
    total_cpu_pattern = re.compile(r'cpu\s+(.*)')
    core_stat_pattern = re.compile(r'cpu(\d+)\s*(.*)')
    app_stat_pattern = re.compile(r'(\d+\s*\(\S+\)(\s+\S+){50})+')

    def __init__(self, device: ADBDevice):
        self.device = device
        self._total_cpu_stat = []
        self._core_cpu_stat = []
        self._app_cpu_stat = {}

    def get_cpu_usage(self):
        # step1: 记录cpu数据
        cpu_stat = self.get_cpu_stat()
        try:
            total_cpu_stat, cpu_core_stat = self._pares_cpu_stat(cpu_stat)
        except ValueError:
            return self.get_cpu_usage()

        if not self._total_cpu_stat or not self._core_cpu_stat:
            if not self._total_cpu_stat:
                self._total_cpu_stat = total_cpu_stat
            if not self._core_cpu_stat:
                self._core_cpu_stat = cpu_core_stat
            return self.get_cpu_usage()

        # step2: 计算总使用率
        total_idle = total_cpu_stat[3] - self._total_cpu_stat[3]
        total_cpu_time = sum(total_cpu_stat) - sum(self._total_cpu_stat)
        total_cpu_usage = 100 * (total_cpu_time - total_idle) / total_cpu_time
        # step3: 计算各核心使用率
        cpu_core_usage = []
        for cpu_index, core_stat in enumerate(cpu_core_stat):
            idle = core_stat[3] - self._core_cpu_stat[cpu_index][3]
            total_cpu_time = sum(core_stat) - sum(self._core_cpu_stat[cpu_index])
            cpu_core_usage.append(100 * (total_cpu_time - idle) / total_cpu_time)

        # step4: 记录保留数据
        self._total_cpu_stat = total_cpu_stat
        self._core_cpu_stat = cpu_core_stat

        return total_cpu_usage, cpu_core_usage

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

    def get_cpu_stat(self) -> str:
        """
        command 'adb shell cat /proc/stat' 获取cpu的活动信息

        Returns:
            cpu活动信息
        """
        if ret := self.device.shell(['cat', '/proc/stat']):
            return ret
        return self.get_cpu_stat()

    def _pares_cpu_stat(self, stat: str) -> Tuple[List[int], List[List[int]]]:
        """
        处理cpu信息数据

        Args:
            stat: cpu数据

        Returns:
            总cpu数据和每个核心的数据
        """
        total_cpu_stat = None
        cpu_core_stat = []

        if total_stat := self.total_cpu_pattern.findall(stat):
            total_stat = self.cpu_jiffies_pattern.findall(total_stat[0])
            total_cpu_stat = [int(v) for v in total_stat]

        if core_stat_list := self.core_stat_pattern.findall(stat):
            for core_stat in core_stat_list:
                _core_stat = self.cpu_jiffies_pattern.findall(core_stat[1].strip())
                cpu_core_stat.append([int(v) for v in _core_stat])

        if not total_cpu_stat or not cpu_core_stat:
            raise ValueError('未获取到cpu信息,需要重新运行cat')  # TODO: 增加对应报错

        return total_cpu_stat, cpu_core_stat

    def get_app_cpu_stat(self, packageName: str):
        pid = self.device.get_pid_by_name(packageName)
        if not pid:
            raise ValueError()  # TODO: 增加对应报错

        try:
            ret = self.device.shell(f'cat /proc/stat&cat /proc/{pid[0][0]}/stat')
        except AdbShellError as err:
            if 'No such file or directory' in str(err):
                raise ValueError(err)  # TODO: 增加对应报错
            raise err

        return ret if ret else self.get_app_cpu_stat(packageName)

    def _pares_app_cpu_stat(self, stat: str):
        """
        处理进程的信息数据

        Args:
            stat: app信息数据

        Returns:

        """
        """
            1557 (system_server) S 823 823 0 0 -1 1077952832 //1~9
            2085481 15248 2003 27 166114 129684 26 30  //10~17
            10 -10 221 0 2284 2790821888 93087 18446744073709551615 //18~25
            1 1 0 0 0 0 6660 0 36088 0 0 0 17 3 0 0 0 0 0 0 0 0 0 0 0 0 0
        [1~9]  
            (1)pid： 进程ID.
            (2)comm: task_struct结构体的进程名
            (3)state: 进程状态, 此处为S
            (4)ppid: 父进程ID （父进程是指通过fork方式，通过clone并非父进程）
            (5)pgrp：进程组ID
            (6)session：进程会话组ID
            (7)tty_nr：当前进程的tty终点设备号
            (8)tpgid：控制进程终端的前台进程号
            (9)flags：进程标识位，定义在include/linux/sched.h中的PF_*, 此处等于1077952832
        [10~17]   
            (10)minflt： 次要缺页中断的次数，即无需从磁盘加载内存页. 比如COW和匿名页
            (11)cminflt：当前进程等待子进程的minflt
            (12)majflt：主要缺页中断的次数，需要从磁盘加载内存页. 比如map文件
            (13)majflt：当前进程等待子进程的majflt
            (14)utime: 该进程处于用户态的时间，单位jiffies，此处等于166114
            (15)stime: 该进程处于内核态的时间，单位jiffies，此处等于129684
            (16)cutime：当前进程等待子进程的utime
            (17)cstime: 当前进程等待子进程的utime
        [18~25]
            (28)priority: 进程优先级, 此次等于10.
            (19)nice: nice值，取值范围[19, -20]，此处等于-10
            (20)num_threads: 线程个数, 此处等于221
            (21)itrealvalue: 该字段已废弃，恒等于0
            (22)starttime：自系统启动后的进程创建时间，单位jiffies，此处等于2284
            (23)vsize：进程的虚拟内存大小，单位为bytes
            (24)rss: 进程独占内存+共享库，单位pages，此处等于93087
            (25)rsslim: rss大小上限
        [25~]
            (32)signal：即将要处理的信号，十进制，此处等于6660
            (33)blocked：阻塞的信号，十进制
            (34)sigignore：被忽略的信号，十进制，此处等于36088
        """
        app_cpu_stat = None
        ret = self.app_stat_pattern.findall(stat)

        if ret:
            app_cpu_stat = ret[0][0]

        cpu_stat = stat.replace(app_cpu_stat, '')
        if not cpu_stat:
            raise ValueError('未获取到cpu信息,需要重新运行cat')  # TODO: 增加对应报错

        total_cpu_stat, cpu_core_stat = self._pares_cpu_stat(cpu_stat)

        pattern = re.compile(r'(\S+)\s*')
        if app_stat := pattern.findall(app_cpu_stat):
            return app_stat, total_cpu_stat, cpu_core_stat

    def get_app_usage(self, packageName: str):
        app_stat = self.get_app_cpu_stat(packageName)
        try:
            app_stat, total_cpu_stat, core_cpu_stat = self._pares_app_cpu_stat(app_stat)
        except ValueError:
            return self.get_app_usage(packageName)

        if not self._total_cpu_stat or not self._core_cpu_stat or not self._app_cpu_stat.get(packageName):
            if not self._total_cpu_stat:
                self._total_cpu_stat = total_cpu_stat
            if not self._core_cpu_stat:
                self._core_cpu_stat = core_cpu_stat
            if not self._app_cpu_stat.get(packageName):
                self._app_cpu_stat[packageName] = app_stat
            return self.get_app_usage(packageName)

        total_cpu_time = sum(total_cpu_stat) - sum(self._total_cpu_stat)
        app_cpu_time = sum([int(v) for v in app_stat[13:17]]) - sum([int(v)
                                                                     for v in self._app_cpu_stat[packageName][13:17]])

        app_usage = 100 * (app_cpu_time / total_cpu_time)

        self._total_cpu_stat = total_cpu_stat
        self._core_cpu_stat = core_cpu_stat
        self._app_cpu_stat[packageName] = app_stat

        return app_usage


if __name__ == '__main__':
    from adbutils import ADBDevice
    from adbutils.extra.performance.top import Top

    device_id = ''
    device = ADBDevice(device_id=device_id)
    top_watcher = Top(device)

    while True:
        if usage := top_watcher.get_cpu_usage():
            cpu_usage, core_usage = usage[0], usage[1]
            print(f'{cpu_usage:.1f}%'
                  '\t'.join([f'cpu{core_index} {usage:.1f}%' for core_index, usage in enumerate(core_usage)]))

        time.sleep(.5)
