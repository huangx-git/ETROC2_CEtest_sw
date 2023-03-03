#!/usr/bin/env python3
import time

def module_mon(module, sleep=10):
    from threading import Thread
    mon = Monitoring(module.monitor)
    t = Thread(target = mon.run, args=(sleep,))
    t.start()
    return mon

class Monitoring:

    def __init__(self, fun):
        self._running = True
        self.fun = fun

    def terminate(self):
        self._running = False

    def run(self, sleep=60):
        while self._running and True:
            self.fun()
            time.sleep(sleep)
