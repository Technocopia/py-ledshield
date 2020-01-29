from threading import Thread, Lock

class EffectRunner(object):
    running = False
    effect = None
    effectThread = None
    tick_count = 0
    def __init__(self):
        self._lock = Lock()

    def _runEffect(self):
        print("_run")
        while self.effect.running:
            if self.tick_count % 100 == 0:
                print(self.tick_count, flush=True)
            if not self.effect.running:
                print("tick w/ no running!", flush=True)
            else:
                # grabbing the lock here can cause issues.. need to think of a
                #way to avoid issues here
                #with self._lock:
                    self.effect.tick()
                    self.tick_count += 1
        print("_run ceasing", flush=True)
        #with self._lock:
        #    self.effect.stop()

    def stopEffect(self):
        if self.effect:
            print("getting my lock on", flush=True)
            with self._lock:
                print("calling effect.stop", flush=True)
                self.effect.stop()
                print("called effect.stop", flush=True)
                self.effect = None
        else:
            print("effect not found!", flush=True)
        print("lock released - waiting for termination", flush=True)
        self.effectThread.join()
        print("ending")


    def startEffect(self, effect):
        if(self.effect):
            print("stopping existing effect", flush=True)
            self.stopEffect()
        print("setting effect", flush=True)
        self.effect = effect

        with self._lock:
            self.effect.start()

        self.effectThread = Thread(target=self._runEffect)
        print("setting thread", flush=True)
        self.effectThread.start()

class EffectRunnerOld(Thread):
    running = False
    effect = None

    def __init__(self):
        Thread.__init__(self)

    def setEffect(self, effect):
        if(self.effect):
            self.effect.stop()

        self.effect = effect

    def stopEffect(self):
        #self.running = False
        if self.effect:
            self.effect.stop()

    def startEffect(self):
        #self.running = True
        if self.effect:
            self.effect.start()

    def run(self):
        self.running = True
        while self.running:
            self.effect.tick()
