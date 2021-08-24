# -*- coding: utf-8 -*-
import re
import time
from typing import Optional, Union, List, Tuple

from adbutils import ADBDevice

from loguru import logger


class Fps(object):
    _MIN_NORMALIZED_FRAME_LENGTH = 0.5
    Movie_FrameTime = 1000 / 24 / 1000  # 电影帧耗时,单位为秒
    nanoseconds_per_second = 1e9  # 纳秒转换成秒
    pending_fence_timestamp = (1 << 63) - 1  # 查询某帧数据出问题的时候，系统会返回一个64位的int最大值，忽略这列数据

    def __init__(self, device: ADBDevice):
        self.device = device
        self._last_drawEnd_timestamps = None

    def get_fps_surfaceView(self, surface_name: str):
        _Fps = 0
        _FTime = 0
        _Jank = 0
        _BigJank = 0
        _Stutter = 0

        # step1: 根据window名,获取帧数信息
        stat = self._get_surfaceFlinger_stat(surface_name)

        # step2: 提取帧数信息,分别得到刷新周期/绘制图像开始时间列表/绘制耗时列表/绘制结束列表
        refresh_period, _drawStart_timestamps, _vsync_timestamps, _drawEnd_timestamps = \
            self._pares_surfaceFlinger_stat(stat)

        if not _drawStart_timestamps or not _vsync_timestamps or not _drawEnd_timestamps:
            return None

        # step3: 根据上次获取的最后一帧时间戳,切分本次有效帧列表
        if self._last_drawEnd_timestamps in _drawEnd_timestamps:
            index = list(reversed(_drawEnd_timestamps)).index(self._last_drawEnd_timestamps)
            index = len(_drawEnd_timestamps) - index + 1
            if index == len(_drawEnd_timestamps) - 1:
                index = 0
        else:
            index = 0

        drawStart_timestamps = _drawStart_timestamps[index:]
        vsync_timestamps = _vsync_timestamps[index:]
        drawEnd_timestamps = _drawEnd_timestamps[index:]

        # step4: 计算FPS(帧数)
        if (frame_count := len(vsync_timestamps)) < 2:
            return None
        seconds = vsync_timestamps[-1] - vsync_timestamps[0]
        _Fps = round((frame_count - 1) / seconds, 2)

        # step5: 计算FTime(帧耗时),
        vsync_frameTimes = self._get_frameTimes(vsync_timestamps)
        if vsync_frameTimes:
            _FTime = max(vsync_frameTimes)
            _FTime *= 1000

        # step6: 计算Jank
        # 由于step3只截取了有效帧,因此需要额外收集前三帧,用于计算帧耗时
        if index - 3 >= 0:
            jank_vsync_timestamps = _vsync_timestamps[index - 3:]
        else:
            jank_vsync_timestamps = vsync_timestamps
        jank_vsync_frameTimes = self._get_frameTimes(jank_vsync_timestamps)
        _Jank, _BigJank, Jank_time = self._get_perfdog_jank(jank_vsync_frameTimes)
        _Stutter = Jank_time / seconds * 100

        # step End: 记录最后一帧时间戳
        self._last_drawEnd_timestamps = drawEnd_timestamps[-1]

        return _Fps, _FTime, _Jank, _BigJank, _Stutter

    def clear_surfaceFlinger_latency(self) -> bool:
        """
        command 'adb shell dumpsys SurfaceFlinger --latency-clear' 清除SurfaceFlinger latency里的数据

        Returns:
            True设备支持dumpsys SurfaceFlinger --latency, 否则为False
        """
        ret = self.device.shell(['dumpsys', 'SurfaceFlinger', '--latency-clear'])
        return not len(ret)

    def _get_surfaceFlinger_stat(self, surface_name: Optional[str] = None) -> str:
        """
        command 'adb shell dumpsys SurfaceFlinger --latency <Surface Name>

        Returns:
            sufaceFlinger stat
        """
        ret = self.device.shell(['dumpsys', 'SurfaceFlinger', '--latency', self._pares_activity_name(surface_name)])
        if len(ret.splitlines()) > 1:
            return ret
        surface_name = self.get_possible_activity() or surface_name
        logger.warning('warning to get surfaceFlinger try again')
        return self._get_surfaceFlinger_stat(surface_name)

    def _pares_surfaceFlinger_stat(self, stat: str) -> Tuple[float, List[float], List[float], List[float]]:
        """
        处理SurfaceFlinger的信息，返回(刷新周期/绘制图像开始时间列表/绘制耗时列表/绘制结束列表)

        like:
            16666666
            10771456257842  10771499569140	10771456257842
            10771473192729	10771516235806	10771473192729
            10771490277889	10771532902472	10771490277889
            10771507357378	10771549569138	10771507357378
            10771523229435	10771566235804	10771523229435
            ...

        Args:
            stat: dumpsys SurfaceFlinger获得的信息

        Returns:
            刷新周期/绘制图像开始时间列表/绘制耗时列表/绘制结束列表
        """
        stat = stat.splitlines()
        # 三个列表分别对应dumpsys SurfaceFlinger的每一列

        # A) when the app started to draw
        # 开始绘制图像的瞬时时间
        drawStart_timestamps = []

        # B) the vsync immediately preceding SF submitting the frame to the h/w
        # 垂直同步软件把帧提交给硬件之前的瞬时时间戳;VSYNC信令将软件SF帧传递给硬件HW之前的垂直同步时间
        vsync_timestamps = []

        # C) timestamp immediately after SF submitted that frame to the h/w
        # 完成绘制的瞬时时间;SF将帧传递给HW的瞬时时间，
        drawEnd_timestamps = []

        # 刷新周期
        refresh_period = int(stat[0]) / self.nanoseconds_per_second

        # 清除无用的空数据
        empty_data = [0, 0, 0]
        pattern = re.compile(r'(\d+)\s*(\d+)\s*(\d+)')
        for line in stat[1:]:
            # 确认数据结构,与数据是否有效
            fields = pattern.search(line)
            if not fields:
                continue
            
            # 判断数据是否有效
            fields = [int(v) for v in fields.groups()]
            if fields == empty_data or self.pending_fence_timestamp in fields:
                continue

            drawStart_timestamp = fields[0]
            drawStart_timestamp /= self.nanoseconds_per_second

            vsync_timestamp = fields[1]
            vsync_timestamp /= self.nanoseconds_per_second

            drawEnd_timestamp = fields[2]
            drawEnd_timestamp /= self.nanoseconds_per_second

            drawStart_timestamps.append(drawStart_timestamp)
            vsync_timestamps.append(vsync_timestamp)
            drawEnd_timestamps.append(drawEnd_timestamp)

        return refresh_period, drawStart_timestamps, vsync_timestamps, drawEnd_timestamps

    @staticmethod
    def _get_frameTimes(data: List[float]) -> List[float]:
        """
        计算两帧渲染耗时

        Args:
            data: 包含帧时间戳的列表

        Returns:
            两帧渲染耗时列表
        """
        deltas = [t2 - t1 for t1, t2 in zip(data, data[1:])]
        return deltas

    def _get_perfdog_jank(self, data: List[float]) -> Tuple[int, int, float]:
        """
        根据每帧耗时,计算jank

        同时满足两条件，则认为是一次卡顿Jank.
            1. FrameTime>前三帧平均耗时2倍。
            2. FrameTime>两帧电影帧耗时 (1000ms/24*2≈83.33ms)。

        同时满足两条件，则认为是一次严重卡顿BigJank.
            1. FrameTime >前三帧平均耗时2倍。
            2. FrameTime >三帧电影帧耗时(1000ms/24*3=125ms)
        Args:
            data: 每帧渲染耗时

        Returns:

        """
        _jank = [new for new, *last in zip(data[3:], data[2:], data[1:], data)
                 if (new >= self.Movie_FrameTime * 2) and (new > (sum(last) / 3) * 2)]

        _bigJank = [new for new, *last in zip(data[3:], data[2:], data[1:], data)
                    if (new >= self.Movie_FrameTime * 3) and (new > (sum(last) / 3) * 2)]

        jank = len(_jank)
        bigJank = len(_bigJank)
        jank_time = sum(_jank) + sum(_bigJank)

        return jank, bigJank, jank_time

    def get_possible_activity(self) -> Optional[str]:
        """
        通过 ‘dumpsys SurfaceFlinger --list',查找到当前最顶部层级名

        Returns:
            包含可能层级
        """
        ret = self.device.shell(['dumpsys', 'SurfaceFlinger', '--list']).strip().splitlines()
        # 特殊适配谷歌手机
        if self.device.manufacturer == 'Google':
            # adb shell dumpsys SurfaceFlinger --latency 'SurfaceView[xx.xx.xx.xx/org.xx.lua.AppActivity](BLAST)#0'
            buffering_stats_pattern = re.compile(r'SurfaceView\[.*\(BLAST\).*', re.DOTALL)
        else:
            buffering_stats_pattern = re.compile(r'SurfaceView -.*', re.DOTALL)
        for layer in ret:
            if layers := buffering_stats_pattern.search(layer):
                return layers.group()
        logger.error("Don't find SurfaceView")

    def check_activity_usable(self, activity_name: str) -> Optional[str]:
        """
        检查activity是否有效,command 'adb shell dumpsys SurfaceFlinge --latency <activity>'
        如果只返回了刷新周期,则认为该activity无效

        Args:
            activity_name: 需要检查的activity名

        Returns:
            满足条件的activity
        """
        if stat := self._get_surfaceFlinger_stat(activity_name):
            stat_len = len(stat.splitlines())
            if stat_len > 1:
                return activity_name

    @staticmethod
    def _pares_activity_name(activity_name: str = None) -> Optional[str]:
        """
        检查activity名是否符合标准

        Args:
            activity_name: activity名

        Returns:
            处理后的activity名
        """
        if not activity_name or not isinstance(activity_name, str):
            return ''

        # 检查是否使用冒号包裹
        pattern = re.compile(r"^'(.*)'$")
        if pattern.search(activity_name):
            return activity_name
        # 包含空格和小括号都要被冒号包裹
        pattern = re.compile(r'\s|\(')
        if pattern.search(activity_name):
            activity_name = f"'{activity_name}'"
        return activity_name
