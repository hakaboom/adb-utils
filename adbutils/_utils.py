import platform
import sys
import os
import queue
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


def _popen_kwargs():
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
    def __init__(self, stream: IO, raise_EOF: Optional[bool] = False):
        self._s = stream
        self._q = queue.Queue()

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


