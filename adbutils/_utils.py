import platform
import sys
import os
import queue
import socket
import threading
import subprocess
from typing import IO, Optional, Union
from adbutils.constant import DEFAULT_ADB_PATH


def check_file(fileName: str):
    """check file in path"""
    return os.path.isfile(f'{fileName}')


def get_std_encoding(stream):
    """
    Get encoding of the stream
    Args:
        stream: stream
    Returns:
        encoding or file system encoding
    """
    return getattr(stream, "encoding", None) or sys.getfilesystemencoding()


def split_cmd(cmds) -> list:
    """
    Split the commands to the list for subprocess
    Args:
        cmds (str): command
    Returns:
        command list
    """
    # cmds = shlex.split(cmds)  # disable auto removing \ on windows
    return cmds.split() if isinstance(cmds, str) else list(cmds)


def _popen_kwargs() -> dict:
    creationflags = 0
    startupinfo = None
    if sys.platform.startswith('win'):
        try:
            creationflags = subprocess.CREATE_NO_WINDOW  # python 3.7+
        except AttributeError:
            creationflags = 0x8000000
    return {
        'creationflags': creationflags,
        'startupinfo': startupinfo,
    }


def get_adb_exe() -> str:
    """
    获取adb路径
    :return:
    """
    # find in $PATH
    cmds = ['adb', "--version"]
    try:
        with open(os.devnull, "w") as null:
            subprocess.check_call(
                cmds, stdout=null, stderr=subprocess.STDOUT, **_popen_kwargs()
            )
        adb_path = 'adb'
    except (FileNotFoundError, OSError, ValueError):
        system = platform.system()
        machine = platform.machine()
        adb_path = DEFAULT_ADB_PATH.get(f'{system}-{machine}')
        if not adb_path:
            adb_path = DEFAULT_ADB_PATH.get(f'{system}')
        if not adb_path:
            raise RuntimeError(f"No adb executable supports this platform({system}-{machine}).")

    return adb_path


class NonBlockingStreamReader(object):
    # TODO: 增加一个方法用于非阻塞状态将stream输出存入文件
    def __init__(self, stream: IO, raise_EOF: Optional[bool] = False, print_output: bool = True,
                 print_new_line: bool = True):
        self._s = stream
        self._q = queue.Queue()
        self._lastline = None
        self.name = id(self)

        def _populateQueue(_stream: IO, _queue: queue.Queue, kill_event: threading.Event):
            """
            Collect lines from 'stream' and put them in 'queue'

            Args:
                _stream: 文件流
                _queue: 队列
                kill_event: 一个事件管理标志

            Returns:
                None
            """
            while not kill_event.is_set():
                line = _stream.readline()
                if line is not None:
                    _queue.put(line)
                    if print_output:
                        if print_new_line and line == self._lastline:
                            continue
                        self._lastline = line
                elif kill_event.is_set():
                    break
                elif raise_EOF:
                    raise UnexpectedEndOfStream
                else:
                    break

        self._kill_event = threading.Event()
        self._t = threading.Thread(target=_populateQueue, args=(self._s, self._q, self._kill_event))
        self._t.daemon = True
        self._t.start()  # start collecting lines from the stream

    def readline(self, timeout: Union[int] = None):
        try:
            return self._q.get(block=timeout is not None, timeout=timeout)
        except queue.Empty:
            return None

    def read(self) -> bytes:
        lines = []
        while True:
            line = self.readline()
            if line is None:
                break
            lines.append(line)
        return b"".join(lines)

    def kill(self) -> None:
        self._kill_event.set()


class UnexpectedEndOfStream(Exception):
    pass


CLEANUP_CALLS = queue.Queue()


def reg_cleanup(func, *args, **kwargs):
    """
    Clean the register for given function
    Args:
        func: function name
        *args: optional argument
        **kwargs: optional arguments
    Returns:
        None
    """
    CLEANUP_CALLS.put((func, args, kwargs))


class SafeSocket(object):
    """safe and exact recv & send"""
    def __init__(self, sock=None):
        if sock is None:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        else:
            self.sock = sock
        self.buf = b""

    # PEP 3113 -- Removal of Tuple Parameter Unpacking
    # https://www.python.org/dev/peps/pep-3113/
    def connect(self, tuple_hp):
        host, port = tuple_hp
        self.sock.connect((host, port))

    def send(self, msg):
        totalsent = 0
        while totalsent < len(msg):
            sent = self.sock.send(msg[totalsent:])
            if sent == 0:
                raise socket.error("socket connection broken")
            totalsent += sent

    def recv(self, size):
        while len(self.buf) < size:
            trunk = self.sock.recv(min(size-len(self.buf), 4096))
            if trunk == b"":
                raise socket.error("socket connection broken")
            self.buf += trunk
        ret, self.buf = self.buf[:size], self.buf[size:]
        return ret

    def recv_with_timeout(self, size, timeout=2):
        self.sock.settimeout(timeout)
        try:
            ret = self.recv(size)
        except socket.timeout:
            ret = None
        finally:
            self.sock.settimeout(None)
        return ret

    def recv_nonblocking(self, size):
        self.sock.settimeout(0)
        try:
            ret = self.recv(size)
        except socket.error as e:
            # 10035 no data when nonblocking
            if e.args[0] == 10035:  # errno.EWOULDBLOCK
                ret = None
            # 10053 connection abort by client
            # 10054 connection reset by peer
            elif e.args[0] in [10053, 10054]:  # errno.ECONNABORTED:
                raise
            else:
                raise
        return ret

    def close(self):
        self.sock.close()
