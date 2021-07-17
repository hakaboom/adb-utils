import platform
import sys
import os
import subprocess

from adbutils.constant import DEFAULT_ADB_PATH


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


def get_adb_exe():
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