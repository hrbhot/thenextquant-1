# -*- coding:utf-8 -*-

"""
服务器心跳

Author: HuangTao
Date:   2018/04/26
"""

import asyncio
import json

from quant.utils import tools
from quant.utils import logger
from quant.config import config

__all__ = ("heartbeat", "HeartbeatSubscribe", "Heartbeat")


class HeartBeat(object):
    """ 心跳
    """

    def __init__(self):
        self._count = 0  # 心跳次数
        self._interval = 0.005  # 服务心跳执行时间间隔(秒)
        self._print_interval = config.heartbeat.get("interval", 60)  # 心跳打印时间间隔(秒)，0为不打印
        self._broadcast_interval = config.heartbeat.get("broadcast", 10)  # 心跳广播间隔(秒)，0为不广播
        self._tasks = {}  # 跟随心跳执行的回调任务列表，由 self.register 注册 {task_id: {...}}

    @property
    def count(self):
        return self._count

    def ticker(self):
        """ 启动心跳， 每interval间隔执行一次
        """
        self._count += 1

        # 打印心跳次数
        if self._print_interval > 0:
            if self._count % int(self._print_interval*200) == 0:
                logger.info("do server heartbeat, count:", self._count, caller=self)

        # 设置下一次心跳回调
        asyncio.get_event_loop().call_later(self._interval, self.ticker)

        # 执行任务回调
        for task_id, task in self._tasks.items():
            interval = task["interval"]
            if self._count % int(interval*200) != 0:
                continue
            func = task["func"]
            args = task["args"]
            kwargs = task["kwargs"]
            kwargs["task_id"] = task_id
            kwargs["heart_beat_count"] = self._count
            asyncio.get_event_loop().create_task(func(*args, **kwargs))

        # 广播服务进程心跳
        if self._broadcast_interval > 0:
            if self._count % int(self._broadcast_interval*200) == 0:
                self.alive()

    def register(self, func, interval=1, *args, **kwargs):
        """ 注册一个任务，在每次心跳的时候执行调用
        @param func 心跳的时候执行的函数
        @param interval 执行回调的时间间隔(秒)
        @return task_id 任务id
        """
        t = {
            "func": func,
            "interval": interval,
            "args": args,
            "kwargs": kwargs
        }
        task_id = tools.get_uuid1()
        self._tasks[task_id] = t
        return task_id

    def unregister(self, task_id):
        """ 注销一个任务
        @param task_id 任务id
        """
        if task_id in self._tasks:
            self._tasks.pop(task_id)

    def alive(self):
        """ 服务进程广播心跳
        """
        from quant.event import EventHeartbeat
        EventHeartbeat(config.server_id, self.count).publish()

class Heartbeat:
    """ Heartbeat object.

    Args:
        server_id: server_id.
        count: heartbeat count.
    """

    def __init__(self, server_id=None, count=None):
        """ Initialize. """
        self.server_id = server_id
        self.count = count

    @property
    def data(self):
        d = {
            "server_id": self.server_id,
            "count": self.count,
        }
        return d

    def __str__(self):
        info = json.dumps(self.data)
        return info

    def __repr__(self):
        return str(self)


class HeartbeatSubscribe:
    """ Subscribe Heartbeat.

    Args:
        server_id: server_id.
        count: heartbeat count.
        callback: Asynchronous callback function for market data update.
                e.g. async def on_event_account_update(asset: Asset):
                        pass
    """

    def __init__(self, server_id, count, callback):
        """ Initialize. """
        if server_id == "#" or count == "#":
            multi = True
        else:
            multi = False
        from quant.event import EventHeartbeat
        EventHeartbeat(server_id, count).subscribe(callback, multi)


heartbeat = HeartBeat()
