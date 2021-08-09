# -*- coding: utf-8 -*-
import re
from typing import Match, Optional, Union, Dict, Tuple, List

from adbutils import ADBDevice
from .exceptions import AdbProcessNotFound


class Meminfo(object):
    def __init__(self, device: ADBDevice):
        """
        获取设备性能数据

        Args:
            device: adb设备类
        """
        self.device = device

    def get_pss_by_process(self, meminfo: Optional[str] = None) -> List[Tuple[int, str, int]]:
        """
        获取系统所有进程的pss内存大小,单位(KB)\n
        返回列表,每个参数都是tuple(memory,package_name,pid)

        Returns:
            所有进程的pss内存
        """
        meminfo = meminfo or self.get_system_meminfo()
        if m := self._parse_system_meminfo(meminfo):
            ret = []
            pss_by_process = m.group('pss_by_process').strip()
            pss_by_process = pss_by_process.splitlines()
            pattern = re.compile(r'(?P<memory>\S+K): (?P<name>\S+)\s*\(pid (?P<pid>\d+)')
            for process in pss_by_process:
                m = pattern.search(process.strip())
                memory, name, pid = self._pares_memory(m.group('memory')), m.group('name'), int(m.group('pid'))
                ret.append((memory, name, pid))
            return ret

    def get_total_ram(self, meminfo: Optional[str] = None) -> int:
        """
        获取全部内存(total_ram)大小,单位(KB)

        Args:
            meminfo: 内存信息

        Returns:
            内存大小(KB)
        """
        meminfo = meminfo or self.get_system_meminfo()
        if m := self._parse_system_meminfo(meminfo):
            return self._pares_memory(m.group('total_ram'))

    def get_free_ram(self, meminfo: Optional[str] = None) -> int:
        """
        获取Free RAM大小,单位(KB)

        Args:
            meminfo: 内存信息

        Returns:
            Free RAM(KB)
        """
        meminfo = meminfo or self.get_system_meminfo()
        if m := self._parse_system_meminfo(meminfo):
            return self._pares_memory(m.group('free_ram'))

    def get_used_ram(self, meminfo: Optional[str] = None) -> int:
        """
        获取Used RAM大小,单位(KB)

        Args:
            meminfo: 内存信息

        Returns:
            Used RAM(KB)
        """
        meminfo = meminfo or self.get_system_meminfo()
        if m := self._parse_system_meminfo(meminfo):
            return self._pares_memory(m.group('used_ram'))

    def get_lost_ram(self, meminfo: Optional[str] = None) -> int:
        """
        获取Lost RAM大小,单位(KB)

        Args:
            meminfo: 内存信息

        Returns:
            Lost RAM(KB)
        """
        meminfo = meminfo or self.get_system_meminfo()
        if m := self._parse_system_meminfo(meminfo):
            return self._pares_memory(m.group('lost_ram'))

    def get_app_meminfo(self, package: Union[str, int]) -> Dict[str, Dict[str, int]]:
        """
         获取指定包或进程号的内存信息
         键为内存条目名称
         值是一个包含pss_total/private_dirty/private_clean/swapPss_dirty/heap_size/heap_alloc/heap_free的字典,对应的内存占用(KB)

        Args:
            package: 包名或pid进程号

        Returns:
            以字典返回所有内存信息
        """
        ret = {}
        _memory_info_count = 7
        param_list = ('pss_total', 'private_dirty', 'private_clean', 'swapPss_dirty',
                      'heap_size', 'heap_alloc', 'heap_free')
        if meminfo := self._get_app_meminfo(package):
            meminfo = self._parse_app_meminfo(meminfo)
            meminfo = meminfo.group('meminfo')
            pattern = re.compile(r'\s*(\S+\s?\S*)\s*(.*)\r?')
            for line in pattern.findall(meminfo):
                _meminfo = line[1]
                mem_pattern = re.compile(r'(\d+)\s*')
                mem = mem_pattern.findall(_meminfo)
                mem += [0 for _ in range(_memory_info_count - len(mem))]

                name = line[0].strip().lower().replace(' ', '_')
                ret[name] = {param_list[index]: v for index, v in enumerate([int(v) for v in mem])}
        return ret

    def get_app_summary(self, package: Union[str, int]) -> Dict[str, int]:
        """
        获取app summary pss。
        返回一个包含java_heap/native_heap/code/stack/graphics/private_other/system/total/total_swap_pss的字典

        Args:
            package: 包名或pid进程号

        Returns:
            app内存信息概要
        """
        ret = {}
        if meminfo := self._get_app_meminfo(package):
            meminfo = self._parse_app_meminfo(meminfo)
            meminfo = meminfo.group('app_summary').strip()
            pattern = re.compile(r'\s*(\S+\s?\S*\s?\S*):\s*(\d+)')
            for v in pattern.findall(meminfo):
                name = v[0].strip().lower().replace(' ', '_')
                memory = int(v[1])
                ret[name] = memory
            return ret

    @staticmethod
    def _pares_memory(memory: str):
        """
        处理字符串memory,转换为int,单位KB

        Args:
            memory(str): 内存

        Returns:
            内存大小,单位(KB)
        """
        memory = int(memory.strip().replace(',', '').replace('K', ''))
        return memory

    @staticmethod
    def _parse_system_meminfo(meminfo: str) -> Optional[Match[str]]:
        """
        处理adb shell dumpsys meminfo返回的数据

        Args:
            meminfo: 内存数据

        Returns:
            包含uptime、realtime、pss_by_process、pss_by_ommAdjustemnt、pss_by_category、
            total_ram、free_ram、used_ram、lost_ram
        """
        pattern = re.compile(r'Uptime: (?P<uptime>\d+) Realtime: (?P<realtime>\d+)'
                             r'.*Total PSS by process:(?P<pss_by_process>.*)'
                             r'.*Total PSS by OOM adjustment:(?P<pss_by_ommAdjustemnt>.*)'
                             r'.*Total PSS by category:(?P<pss_by_category>.*)'
                             r'.*Total RAM:\s*(?P<total_ram>\S+)'
                             r'.*Free RAM:\s*(?P<free_ram>\S+)'
                             r'.*Used RAM:\s*(?P<used_ram>\S+)'
                             r'.*Lost RAM:\s*(?P<lost_ram>\S+)', re.DOTALL)
        return m if (m := pattern.search(meminfo)) else None

    @staticmethod
    def _parse_app_meminfo(meminfo: str):
        pattern = re.compile(r'Uptime: (?P<uptime>\d+) Realtime: (?P<realtime>\d+)'
                             r'.*\*\* MEMINFO in pid (?P<pid>\d+) \[(?P<package_name>\S+)] \*\*'
                             r'.*Pss\s*Private\s*Private\s*SwapPss\s*Heap\s*Heap\s*Heap'
                             r'.*Total\s*Dirty\s*Clean\s*Dirty\s*Size\s*Alloc\s*Free'
                             r'.*------\s*------\s*------\s*------\s*------\s*------\s*------'
                             r'(?P<meminfo>.*)'
                             r'.*App Summary\s*(?P<app_summary>.*)'
                             r'.*Objects(.*)', re.DOTALL)
        return m if (m := pattern.search(meminfo)) else None

    def _get_app_meminfo(self, package: Union[str, int]):
        """
        'adb shell dumpsys meminfo <packageName|pid>' 获取指定包或进程号的内存信息

        Raises:
            AdbProcessNotFound: 未找到对应进程时弹出异常
        Args:
            package: 包名或pid进程号

        Returns:
            内存信息
        """
        if 'No process found for:' in (ret := self.device.shell(['dumpsys', 'meminfo', str(package)])):
            raise AdbProcessNotFound(ret)
        else:
            return ret

    def get_system_meminfo(self) -> str:
        """
        'adb shell dumpsys meminfo' 获取系统内存信息

        Returns:
            内存信息
        """
        return self.device.shell(['dumpsys', 'meminfo'])


if __name__ == '__main__':
    from adbutils import ADBDevice
    from adbutils.extra.performance.meminfo import Meminfo

    device_id = ''
    device = ADBDevice(device_id=device_id)
    performance = Meminfo(device)

    performance.get_system_meminfo()

    for i in range(100):
        package_name = device.foreground_package
        total = performance.get_app_summary(package_name)['total']
        # 打印package_name对应app的内存占用
        print(f'{(int(total) / 1024):.0f}MB')
