import subprocess
import re

from adbutils._utils import get_adb_exe, split_cmd, _popen_kwargs, get_std_encoding
from adbutils.constant import ANDROID_ADB_SERVER_HOST, ANDROID_ADB_SERVER_PORT
from typing import Union, List, Optional


class ADBClient(object):
    SUBPROCESS_FLAG = _popen_kwargs()['creationflags']

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

    @property
    def host(self):
        return self.__host

    @property
    def port(self):
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
        :return: adb server版本
        """
        ret = self.cmd('version', devices=False)
        pattern = re.compile('Android Debug Bridge version \d.\d.(\d+)\n')
        version = pattern.findall(ret)
        if version:
            return int(version[0])

    @property
    def devices(self) -> dict:
        """
        command 'adb devices'

        Returns:
            devices dict key[device_name]-value[device_state]
        """
        pattern = re.compile('([\S]+)\t([\w]+)\n?')
        ret = self.cmd("devices", devices=False)
        return {value[0]: value[1] for value in pattern.findall(ret)}

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

    def connect(self, force: Optional[bool] = False) -> None:
        """
        command 'adb connect <device_id>'

        Args:
            force: 不判断设备当前状态,强制连接

        Returns:
                None
        """
        if self.device_id and ':' in self.device_id and (force or self.status != 'devices'):
            connect_result = self.cmd("connect %s" % self.device_id, devices=False)
            # TODO: 判断设备是否连接上

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
            cmds = ['forawrd', '--remove-all']
        self.cmd(cmds)

    def get_forwards(self, device_id: str = None) -> dict:
        """
        command 'adb forward --list'

        Args:
            device_id (str): 获取指定设备下的端口
        Returns:
            forwards dict key[device_name]-value[Tuple[local, remote]]
        """
        forwards = {}
        pattern = re.compile('([\S]+)\s([\S]+)\s([\S]+)\n?')
        ret = self.cmd(['forward', '--list'], devices=False, skip_error=True)
        for value in pattern.findall(ret):
            if device_id and device_id != value[0]:
                continue
            if value[0] in forwards:
                forwards[value[0]] += [(value[1], value[2])]
            else:
                forwards[value[0]] = [(value[1], value[2])]
        return forwards

    def get_forward_port(self, remote: str):
        """
        # TODO: 准备写
        Args:
            remote:

        Returns:

        """


    @property
    def status(self) -> Union[None, str]:
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
        else:
            raise  # TODO:AdbError(stdout, stderr, ['get-state'])
    
    def cmd(self, cmds: Union[list, str], devices: Optional[bool] = True, decode: Optional[bool] = True,
            timeout: Optional[int] = None, skip_error: Optional[bool] = False):
        """
        创建cmd命令, 并返回命令返回值

        Args:
            cmds: 需要运行的参数,可以是list,str
            devices (bool): 如果为True,则需要指定device-id,命令中会传入-s
            decode (bool): 是否解码stdout,stderr
            timeout (int): 设置命令超时时间
            skip_error (bool): 是否跳过报错

        Returns:
            返回命令结果stdout
        """
        proc = self.start_cmd(cmds, devices)
        if timeout and isinstance(timeout, int):
            try:
                stdout, stderr = proc.communicate(timeout=timeout)
            except subprocess.TimeoutExpired:
                proc.kill()
                stdout, stderr = proc.communicate()
                # TODO: raise AdbTimeout
        else:
            stdout, stderr = proc.communicate()

        if decode:
            stdout = stdout.decode(get_std_encoding(stdout))
            stderr = stderr.decode(get_std_encoding(stderr))

        if proc.returncode > 0:
            if not skip_error:
                raise  # TODO: 增加对应raise

        return stdout

    def start_cmd(self, cmds: Union[list, str], devices: bool = True) -> subprocess.Popen:
        """
        创建一个Popen
        :param cmds: cmd commands
        :param devices: 如果为True,则需要指定device-id,命令中会传入-s
        :return: Popen
        """
        cmds = split_cmd(cmds)
        if devices:
            if not self.device_id:
                raise print('must set device_id')
            cmd_options = self.cmd_options + ['-s', self.device_id]
        else:
            cmd_options = self.cmd_options

        cmds = cmd_options + cmds
        proc = subprocess.Popen(
            cmds,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=self.SUBPROCESS_FLAG
        )
        return proc
