import queue
import random
import subprocess
import re
import socket
import os
import threading
import time
import warnings
import numpy as np
from baseImage import Rect, Point

from adbutils._utils import (get_adb_exe, split_cmd, _popen_kwargs, get_std_encoding, check_file,
                             NonBlockingStreamReader, reg_cleanup)
from adbutils.constant import (ANDROID_ADB_SERVER_HOST, ANDROID_ADB_SERVER_PORT, ADB_CAP_RAW_REMOTE_PATH,
                               ADB_CAP_RAW_LOCAL_PATH, IP_PATTERN, ADB_DEFAULT_KEYBOARD, ANDROID_TMP_PATH,
                               ADB_KEYBOARD_APK_PATH)
from adbutils.exceptions import (AdbError, AdbShellError, AdbBaseError, AdbTimeout, NoDeviceSpecifyError,
                                 AdbDeviceConnectError, AdbInstallError, AdbSDKVersionError, AdbExtraModuleNotFount)
from adbutils._wraps import retries
from loguru import logger

from typing import Union, List, Optional, Tuple, Dict, Match, Iterator, Final, Generator, Any


class ADBClient(object):
    SUBPROCESS_FLAG: Final[int] = _popen_kwargs()['creationflags']

    def __init__(self, device_id: Optional[str] = None, adb_path: Optional[str] = None,
                 host: Optional[str] = ANDROID_ADB_SERVER_HOST,
                 port: Optional[int] = ANDROID_ADB_SERVER_PORT):
        """
        Args:
            device_id (str): 指定设备名
            adb_path (str): 指定adb路径
            host (str): 指定连接地址
            port (int): 指定连接端口
        """
        self.device_id = device_id
        self.adb_path = adb_path or get_adb_exe()
        self._set_cmd_options(host, port)
        self.connect()

    @property
    def host(self) -> str:
        return self.__host

    @property
    def port(self) -> int:
        return self.__port

    def _set_cmd_options(self, host: str, port: int):
        """
        Args:
            host (str): 指定连接地址
            port (int): 指定连接端口
        """
        self.__host = host
        self.__port = port
        self.cmd_options = [self.adb_path]
        if self.host not in ('127.0.0.1', 'localhost'):
            self.cmd_options += ['-H', self.host]
        if self.port != ANDROID_ADB_SERVER_PORT:
            self.cmd_options += ['-P', str(self.port)]

    @property
    def server_version(self) -> int:
        """
        获得cmd version

        Returns:
            adb server版本
        """
        ret = self.cmd('version', devices=False)
        pattern = re.compile(r'Android Debug Bridge version \d.\d.(\d+)')
        if version := pattern.findall(ret):
            return int(version[0])

    @property
    def devices(self) -> Dict[str, str]:
        """
        command 'adb devices'

        Returns:
            devices dict key[device_name]-value[device_state]
        """
        pattern = re.compile(r'([\S]+)\t([\w]+)\n?')
        ret = self.cmd("devices", devices=False)
        return {value[0]: value[1] for value in pattern.findall(ret)}

    def get_device_id(self, decode: bool = False) -> str:
        return decode and self.device_id.replace(':', '_') or self.device_id

    def start_server(self) -> None:
        """
        command 'adb start_server'

        Returns:
            None
        """
        self.cmd('start-server', devices=False)

    def kill_server(self) -> None:
        """
        command 'adb kill_server'

        Returns:
            None
        """
        self.cmd('kill-server', devices=False)

    @retries(2, exceptions=(AdbDeviceConnectError,))
    def connect(self, force: Optional[bool] = False) -> None:
        """
        command 'adb connect <device_id>'

        Args:
            force: 不判断设备当前状态,强制连接

        Returns:
                连接成功返回True,连接失败返回False
        """
        if self.device_id and ':' in self.device_id and (force or self.status != 'devices'):
            ret = self.cmd(f"connect {self.device_id}", devices=False, skip_error=True)
            if 'failed' in ret:
                raise AdbDeviceConnectError(f'failed to connect to {self.device_id}')

    def disconnect(self) -> None:
        """
        command 'adb -s <device_id> disconnect'

        Returns:
            None
        """
        if ':' in self.device_id:
            self.cmd(f"disconnect {self.device_id}", devices=False)

    def forward(self, local: str, remote: str, no_rebind: Optional[bool] = True) -> None:
        """
        command adb forward

        Args:
            local:  要转发的本地端口
            remote: 要与local绑定的设备端口
            no_rebind: if True,如果local端已经绑定则失败

        Returns:
            None
        """
        cmds = ['forward']
        if no_rebind:
            cmds += ['--no-rebind']
        self.cmd(cmds + [local, remote])

    def remove_forward(self, local: Optional[str] = None) -> None:
        """
        command adb forward --remove <local>

        Args:
            local: 本地端口。如果未指定local,则默认清除所有连接' adb forward --remove-all'

        Returns:
            None
        """
        if local:
            cmds = ['forward', '--remove', local]
        else:
            cmds = ['forward', '--remove-all']
        self.cmd(cmds)

    def get_forwards(self, device_id: Optional[str] = None) -> Dict[str, List[Tuple[str, str]]]:
        """
        command 'adb forward --list'

        Args:
            device_id (str): 获取指定设备下的端口
        Returns:
            forwards dict key[device_name]-value[Tuple[local, remote]]
        """
        forwards = {}
        pattern = re.compile(r'([\S]+)\s([\S]+)\s([\S]+)\n?')
        ret = self.cmd(['forward', '--list'], devices=False, skip_error=True)
        for value in pattern.findall(ret):
            if device_id and device_id != value[0]:
                continue
            if value[0] in forwards:
                forwards[value[0]] += [(value[1], value[2])]
            else:
                forwards[value[0]] = [(value[1], value[2])]

        return forwards

    def get_forward_port(self, remote: str, device_id: Optional[str] = None) -> Optional[int]:
        """
        获取开放端口的端口号

        Args:
            remote (str): 设备端口
            device_id (str): 获取指定设备下的端口
        Returns:
            本地端口号
        """
        forwards = self.get_forwards(device_id=device_id)
        local_pattern = re.compile(r'tcp:(\d+)')
        for device_id, value in forwards.items():
            if isinstance(value, (list, tuple)):
                for _local, _remote in value:
                    if (_remote == remote) and (ret := local_pattern.search(_local)):
                        return int(ret.group(1))
        return None

    def get_available_forward_local(self) -> int:
        """
        随机获取一个可用的端口号

        Returns:
            可用端口(int)
        """
        sock = socket.socket()
        port = random.randint(11111, 20000)
        result = False
        try:
            sock.bind((self.host, port))
            result = True
        except socket.error:
            pass
        sock.close()
        if result:
            return port
        return self.get_available_forward_local()

    def push(self, local: str, remote: str) -> None:
        """
        command 'adb push <local> <remote>'

        Args:
            local: 发送文件的路径
            remote: 发送到设备上的路径

        Raises:
            RuntimeError:文件不存在

        Returns:
            None
        """
        if not check_file(local):
            raise RuntimeError(f"file: {local} does not exists")
        self.cmd(['push', local, remote], decode=False)

    def push_with_progress(self, local: str, remote: str) -> Generator[Union[str, bool], Any, None]:
        """
        特殊push方法, 返回一个生成器, 通过next获取push进度,push完成后返回True

        Args:
            local: 本地的路径
            remote: 设备上的路径

        Returns:
            生成器
        """
        proc = self.start_cmd(cmds=['push', local, remote])

        nbsp = NonBlockingStreamReader(proc.stdout)
        progressRE = re.compile(r'\[\s*(\d+)%]')
        while True:
            line: bytes = nbsp.readline(timeout=1)
            if line is None:
                raise AdbBaseError(proc.stderr)
            elif b'file pushed' in line:
                break
            line: str = line.decode(get_std_encoding(line))
            yield progressRE.search(line).group(1)

        yield True
        reg_cleanup(proc.kill)

    def pull(self, local: str, remote: str) -> None:
        """
        command 'adb pull <remote> <local>

        Args:
            local: 本地的路径
            remote: 设备上的路径

        Returns:
            None
        """
        self.cmd(['pull', remote, local], decode=False)

    def pull_with_progress(self, local: str, remote: str) -> Generator[Union[str, bool], Any, None]:
        """
        特殊pull方法, 返回一个生成器, 通过next获取pull进度,pull完成后返回True

        Args:
            local: 本地的路径
            remote: 设备上的路径

        Returns:
            生成器
        """
        proc = self.start_cmd(cmds=['pull', remote, local])

        nbsp = NonBlockingStreamReader(proc.stdout)
        progressRE = re.compile(r'\[\s*(\d+)%]')
        while True:
            line: bytes = nbsp.readline(timeout=1)
            if line is None:
                raise AdbBaseError(proc.stderr)
            elif b'file pulled' in line:
                break
            line: str = line.decode(get_std_encoding(line))
            yield progressRE.search(line).group(1)

        yield True
        reg_cleanup(proc.kill)

    def install(self, local: str, install_options: Union[str, list, None] = None) -> bool:
        """
        command 'adb install <local>'

        Args:
            local: apk文件路径
            install_options: 可指定参数
                    "-r",  # 重新安装现有应用，并保留其数据。
                    "-t",  # 允许安装测试 APK。
                    "-g",  # 授予应用清单中列出的所有权限。
                    "-d",  # 允许APK降级覆盖安装
                    "-l",  # 将应用安装到保护目录/mnt/asec
                    "-s",  # 将应用安装到sdcard
        Raises:
            AdbInstallError: 安装失败
            AdbError: 安装失败
        Returns:
            安装成功返回True
        """
        cmds = ['install']
        if isinstance(install_options, str):
            cmds.append(install_options)
        elif isinstance(install_options, list):
            cmds += install_options

        cmds = cmds + [local]
        proc = self.start_cmd(cmds)
        stdout, stderr = proc.communicate()

        stdout = stdout.decode(get_std_encoding(stdout))
        stderr = stderr.decode(get_std_encoding(stdout))

        pattern = re.compile(r"Failure \[(.+):.+\]")
        if proc.returncode == 0:
            return True
        elif pattern.search(stderr):
            raise AdbInstallError(pattern.findall(stderr)[0])
        else:
            raise AdbError(stdout, stderr)

    def uninstall(self, package_name: str, install_options: Optional[str] = None) -> None:
        """
        command 'adb uninstall <package>

        Args:
            package_name: 需要卸载的包名
            install_options: 可指定参数
                            "-k",  # 移除软件包后保留数据和缓存目录。

        Returns:
            None
        """
        cmds = ['uninstall']
        if install_options and isinstance(install_options, str):
            cmds.append(install_options)

        cmds = cmds + [package_name]
        self.cmd(cmds)

    @property
    def status(self) -> Optional[str]:
        """
        command adb -s <device_id> get-state,返回当前设备状态

        Returns:
            当前设备状态
        """
        proc = self.start_cmd('get-state')
        stdout, stderr = proc.communicate()

        stdout = stdout.decode(get_std_encoding(stdout))
        stderr = stderr.decode(get_std_encoding(stdout))

        if proc.returncode == 0:
            return stdout.strip()
        elif "not found" in stderr:
            return None
        elif 'device offline' in stderr:
            return 'offline'
        else:
            raise AdbError(stdout, stderr)

    def cmd(self, cmds: Union[list, str], devices: Optional[bool] = True, decode: Optional[bool] = True,
            timeout: Optional[int] = None, skip_error: Optional[bool] = False):
        """
        创建cmd命令, 并返回命令返回值

        Args:
            cmds (list,str): 需要运行的参数
            devices (bool): 如果为True,则需要指定device-id,命令中会传入-s
            decode (bool): 是否解码stdout,stderr
            timeout (int): 设置命令超时时间
            skip_error (bool): 是否跳过报错
        Raises:
            AdbDeviceConnectError: 设备连接异常
            AdbTimeout:输入命令超时
        Returns:
            返回命令结果stdout
        """

        proc = self.start_cmd(cmds, devices)
        if timeout and isinstance(timeout, int):
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                _, stderr = proc.communicate()
                raise AdbTimeout(f"cmd command {' '.join(proc.args)} time out")
        else:
            stdout, stderr = proc.communicate()

        if decode:
            stdout = stdout.decode(get_std_encoding(stdout))
            stderr = stderr.decode(get_std_encoding(stderr))

        if proc.returncode > 0:
            pattern = AdbDeviceConnectError.CONNECT_ERROR
            if isinstance(stderr, bytes):
                pattern = pattern.encode("utf-8")
            if re.search(pattern, stderr):
                raise AdbDeviceConnectError(stderr)
            if not skip_error:
                raise AdbError(stdout, stderr)

        return stdout

    def start_cmd(self, cmds: Union[list, str], devices: bool = True) -> subprocess.Popen:
        """
        根据cmds创建一个Popen

        Args:
            cmds: cmd commands
            devices: 如果为True,则需要指定device-id,命令中会传入-s
        Raises:
            NoDeviceSpecifyError:没有指定设备运行cmd命令
        Returns:
            Popen管道
        """
        cmds = split_cmd(cmds)
        if devices:
            if not self.device_id:
                raise NoDeviceSpecifyError('must set device_id')
            cmd_options = self.cmd_options + ['-s', self.device_id]
        else:
            cmd_options = self.cmd_options

        cmds = cmd_options + cmds
        logger.info(' '.join(cmds))
        proc = subprocess.Popen(
            cmds,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=self.SUBPROCESS_FLAG
        )
        return proc


class ADBShell(ADBClient):
    SHELL_ENCODING: Final[str] = 'utf-8'  # adb shell的编码
    PS_HEAD: Final[List[str]] = ['user', 'pid', 'ppid', 'vsize', 'rss', '', 'wchan', 'pc', 'name']  # adb shell ps

    @property
    def line_breaker(self) -> str:
        """
        Set carriage return and line break property for various platforms and SDK versions

        Returns:
            carriage return and line break string
        """
        if not hasattr(self, '_line_breaker'):
            if self.sdk_version >= 24:
                line_breaker = os.linesep
            else:
                line_breaker = '\r' + os.linesep
            line_breaker = line_breaker.encode("ascii")
            setattr(self, '_line_breaker', line_breaker)

        return getattr(self, '_line_breaker')

    @property
    def memory(self) -> str:
        """
        获取设备内存大小

        Returns:
            单位MB
        """
        ret = self.shell(['dumpsys', 'meminfo'])
        pattern = re.compile(r'.*Total RAM:\s+(\S+)\s+', re.DOTALL)
        if m := pattern.search(ret):
            memory = m.group(1)
        else:
            raise AdbBaseError(ret)

        if ',' in memory:
            memory = memory.split(',')
            # GB: memory[0], MB: memory[1], KB: memory[2]
            memory = int(int(memory[0]) * 1024) + int(memory[1])
        else:
            memory = round(int(memory) / 1024)
        return f'{str(memory)}MB'

    @property
    def cpu_coreNum(self) -> Optional[int]:
        """
        获取cpu核心数量

        Returns:
            cpu核心数量
        """
        if not hasattr(self, '_cpu_coreNum'):
            setattr(self, '_cpu_coreNum', int(self.shell("cat /proc/cpuinfo").strip().count('processor')))

        return getattr(self, '_cpu_coreNum')

    @property
    def cpu_max_freq(self) -> List[Optional[int]]:
        """
        获取cpu各核心的最高频率

        Raises:
            AdbBaseError: 获取cpu信息失败
        Returns:
            包含核心最高频率的列表
        """
        _cores = []
        cmds = [f"cat /sys/devices/system/cpu/cpu{i}/cpufreq/scaling_max_freq" for i in range(self.cpu_coreNum)]
        cmds = '&'.join(cmds)

        ret = self.shell(cmds)
        if not ret:
            raise AdbBaseError('get cpufreq error')

        pattern = re.compile('(\d+)')
        if ret := pattern.findall(ret):
            _cores = [int(int(core) / 1000) for core in ret]
        else:
            raise AdbBaseError('get cpufreq error')

        return _cores

    @property
    def cpu_min_freq(self) -> List[Optional[int]]:
        """
        获取cpu各核心的最低频率

        Raises:
            AdbBaseError: 获取cpu信息失败
        Returns:
            包含核心最低频率的列表
        """
        _cores = []
        cmds = [f"cat /sys/devices/system/cpu/cpu{i}/cpufreq/scaling_min_freq" for i in range(self.cpu_coreNum)]
        cmds = '&'.join(cmds)

        ret = self.shell(cmds)
        if not ret:
            raise AdbBaseError('get cpufreq error')

        pattern = re.compile('(\d+)')
        if ret := pattern.findall(ret):
            _cores = [int(int(core) / 1000) for core in ret]
        else:
            raise AdbBaseError('get cpufreq error')

        return _cores

    @property
    def cpu_cur_freq(self) -> List[Optional[int]]:
        """
        获取cpu各核心的当前频率

        Raises:
            AdbBaseError: 获取cpu信息失败
        Returns:
            包含核心当前频率的列表
        """
        _cores = []
        cmds = [f"cat /sys/devices/system/cpu/cpu{i}/cpufreq/scaling_cur_freq" for i in range(self.cpu_coreNum)]
        cmds = '&'.join(cmds)

        ret = self.shell(cmds)
        if not ret:
            raise AdbBaseError('get cpufreq error')

        pattern = re.compile('(\d+)')
        if ret := pattern.findall(ret):
            _cores = [int(int(core) / 1000) for core in ret]
        else:
            raise AdbBaseError('get cpufreq error')

        return _cores

    @property
    def cpu_abi(self) -> str:
        """
        获取cpu构架

        Returns:
            cpu构建
        """
        if not hasattr(self, '_cpu_adi'):
            setattr(self, '_cpu_adi', self.shell("getprop ro.product.cpu.abi").strip())

        return getattr(self, '_cpu_adi')

    @property
    def gpu_model(self):
        """
        获取gpu型号

        Returns:
            gpu型号
        """
        if not hasattr(self, '_gpu_model'):
            ret = self.shell('dumpsys SurfaceFlinger')
            pattern = re.compile(r'GLES:\s+(.*)')
            m = pattern.search(ret)
            if not m:
                return None
            _list = m.group(1).split(',')
            gpuModel = ''

            if len(_list) > 0:
                gpuModel = _list[1].strip()
            setattr(self, '_gpu_model', gpuModel)

        return getattr(self, '_gpu_model')

    @property
    def opengl_version(self):
        """
        获取设备opengl版本

        Returns:
            opengl版本
        """
        if not hasattr(self, '_opengl'):
            ret = self.shell('dumpsys SurfaceFlinger')
            pattern = re.compile(r'GLES:\s+(.*)')
            m = pattern.search(ret)
            if not m:
                return None
            _list = m.group(1).split(',')
            opengl = ''

            if len(_list) > 1:
                m2 = re.search(r'(\S+\s+\S+\s+\S+).*', _list[2])
                if m2:
                    opengl = m2.group(1)
            setattr(self, '_opengl', opengl)

        return getattr(self, '_opengl')

    @property
    def model(self) -> str:
        """
        获取手机型号

        Returns:
            手机型号
        """
        if not hasattr(self, '_model'):
            setattr(self, '_model', self.getprop('ro.product.model'))

        return getattr(self, '_model')

    @property
    def manufacturer(self) -> str:
        """
        获取手机厂商名

        Returns:
            手机厂商名
        """
        if not hasattr(self, '_manufacturer'):
            setattr(self, '_manufacturer', self.getprop('ro.product.manufacturer'))

        return getattr(self, '_manufacturer')

    @property
    def android_version(self) -> str:
        """
        获取系统安卓版本

        Returns:
            安卓版本
        """
        if not hasattr(self, '_android_version'):
            setattr(self, '_android_version', self.getprop('ro.build.version.release'))

        return getattr(self, '_android_version')

    @property
    def sdk_version(self) -> int:
        """
        获取sdk版本

        Returns:
            sdk版本号
        """
        if not hasattr(self, '_sdk_version'):
            setattr(self, '_sdk_version', int(self.getprop('ro.build.version.sdk')))

        return getattr(self, '_sdk_version')

    @property
    def abi_version(self) -> str:
        """
        获取abi版本

        Returns:
            abi版本
        """
        if not hasattr(self, '_abi_version'):
            setattr(self, '_abi_version', self.getprop('ro.product.cpu.abi'))

        return getattr(self, '_abi_version')

    @property
    def displayInfo(self) -> Dict[str, Union[int, float]]:
        """
        获取屏幕数据

        Returns:
            width/height/density/orientation/rotation/max_x/max_y
        """
        display_info = self.getPhysicalDisplayInfo()
        orientation = self.orientation
        max_x, max_y = self.getMaxXY()
        display_info.update({
            "orientation": orientation,
            "rotation": orientation * 90,
            "max_x": max_x,
            "max_y": max_y,
        })
        return display_info

    @property
    def dpi(self) -> int:
        if ret := self.getprop('ro.sf.lcd_density', True):
            return int(ret)

    @property
    def orientation(self) -> int:
        """
        获取屏幕方向

        Returns:
            屏幕方向 0/1/2
        """
        return self.getDisplayOrientation()

    @property
    def ip_address(self) -> Optional[str]:
        """
        获得设备ip地址

        Returns:
            未找到则返回None,找到则返回IP address
        """

        def get_ip_address_from_interface(interface):
            # android >= 6.0: ip -f inet addr show {interface}
            try:
                res = self.shell(f'ip -f inet addr show {interface}')
            except AdbShellError:
                res = ''
            if matcher := re.search(r"inet (?P<ip>(\d+\.){3}\d+)", res):
                return matcher.group('ip')

            # android >= 6.0 backup method: ifconfig
            try:
                res = self.shell('ifconfig')
            except AdbShellError:
                res = ''
            if matcher := re.search(interface + r'.*?inet addr:((\d+\.){3}\d+)', res, re.DOTALL):
                return matcher.group(1)

            # android <= 6.0: netcfg
            try:
                res = self.shell('netcfg')
            except AdbShellError:
                res = ''
            if matcher := re.search(interface + r'.* ((\d+\.){3}\d+)/\d+', res):
                return matcher.group(1)

            # android <= 6.0 backup method: getprop dhcp.{}.ipaddress
            try:
                res = self.shell('getprop dhcp.{}.ipaddress'.format(interface))
            except AdbShellError:
                res = ''
            if matcher := IP_PATTERN.search(res):
                return matcher.group(0)

            # sorry, no more methods...
            return None

        interfaces = ('eth0', 'eth1', 'wlan0')
        for i in interfaces:
            ip = get_ip_address_from_interface(i)
            if ip and not ip.startswith('172.') and not ip.startswith('127.') and not ip.startswith('169.'):
                return ip
        return None

    @property
    def foreground_activity(self) -> str:
        """
        获取当前前台activity

        Raises:
            AdbBaseError: 没有获取到前台activity
        Returns:
            当前activity
        """
        if m := self._get_activityRecord(key='mResumedActivity'):
            return m.group('activity')
        else:
            raise AdbBaseError(f'running_activities get None')

    @property
    def foreground_package(self) -> str:
        """
        获取当前前台包名

        Raises:
            AdbBaseError: 没有获取到前台包名
        Returns:
            当前包名
        """
        if m := self._get_activityRecord(key='mResumedActivity'):
            return m.group('packageName')
        else:
            raise AdbBaseError(f'running_activities get None')

    @property
    def running_activities(self) -> List[str]:
        """
        获取正在运行的所有activity

        Raises:
            AdbBaseError: 未获取到当前运行的activity
        Returns:
            所有正在运行的activity
        """
        if m := self._get_running_activities():
            return [match.group('activity') for match in m]
        else:
            raise AdbBaseError(f'running_activities get None')

    @property
    def running_package(self) -> List[str]:
        """
        获取正在运行的所有包名

        Raises:
            AdbBaseError: 未获取到当前运行的包名
        Returns:
            所有正在运行的包名
        """
        if m := self._get_running_activities():
            return [match.group('packageName') for match in m]
        else:
            raise AdbBaseError(f'running_activities get None')

    @property
    def default_ime(self) -> str:
        """
        获取当前输入法ID

        Returns:
            输入法ID
        """
        try:
            ime = self.shell(['settings', 'get', 'secure', 'default_input_method']).strip()
        except AdbShellError:
            ime = None
        return ime

    @property
    def ime_list(self) -> List[str]:
        """
        获取系统可用输入法

        Returns:
            输入法列表
        """
        if ret := self.shell(['ime', 'list', '-s']):
            return ret.split()

    def is_keyboard_shown(self) -> bool:
        """
        判断键盘是否显示

        Returns:
            True显示键盘/False未显示键盘
        """

        if ret := self.shell(['dumpsys', 'input_method']):
            return 'mInputShown=true' in ret
        return False

    def is_screenon(self) -> bool:
        """
        检测屏幕打开关闭状态

        Raises:
            AdbBaseError: 未检测到屏幕打开状态
        Returns:
            True屏幕打开/False屏幕关闭
        """
        pattern = re.compile(r'mScreenOnFully=(?P<Bool>true|false)')
        ret = self.shell(['dumpsys', 'window', 'policy'])

        if m := pattern.search(ret):
            return m.group('Bool') == 'true'
        else:
            # MIUI11
            screenOnRE = re.compile('screenState=(SCREEN_STATE_ON|SCREEN_STATE_OFF)')
            m = screenOnRE.search(self.shell('dumpsys window policy'))
            if m:
                return m.group(1) == 'SCREEN_STATE_ON'
        raise AdbBaseError('Could not determine screen ON state')

    def is_locked(self) -> bool:
        """
        判断屏幕是否锁定

        Raises:
            AdbBaseError: 未检测到屏幕锁定状态
        Returns:
            True屏幕锁定/False屏幕未锁定
        """
        ret = self.shell('dumpsys window policy')
        pattern = re.compile(r'(?:mShowingLockscreen|isStatusBarKeyguard|showing)=(?P<Bool>true|false)')

        if m := pattern.search(ret):
            return m.group('Bool') == 'true'
        raise AdbBaseError('Could not determine screen lock state')

    def get_pid_by_name(self, packageName: str, fuzzy_search: Optional[bool] = False) -> List[Tuple[int, str]]:
        """
        根据进程名获取对应pid

        Args:
            packageName: 包名
            fuzzy_search: if True,返回所有包含packageName的pid
        Returns:
            获取到的进程列表(pid, name)
        """
        ps_len = len(self.PS_HEAD)
        if fuzzy_search:
            return [(int(proc[self.PS_HEAD.index('pid')]), proc_name) for proc in self.get_process()
                    if len(proc) == ps_len and (packageName in (proc_name := proc[self.PS_HEAD.index('name')]))]
        else:
            return [(int(proc[self.PS_HEAD.index('pid')]), proc_name) for proc in self.get_process()
                    if len(proc) == ps_len and (packageName == (proc_name := proc[self.PS_HEAD.index('name')]))]

    def get_process(self, flag_options: Union[str, list, tuple, None] = None) -> List[List[str]]:
        """
        command 'adb shell ps'

        Returns:
            所有进程的列表
        """
        cmds = ['ps']
        if isinstance(flag_options, str):
            cmds.append(flag_options)
        elif isinstance(flag_options, (list, tuple)):
            cmds = cmds + flag_options

        process = []
        process_pattern = re.compile('(\S+)')
        if ret := self.shell(cmds):
            ret = ret.splitlines()
            for v in ret[1:]:
                if proc := process_pattern.findall(v):
                    process.append(proc)

        return process

    def _get_running_activities(self) -> Optional[List[Match[str]]]:
        """
        command 'adb dumpsys activity activities'
        获取各个Stack中正在运行的activities参数

        Returns:
            包含了多个Match的列表, Match可以使用memory/user/packageName/activity/task
        """
        running_activities = []
        cmds = ['dumpsys', 'activity', 'activities']
        activities = self.shell(cmds)
        # 获取Stack
        pattern = re.compile(r'Stack #([\d]+):')
        stack = pattern.findall(activities)
        if not stack:
            return None
        stack.sort()
        # 根据Stack拆分running activities
        for index in stack:
            pattern = re.compile(rf'Stack #{index}[\s\S]+?Running activities \(most recent first\):([\s\S]+?)\r\n\r\n')
            ret = pattern.findall(activities)
            if ret:
                running_activities.append(ret[0])

        ret = []
        pattern = re.compile(
            r"TaskRecord[\s\S]+?Run #(?P<index>\d+):[\s]?"
            r"ActivityRecord\{(?P<memory>.*) (?P<user>.*) (?P<packageName>.*)/(?P<activity>\.?.*) (?P<task>.*)}")
        for v in running_activities:
            if m := pattern.search(v):
                ret.append(m)

        return ret

    def _get_activityRecord(self, key: str) -> Optional[Match[str]]:
        """
        command 'adb dumpsys activity activities'
        根据<key>获取对应ActivityRecord信息

        Returns:
            Match,可以使用memory/user/packageName/activity/task
        """
        cmds = ['dumpsys', 'activity', 'activities']
        ret = self.shell(cmds)
        pattern = re.compile(
            rf'{key}: '
            r'ActivityRecord\{(?P<memory>.*) (?P<user>.*) (?P<packageName>.*)/\.?(?P<activity>.*) (?P<task>.*)}[\n\r]')

        if m := pattern.search(ret):
            return m
        else:
            return None

    def check_app(self, name: str) -> bool:
        """
        判断应用是否安装

        Args:
            name: package name

        Returns:
            return True if find, false otherwise
        """
        if name in self.app_list():
            return True
        return False

    def check_file(self, path: str, name: str) -> bool:
        """
        command 'adb shell find <name> in the <path>'

        Args:
            path: 在设备上的路径
            name: 需要检索的文件名

        Returns:
            bool 是否找到文件
        """
        return bool(self.raw_shell(['find', path, '-name', name]))

    def check_dir(self, path: str, name: str, flag: bool = False) -> bool:
        """
        command 'adb shell cd <path>

        Args:
            path: 在设备上的路径
            name: 需要检索的文件夹名
            flag: 如果为True,则会在找不到文件夹时候创建一个新的

        Returns:
            bool 是否存在路径
        """
        if not bool(self.raw_shell(['find', path, '-maxdepth 1', '-type d', '-name', name])):
            if flag:
                self.create_dir(path=path, name=name)
            return False

        return True

    def create_dir(self, path: str, name: str):
        """
        command 'adb shell mkdir

        Args:
            path: 在设备上的路径
            name: 需要创建的文件夹名

        Returns:
            None
        """
        self.shell(cmds=['mkdir', '-m 755', os.path.join(path, name)])

    def get_file_size(self, remote: str) -> int:
        """
        command 'adb shell du -k -s <remote>' 获取remote路径下文件大小

        Args:
            remote: 文件路径

        Returns:
            文件大小(KB)
        """
        ret = self.shell(cmds=['du', '-k', '-s', remote])
        pattern = re.compile(rf'(\d+)\s*{remote}')
        if m := pattern.findall(ret):
            return int(m[-1])

    def getMaxXY(self) -> Tuple[int, int]:
        """
        获取屏幕可点击的最大长宽距离

        Returns:
            max_x,max_y
        """
        ret = self.shell(['getevent', '-p']).split('\n')
        max_x, max_y = None, None
        pattern = re.compile(r'max ([0-9]+)')
        for i in ret:
            if i.find('0035') != -1:
                if ret := pattern.findall(i):
                    max_x = int(ret[0])

            if i.find('0036') != -1:
                if ret := pattern.findall(i):
                    max_y = int(ret[0])
        return max_x, max_y

    def getPhysicalDisplayInfo(self) -> Dict[str, Union[int, float]]:
        """
        Get value for display dimension and density from `mPhysicalDisplayInfo` value obtained from `dumpsys` command.

        Returns:
            physical display info for dimension and density

        """
        phyDispRE = re.compile(
            r'.*PhysicalDisplayInfo{(?P<width>\d+) x (?P<height>\d+), .*, density (?P<density>[\d.]+).*')
        ret = self.raw_shell('dumpsys display')
        if m := phyDispRE.search(ret):
            displayInfo = {}
            for prop in ['width', 'height']:
                displayInfo[prop] = int(m.group(prop))
            for prop in ['density']:
                # In mPhysicalDisplayInfo density is already a factor, no need to calculate
                displayInfo[prop] = float(m.group(prop))
            return displayInfo

        # This could also be mSystem or mOverscanScreen
        phyDispRE = re.compile('\s*mUnrestrictedScreen=\((?P<x>\d+),(?P<y>\d+)\) (?P<width>\d+)x(?P<height>\d+)')
        # This is known to work on older versions (i.e. API 10) where mrestrictedScreen is not available
        dispWHRE = re.compile(r'\s*DisplayWidth=(?P<width>\d+) *DisplayHeight=(?P<height>\d+)')
        ret = self.raw_shell('dumpsys window')
        m = phyDispRE.search(ret, 0)
        if not m:
            m = dispWHRE.search(ret, 0)
        if m:
            displayInfo = {}
            for prop in ['width', 'height']:
                displayInfo[prop] = int(m.group(prop))
            for prop in ['density']:
                d = self._getDisplayDensity(strip=True)
                if d:
                    displayInfo[prop] = d
                else:
                    # No available density information
                    displayInfo[prop] = -1.0
            return displayInfo

        # gets C{mPhysicalDisplayInfo} values from dumpsys. This is a method to obtain display dimensions and density
        phyDispRE = re.compile(r'Physical size: (?P<width>\d+)x(?P<height>\d+).*Physical density: (?P<density>\d+)',
                               re.S)
        ret = self.raw_shell('wm size; wm density')

        if m := phyDispRE.search(ret):
            displayInfo = {}
            for prop in ['width', 'height']:
                displayInfo[prop] = int(m.group(prop))
            for prop in ['density']:
                displayInfo[prop] = float(m.group(prop))
            return displayInfo

        return {}

    def _getDisplayDensity(self, strip=True) -> Union[float, int]:
        """
        Get display density

        Args:
            strip: strip the output
        Returns:
            display density
        """
        BASE_DPI = 160.0

        if density := self.getprop('ro.sf.lcd_density', strip):
            return float(density) / BASE_DPI

        if density := self.getprop('qemu.sf.lcd_density', strip):
            return float(density) / BASE_DPI
        return -1.0

    def getDisplayOrientation(self) -> int:
        """
        Another way to get the display orientation, this works well for older devices (SDK version 15)

        Returns:
            display orientation information

        """
        # another way to get orientation, for old sumsung device(sdk version 15)
        SurfaceFlingerRE = re.compile(r'orientation=(\d+)')
        ret = self.shell('dumpsys SurfaceFlinger')
        if m := SurfaceFlingerRE.search(ret):
            return int(m.group(1))

        # Fallback method to obtain the orientation
        # See https://github.com/dtmilano/AndroidViewClient/issues/128
        surfaceOrientationRE = re.compile(r'SurfaceOrientation:\s+(\d+)')
        ret = self.shell('dumpsys input')
        if m := surfaceOrientationRE.search(ret):
            return int(m.group(1))
        # We couldn't obtain the orientation
        warnings.warn("Could not obtain the orientation, return 0")
        return 0

    def keyevent(self, keycode: Union[str, int]) -> None:
        """
        command 'adb shell input keyevent'
        Args:
            keycode: key code number or name

        Returns:
            None
        """
        self.shell(['input', 'keyevent', str(keycode)])

    def getprop(self, key: str, strip: Optional[bool] = True) -> Optional[str]:
        """
        command 'adb shell getprop <key>

        Args:
            key: 需要查询的参数
            strip: 删除文本头尾空格

        Returns:
            getprop获取到的参数
        """
        ret = self.raw_shell(['getprop', key])
        return strip and ret.rstrip() or ret

    def get_app_install_path(self, packageName: str) -> Optional[str]:
        """
        command 'adb shell pm path <package>'

        Args:
            packageName: 需要查找的包名

        Returns:
            包安装路径
        """
        if packageName in self.app_list():
            stdout = self.shell(['pm', 'path', packageName])
            if 'package:' in stdout:
                return stdout.split('package:')[1].strip()
        else:
            return None

    def app_list(self, flag_options: Union[str, list, tuple, None] = None) -> List[str]:
        """
        command 'adb shell pm list packages'

        Args:
            flag_options: 可指定参数
                    "-f",  # 查看它们的关联文件。
                    "-d",  # 进行过滤以仅显示已停用的软件包。
                    "-e",  # 进行过滤以仅显示已启用的软件包。
                    "-s",  # 进行过滤以仅显示系统软件包。
                    "-3",  # 进行过滤以仅显示第三方软件包。
                    "-i",  # 查看软件包的安装程序。
                    "-u",  # 也包括已卸载的软件包。
                    "--user user_id",  # 要查询的用户空间。

        Returns:

        """
        if self.sdk_version >= 24:
            cmds = ['cmd', 'package', 'list', 'packages']
        else:
            cmds = ['pm', 'list', 'packages']

        if isinstance(flag_options, str):
            cmds.append(flag_options)
        elif isinstance(flag_options, (list, tuple)):
            cmds = cmds + flag_options
        ret = self.shell(cmds)
        packages = ret.splitlines()
        # remove all empty string; "package:xxx" -> "xxx"
        packages = [p.split(":")[1] for p in packages if p]
        return packages

    def broadcast(self, action: str, user: str = None) -> None:
        """
        发送广播信号

        Args:
            action: 需要触发的广播行为
            user: 向指定组件广播

        Returns:
            None
        """
        cmds = ['am', 'broadcast'] + ['-a', action]
        if user:
            cmds += ['-n', user]
        self.start_cmd(cmds)

    def shell(self, cmds: Union[list, str], decode: Optional[bool] = True, skip_error: Optional[bool] = False) \
            -> Union[str, bytes]:
        """
        command 'adb shell

        Args:
            cmds (list,str): 需要运行的参数
            decode (bool): 是否解码stdout,stderr
            skip_error (bool): 是否跳过报错
        Raises:
            AdbShellError:指定shell命令时出错
        Returns:
            命令返回结果
        """
        if self.sdk_version < 25:
            # sdk_version < 25, adb shell 不返回错误
            # https://issuetracker.google.com/issues/36908392
            cmds = split_cmd(cmds) + [';', 'echo', '---$?---']
            ret = self.raw_shell(cmds, decode=decode).rstrip()
            if m := re.match("(.*)---(\d+)---$", ret, re.DOTALL):
                stdout = m.group(1)
                returncode = int(m.group(2))
            else:
                warnings.warn('return code not matched')
                stdout = ret
                returncode = 0

            if returncode > 0:
                if not skip_error:
                    raise AdbShellError(stdout, stderr=None)
            return stdout
        else:
            try:
                ret = self.raw_shell(cmds, decode=decode, skip_error=skip_error)
            except AdbError as err:
                raise AdbShellError(err.stdout, err.stderr)
            else:
                return ret

    def raw_shell(self, cmds: Union[list, str], decode: Optional[bool] = True, skip_error: Optional[bool] = False) \
            -> str:
        """
        command 'adb shell

        Args:
            cmds (list): 需要运行的参数
            decode (bool): 是否解码stdout,stderr
            skip_error (bool): 是否跳过报错
        Returns:
            命令返回结果
        """
        cmds = ['shell'] + split_cmd(cmds)
        stdout = self.cmd(cmds, decode=False, skip_error=skip_error)
        if not decode:
            return stdout

        try:
            return stdout.decode(self.SHELL_ENCODING)
        except UnicodeDecodeError:
            return str(repr(stdout))

    def start_shell(self, cmds: Union[list, str]):
        cmds = ['shell'] + split_cmd(cmds)
        return self.start_cmd(cmds)


class ADBDevice(ADBShell):
    def __init__(self, device_id: Optional[str] = None, adb_path: Optional[str] = None,
                 host: Optional[str] = ANDROID_ADB_SERVER_HOST,
                 port: Optional[int] = ANDROID_ADB_SERVER_PORT):
        """
        Args:
            device_id (str): 指定设备名
            adb_path (str): 指定adb路径
            host (str): 指定连接地址
            port (int): 指定连接端口
        """
        super(ADBDevice, self).__init__(device_id=device_id, adb_path=adb_path, host=host, port=port)
        self.set_input_method(ime_method=ADB_DEFAULT_KEYBOARD, ime_apk_path=ADB_KEYBOARD_APK_PATH)

    def screenshot(self, rect: Union[Rect, Tuple[int, int, int, int], List[int]] = None) -> np.ndarray:
        """
        command 'adb screencap'

        Args:
            rect: 自定义截取范围 Rect/(x, y, width, height)

        Raises:
                ValueError:传入参数rect错误
                OverflowError:rect超出屏幕边界范围
        Returns:
            图像数据
        """
        remote_path = ADB_CAP_RAW_REMOTE_PATH
        raw_local_path = ADB_CAP_RAW_LOCAL_PATH.format(device_id=self.get_device_id(True))

        self.raw_shell(['screencap', remote_path])
        self.start_shell(['chmod', '755', remote_path])
        self.pull(local=raw_local_path, remote=remote_path)

        # read size
        img_data = np.fromfile(raw_local_path, dtype=np.uint16)
        width, height = img_data[2], img_data[0]
        _data = img_data
        # read raw
        _line = 4  # 色彩通道数
        img_data = np.fromfile(raw_local_path, dtype=np.uint8)
        img_data = img_data[slice(_line * 3, len(img_data))]
        # 范围截取
        img_data = img_data.reshape(width, height, _line)
        width, height = img_data.shape[1::-1]
        if rect:
            if isinstance(rect, Rect):
                pass
            elif isinstance(rect, (tuple, list)):
                try:
                    rect = Rect(*rect)
                except TypeError:
                    raise ValueError('param "rect" takes 4 positional arguments <x,y,width,height>')
            else:
                raise ValueError('param "rect" must be <Rect>/tuple/list')

            # 判断边界是否超出width,height
            if not Rect(0, 0, width, height).contains(rect):
                raise OverflowError(f'rect不能超出屏幕边界 {rect}')
            x_min, y_min = int(rect.tl.x), int(rect.tl.y)
            x_max, y_max = int(rect.br.x), int(rect.br.y)
            img_data = img_data[y_min:y_max, x_min:x_max]

        img_data = img_data[:, :, ::-1][:, :, 1:4]  # imgData中rgbA转为ABGR,并截取bgr
        # 删除raw临时文件
        os.remove(raw_local_path)
        return img_data

    def start_app(self, package: str, activity: Optional[str] = None):
        """
        if not activity command 'adb shell monkey'
        if activity command 'adb shell am start

        Args:
            package: package name
            activity: activity name

        Returns:
            None
        """
        if not activity:
            cmds = ['monkey', '-p', package, '-c', 'android.intent.category.LAUNCHER', '1']
        else:
            cmds = ['am', 'start', '-n', f'{package}/{package}.{activity}']
        self.shell(cmds)

    def stop_app(self, package: str) -> None:
        """
        command 'adb shell am force-stop' to force stop the application

        Args:
            package: package name

        Returns:
            None
        """
        self.shell(['am', 'force-stop', package])

    def clear_app(self, package: str) -> None:
        """
        command 'adb shell pm clear' to force stop the application
        这条命令的效果相当于在设置里的应用信息界面点击了「清除缓存」和「清除数据」

        Args:
            package: package name

        Returns:
            None
        """
        self.shell(['pm', 'clear', package])

    def install(self, local: str, install_options: Union[str, list, None] = None) -> bool:
        """
        push apk 文件到 /data/local/tmp;
        调用 pm install 安装;
        删除 /data/local/tmp 下的对应 apk 文件

        Args:
            local: apk文件路径
            install_options: 可指定参数
                    "-r",  # 重新安装现有应用，并保留其数据。
                    "-t",  # 允许安装测试 APK。
                    "-g",  # 授予应用清单中列出的所有权限。
                    "-d",  # 允许APK降级覆盖安装
                    "-l",  # 将应用安装到保护目录/mnt/asec
                    "-s",  # 将应用安装到sdcard
        Raises:
            AdbInstallError: 安装失败
            AdbError: 安装失败
        Returns:
            安装成功返回True
        """
        apk_name = os.path.split(local)[-1]
        remote = os.path.join(ANDROID_TMP_PATH, apk_name)
        self.push(local=local, remote=remote)
        try:
            flag = self.pm_install(remote=remote, install_options=install_options)
            self.raw_shell(f'rm -r {remote}')
            return flag
        except AdbBaseError as err:
            raise err

    def pm_install(self, remote: str, install_options: Union[str, list, None] = None) -> bool:
        """
        command 'adb shell pm install <local>'

        Args:
            remote: apk文件路径
            install_options: 可指定参数
                    "-r",  # 重新安装现有应用，并保留其数据。
                    "-t",  # 允许安装测试 APK。
                    "-g",  # 授予应用清单中列出的所有权限。
                    "-d",  # 允许APK降级覆盖安装
                    "-l",  # 将应用安装到保护目录/mnt/asec
                    "-s",  # 将应用安装到sdcard
        Raises:
            AdbInstallError: 安装失败
            AdbError: 安装失败
        Returns:
            安装成功返回True
        """
        cmds = ['pm', 'install']
        if isinstance(install_options, str):
            cmds.append(install_options)
        elif isinstance(install_options, list):
            cmds += install_options

        cmds = cmds + [remote]
        proc = self.start_shell(cmds)
        stdout, stderr = proc.communicate()

        stdout = stdout.decode(get_std_encoding(stdout))
        stderr = stderr.decode(get_std_encoding(stdout))

        if proc.returncode == 0:
            return True
        elif err := re.compile(r"Failure \[(.+):.+\]").search(stderr):
            raise AdbInstallError(err.group(1))
        else:
            raise AdbError(stdout, stderr)

    def tap(self, point: Union[Tuple[int, int], Point]):
        """
        command 'adb shell input tap' 点击屏幕

        Args:
            point: 坐标(x,y)

        Returns:
            None
        """
        x, y = None, None
        if isinstance(point, Point):
            x, y = point.x, point.y
        elif isinstance(point, (tuple, list)):
            x, y = point[0], point[1]
        self.shell(f'input tap {x} {y}')

    def swipe(self, start_point: Union[Tuple[int, int], Point], end_point: Union[Tuple[int, int], Point],
              duration: int = 500) -> None:
        """
        command 'adb shell input swipe> 滑动屏幕

        Args:
            start_point: 起点坐标
            end_point: 重点坐标
            duration: 操作后延迟
        Returns:
            None
        """

        def _handle(point):
            if isinstance(point, Point):
                return point.x, point.y
            elif isinstance(point, (tuple, list)):
                return point

        start_x, start_y = _handle(start_point)
        end_x, end_y = _handle(end_point)

        version = self.sdk_version
        if version <= 15:
            raise AdbSDKVersionError(f'swipe: API <= 15 not supported (version={version})')
        elif version <= 17:
            self.shell(f'input swipe {start_x} {start_y} {end_x} {end_y} {duration}')
        else:
            self.shell(f'input touchscreen swipe {start_x} {start_y} {end_x} {end_y}')

    def set_input_method(self, ime_method: str, ime_apk_path: Optional[str] = None) -> None:
        """
        设置输入法

        Args:
            ime_method: 输入法ID
            ime_apk_path: 输入法安装包
        Returns:
            None
        """
        if ime_method not in self.ime_list:
            if ime_apk_path:
                self.install(ime_apk_path)
        if self.default_ime != ime_method:
            self.shell(['ime', 'enable', ime_method])
            self.shell(['ime', 'set', ime_method])

    def text(self, text, enter: Optional[bool] = False):
        """
        input text on the device
        预置命令: #CLEAR# 清除当前输入框内所有字符。在使用原生input时不能保证百分百清空输入框数据

        Args:
            text: 需要输入的字符
            enter: press 'Enter' key

        Returns:
            None
        """
        if self.default_ime == ADB_DEFAULT_KEYBOARD:
            if text == '#CLEAR#':
                self.broadcast('ADB_CLEAR_TEXT')
            else:
                self.shell(f"am broadcast -a ADB_INPUT_TEXT --es msg '{str(text)}'")
        else:
            if text == '#CLEAR#':
                logger.warning('建议使用AdbKeyboard')
                for i in range(255):
                    self.keyevent('KEYCODE_CLEAR')
            else:
                self.shell(['input', 'text', str(text)])

        if enter:
            time.sleep(1)
            self.keyevent('ENTER')


__all__ = ['ADBClient', 'ADBDevice']
