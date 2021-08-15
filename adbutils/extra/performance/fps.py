# -*- coding: utf-8 -*-
import time
from typing import Optional, Union, List, Tuple

from adbutils import ADBDevice

from loguru import logger


class Fps(object):
    _MIN_NORMALIZED_FRAME_LENGTH = 0.5
    nanoseconds_per_second = 1e9
    # 查询某帧数据出问题的时候，系统会返回一个64位的int最大值，忽略这列数据
    pending_fence_timestamp = (1 << 63) - 1

    def __init__(self, device: ADBDevice):
        self.device = device

    def _clear_surfaceFlinger_latency(self):
        """
        command 'adb shell dumpsys SurfaceFlinger --latency-clear' 清除SurfaceFlinger latency里的数据

        Returns:
            True设备支持dumpsys SurfaceFlinger --latency, 否则为False
        """
        ret = self.device.shell(['dumpsys', 'SurfaceFlinger', '--latency-clear'])
        return not len(ret)

    def _get_surfaceFlinger_stat(self, surface_name: Optional[str] = None):
        """
        command 'adb shell dumpsys SurfaceFlinger --latency <Surface Name>

        Returns:

        """
        if ret := self.device.shell(['dumpsys', 'SurfaceFlinger', '--latency', surface_name]):
            return ret
        logger.warning('warning to get surfaceFlinger try again')
        return self._get_surfaceFlinger_stat(surface_name)

    def _pares_surfaceFlinger_stat(self, stat: str) -> Tuple[float, List[int], List[int], List[int]]:
        """
        处理SurfaceFlinger的信息，返回(刷新周期/绘制图像开始时间列表/绘制耗时列表/绘制结束列表)

        like:
            16666666
            10771456257842  10771499569140	10771456257842
            10771473192729	10771516235806	10771473192729
            10771490277889	10771532902472	10771490277889
            10771507357378	10771549569138	10771507357378
            10771523229435	10771566235804	10771523229435

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
        empty_data = ['0', '0', '0']
        for line in stat[1:]:
            fields = line.split()
            # 确认数据结构,与数据是否有效
            if (len(fields) != 3) or (fields == empty_data):
                continue

            drawStart_timestamp = int(fields[0])
            if drawStart_timestamp == self.pending_fence_timestamp:  # 忽略异常数据
                continue
            drawStart_timestamp /= self.nanoseconds_per_second

            vsync_timestamp = int(fields[1])
            if vsync_timestamp == self.pending_fence_timestamp:  # 忽略异常数据
                continue
            vsync_timestamp /= self.nanoseconds_per_second

            drawEnd_timestamp = int(fields[2])
            if drawEnd_timestamp == self.pending_fence_timestamp:  # 忽略异常数据
                continue
            drawEnd_timestamp /= self.nanoseconds_per_second

            drawStart_timestamps.append(drawStart_timestamp)
            vsync_timestamps.append(vsync_timestamp)
            drawEnd_timestamps.append(drawEnd_timestamp)

        return refresh_period, drawStart_timestamps, vsync_timestamps, drawEnd_timestamps
