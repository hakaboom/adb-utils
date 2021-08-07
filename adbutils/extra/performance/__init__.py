# -*- coding: utf-8 -*-
import re
from typing import Match, Optional, Union, Dict, Tuple, List


class Performance(object):
    def __init__(self, device):
        """
        获取设备性能数据

        Args:
            device: adb设备类
        """
        self.device = device

    def get_pss_by_process(self, meminfo: Optional[str] = None) -> List[Tuple[int, str, int]]:
        """
        获取系统所有进程的pss内存大小,单位(KB)

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

    def get_app_meminfo(self, package: Union[str, int]) -> Dict[str, Tuple[int, int, int, int, int, int, int]]:
        """
         获取指定包或进程号的内存信息

        Args:
            package: 包名或pid进程号

        Returns:
            详细的内存信息
        """
        ret = {}
        if meminfo := self._get_app_meminfo(package):
            meminfo = self._parse_app_meminfo(meminfo)
            meminfo = meminfo.group('meminfo').strip()
            meminfo = meminfo.split('\n')
            # name, pss_total, private_dirty, private_clean, swapPss_dirty, heap_size, heap_alloc, heep_free
            _memory_info_count = 8
            for v in meminfo:
                mem_pattern = re.compile(r'(\S+\s?\S*)\s+')
                mem = mem_pattern.findall(v)
                if len(mem) < _memory_info_count:
                    mem += [0 for i in range(_memory_info_count - len(mem))]

                name = mem[0] or ''
                name = name.strip().lower()
                ret[name] = tuple([int(v) for v in mem[1:]])

        # TODO: 只返回需要的参数
        # total = ret['total']
        # print(f'{(total[0] / 1024):.0f}MB')
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

        Args:
            package: 包名或pid进程号

        Returns:
            内存信息
        """
        return self.device.shell(['dumpsys', 'meminfo', str(package)])

    def get_system_meminfo(self) -> str:
        """
        'adb shell dumpsys meminfo' 获取系统内存信息

        Returns:
            内存信息
        """
        return self.device.shell(['dumpsys', 'meminfo'])