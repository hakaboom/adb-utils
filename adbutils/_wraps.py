# -*- coding: utf-8 -*-
import time
import threading
from inspect import isfunction
from functools import wraps
from typing import Optional, Union, Tuple, List, Type


class print_run_time(object):
    def __init__(self):
        pass

    def __call__(self, func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            start_time = time.time()
            ret = func(*args, **kwargs)
            print("{}() run time is {time:.2f}ms".format(func.__name__, time=(time.time() - start_time) * 1000))
            return ret
        return wrapped_function


class retries(object):
    def __init__(self, max_tries: int, delay: Optional[int] = 1,
                 exceptions: Tuple[Type[Exception], ...] = (Exception,), hook=None):
        """
        通过装饰器实现的"重试"函数

        Args:
            max_tries: 最大可重试次数。超出次数后仍然失败,则弹出异常
            delay: 重试等待间隔
            exceptions: 需要检测的异常
            hook: 钩子函数
        """
        self.max_tries = max_tries
        self.delay = delay
        self.exceptions = exceptions
        self.hook = hook

    def __call__(self, func):
        @wraps(func)
        def wrapped_function(*args, **kwargs):
            tries = list(range(self.max_tries))
            tries.reverse()
            for tries_remaining in tries:
                try:
                    return func(*args, **kwargs)
                except self.exceptions as err:
                    if tries_remaining > 0:
                        if isfunction(self.hook):
                            self.hook(tries_remaining, err)
                        time.sleep(self.delay)
                    else:
                        raise err
        return wrapped_function


class ThreadSafeIter:
    """
    Takes an iterator/generator and makes it thread-safe by
    serializing call to the `next` method of given iterator/generator.
    """
    def __init__(self, it):
        self.it = it
        self.lock = threading.Lock()
        self._next = self.it.__next__  # py3

    def __iter__(self):
        return self

    def __next__(self):
        with self.lock:
            return self._next()

    def send(self, *args):
        with self.lock:
            return self.it.send(*args)


def threadsafe_generator(func):
    """
    A decorator that takes a generator function and makes it thread-safe.
    """
    @wraps(func)
    def wrapped_function(*a, **kw):
        return ThreadSafeIter(func(*a, **kw))
    return wrapped_function
