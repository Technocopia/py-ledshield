import cv2
import imutils
import numpy as np
import time, json
from collections import deque

# THESE ARE IN BGR
BLUE = (255, 25, 0)
GREEN = (40, 67, 40)
RED = (0, 0, 255)
# WHITE = (220, 220, 220)
YELLOW = (10, 180, 180)
# ORANGE = (10, 100, 220)


def bgrToHsvRange(bgr, threshold=30, saturationRange=(120, 255), valueRange=(120, 255)):
    hsv = bgrToHsv(bgr)
    return getHsvRange(hsv, threshold, saturationRange, valueRange)

def bgrToHsv(bgr):
    #return cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0]
    return tuple(
        map(int,cv2.cvtColor(np.uint8([[bgr]]), cv2.COLOR_BGR2HSV)[0][0])
    )


def hsvToBgr(hsv):
    # tuple(map(int, cv2....))
    # return cv2.cvtColor(np.uint8([[hsv]]), cv2.COLOR_HSV2BGR)
    #print([[hsv]])
    #return cv2.cvtColor(np.array([[hsv]]), cv2.COLOR_HSV2BGR)
    return tuple(
        map(int, cv2.cvtColor(np.uint8([[hsv]]), cv2.COLOR_HSV2BGR)[0][0])
    )

def getHsvRange(hsv, threshold=30, saturationRange=(120, 255), valueRange=(120, 255)):
    minS, maxS = saturationRange
    minV, maxV = valueRange
    minHSV = np.array([hsv[0] - threshold, minS, minV])
    maxHSV = np.array([hsv[0] + threshold, maxS, maxV])
    return minHSV, maxHSV

def rangeSplit(colorLower, colorUpper):
    hUpper, sUpper, vUpper = colorUpper
    hLower, sLower, vLower = colorLower

    if hUpper < hLower:
        raise "upper h-value is smaller than lower h-value"

    if hLower < 0 and hUpper > 180:
        raise "both upper and lower h-values are out of range"

    rangeList = []

    if hLower < 0 or hUpper > 180:
        if hLower < 0:
            rangeList.append(
                (
                    np.array([180 + hLower, sLower, vLower]),
                    np.array([180, sUpper, vUpper]),
                )
            )
            rangeList.append(
                (np.array([0, sLower, vLower]), np.array([hUpper, sUpper, vUpper]))
            )
        if hUpper > 180:
            rangeList.append(
                (np.array([hLower, sLower, vLower]), np.array([180, sUpper, vUpper]))
            )
            rangeList.append(
                (
                    np.array([0, sLower, vLower]),
                    np.array([180 - hUpper, sUpper, vUpper]),
                )
            )
    else:
        rangeList.append((colorLower, colorUpper))

    return rangeList


def inRangeFromRangeList(hsv, rangeList):
    lower, upper = rangeList[0]
    mask = cv2.inRange(hsv, lower, upper)
    for lower, upper in rangeList[1:]:
        mask |= cv2.inRange(hsv, lower, upper)
    return mask


class TimeKeeper:
    _timers = {}

    def start(self, name):
        thistimer = self._timers.setdefault(
            name,
            {
                "total": 0,
                "samples": 0,
                "last": None,
                "current": None,
                "avg": None,
                "min": None,
                "max": None,
            },
        )
        if thistimer["current"] is not None:
            print(thistimer)
            raise ValueError("Timer was already running")

        thistimer["current"] = time.time()

    def stop(self, name):
        if not self._timers[name]:
            raise ValueError("No Such Timer")

        thistimer = self._timers[name]

        if not thistimer["current"]:
            raise ValueError("Timer was stopped before it was started")

        last = time.time() - thistimer["current"]

        thistimer["last"] = last
        thistimer["min"] = min(
            i for i in [last, thistimer["min"]] if i is not None and i != 0.0
        )
        thistimer["max"] = max(i for i in [last, thistimer["max"]] if i is not None)
        count = thistimer["samples"] + 1
        thistimer["samples"] = count
        thistimer["avg"] = ((thistimer["avg"] or 0) * (count - 1) + last) / count
        thistimer["total"] += last
        thistimer["current"] = None

    def get(self, name):
        if not self._timers[name]:
            raise ValueError("No Such Timer")
        return self._timers[name]

    def __str__(self):
        return json.dumps(self._timers)


class TrackingColor:
    _bgr = None
    _hsv = None
    _rangeList = None

    def __init__(
        self, hsv, threshold=15, saturationRange=(150, 255), valueRange=(150, 255)
    ):
        self.hsv = hsv
        self.threshold = threshold
        self.saturationRange = saturationRange
        self.valueRange = valueRange

    @property
    def hsv(self):
        return self._hsv

    @hsv.setter
    def hsv(self, hsv):
        self._hsv = hsv
        self._bgr = hsvToBgr(hsv)
        self._rangeList = None

    @property
    def bgr(self):
        return self._bgr

    @bgr.setter
    def bgr(self, bgr):
        print("in bgr setter new bgr:", bgr)
        print("in bgr setter old HSV", self._hsv)

        self._bgr = bgr
        self._hsv = bgrToHsv(bgr)
        self._bgr = hsvToBgr(self._hsv)
        self._rangeList = None
        print("in bgr setter new bgr (check):", self._bgr)
        print("in bgr setter new HSV", self._hsv)


    @property
    def rangeList(self):
        if self._rangeList is None:
            colorLower, colorUpper = getHsvRange(
                self.hsv,
                threshold=self.threshold,
                saturationRange=self.saturationRange,
                valueRange=self.valueRange,
            )
            self._rangeList = rangeSplit(colorLower, colorUpper)
        return self._rangeList


class Tracker:
    name = None
    kernel = None
    colorMask = None
    contours = None
    x = None
    y = None
    radius = None

    def __init__(self, trackingColor, name=None):
        self.trackingColor = trackingColor
        self.name = name
        self.kernel = np.ones((5, 5), np.uint8)

    def createColorTrackingMask(self, hsvFrame, trackingColor):
        colorMask = inRangeFromRangeList(hsvFrame, trackingColor.rangeList)
        colorMask = cv2.erode(colorMask, self.kernel, iterations=2)
        colorMask = cv2.morphologyEx(colorMask, cv2.MORPH_OPEN, self.kernel)
        colorMask = cv2.dilate(colorMask, self.kernel, iterations=1)
        return colorMask

    def update(self, hsvFrame):
        # Determine which pixels fall within the color boundaries and then blur the binary image
        self.colorMask = self.createColorTrackingMask(hsvFrame, self.trackingColor)
        if imutils.is_cv2():
            self.contours, _ = cv2.findContours(
                self.colorMask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
        elif imutils.is_cv3():
            _, self.contours, _ = cv2.findContours(
                self.colorMask.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
            )
        # Check to see if any contours (blue stuff) were found
        if len(self.contours) > 0:
            contour = sorted(self.contours, key=cv2.contourArea, reverse=True)[0]
            # Get the radius of the enclosing circle around the found contour
            ((self.x, self.y), self.radius) = cv2.minEnclosingCircle(contour)
        else:
            self.x, self.y, self.radius = None, None, None


class EffectFilter:
    frequency = None

    def __init__(self, frequency=1):
        self.frequency = frequency

    def process(self, surface, tick_count):
        if tick_count % self.frequency:
            return surface
        return self.filter(surface)

    def filter(self, surface):
        print("parent tld")
        return surface


class BlurFilter(EffectFilter):
    def filter(self, surface):
        return cv2.GaussianBlur(surface, (9, 9), cv2.BORDER_DEFAULT)


class FadeFilter(EffectFilter):
    def filter(self, surface):
        # there has to be a better way, for now this works
        # have to cast to signed value to prevent wrap around
        # ret = cv2.subtract(surface, 10)
        ret = np.clip(np.array(surface, dtype=np.int16) - 5, 0, 255)
        return np.array(ret, dtype=np.uint8)


# once we can initialize w/ opts, this will be a generic move(or transpose) filter
class MoveDownFilter(EffectFilter):
    def filter(self, surface):
        height, width = surface.shape[:2]
        # T = np.float32([[1, 0, 0], [0, 1, 1]])
        # return cv2.warpAffine(surface, T, (width, height))

        # this method is quite a bit faster!
        # to shift two down:
        ret = np.roll(surface, 4, 0)
        # to shift one down:
        # ret = np.roll(surface, 1, 1)

        # leave this line out of you want to wrap around
        # otherwise, this will clear out the lines that wrapped
        # ret[[0],:] = 0
        return ret


class AirDraw:
    # move these to parent class
    # state
    running = False
    tick_count = 0
    cap = None
    status = ""
    canvas = None
    trackers = []
    postProcessors = []

    # options
    showMask = True
    showCanvas = True
    showFeed = True

    timers = None

    def __init__(self):
        cv2.destroyAllWindows()
        cv2.waitKey(30)

    def __str__(self):
        return self.timers

    def reset(self):
        print("resetting", flush=True)
        self.timers = TimeKeeper()
        self.trackers = [
            Tracker(
                TrackingColor(
                    bgrToHsv(BLUE), threshold=15, saturationRange=(80, 255), valueRange=(80, 255)
                ),
                "blue",
            ),
            # #Tracker(TrackingColor(GREEN, threshold=10, saturationRange=(60,100), valueRange=(50,80)), 'green'),
            # #Tracker(TrackingColor(WHITE, threshold=30, saturationRange=(0,80), valueRange=(60,120)), 'white'),
            Tracker(
                TrackingColor(
                    bgrToHsv(YELLOW),
                    threshold=10,
                    saturationRange=(100, 255),
                    valueRange=(125, 255),
                ),
                "yellow",
            ),
            Tracker(
                TrackingColor(
                    bgrToHsv(RED), threshold=4, saturationRange=(100, 255), valueRange=(100, 255)
                ),
                "red",
            ),
            # #Tracker(TrackingColor(ORANGE, threshold=4, saturationRange=(100,255), valueRange=(100,255)), 'orange')
        ]

        self.cap = cv2.VideoCapture(0)

        self.postProcessors = [MoveDownFilter(1), BlurFilter(1), FadeFilter(1)]
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 64)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 40)

        camwidth = int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        camheight = int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        self.canvas = np.zeros((camheight, camwidth, 3), np.uint8)

        print("initializing canvas", flush=True)

    def start(self):
        if not self.running:
            print("starting", flush=True)
            self.cleanup()
            self.running = True
            self.reset()
            return
        print("already running", flush=True)

    def stop(self):
        print("stopping", flush=True)
        self.running = False
        self.cleanup()

    # see for example on enforcing an fps
    # http://code.activestate.com/recipes/579053-high-precision-fps/
    def tick(self):
        if self.running:
            self.tick_count = self.tick_count + 1
            self.timers.start("loop")
            self.loop()
            self.timers.stop("loop")
        else:
            print("tick called on non-running thread", flush=True)

    def cleanup(self):
        print("running cleanup", flush=True)
        cv2.destroyAllWindows()
        print("waiting", flush=True)
        # k = cv2.waitKey(3000) & 0xff
        cv2.waitKey(10)
        if self.cap:
            print("releasing camera", flush=True)
            result = self.cap.release()
            print(result, flush=True)
            print("released", flush=True)

    def getStatus(self):
        return self.status

    def loop(self):
        if not self.cap:
            print("no capture device!", flush=True)
            return
        if not self.running:
            print("cannot loop when not running", flush=True)
            return
        self.timers.start("capture")
        ret, frame = self.cap.read()
        # frame = cv2.resize(frame, (160, 120))
        frame = cv2.flip(frame, 1)
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        self.timers.stop("capture")
        self.timers.start("trackers")
        for tracker in self.trackers:
            tracker.update(hsv)

            if self.showMask:
                cv2.imshow(tracker.name, tracker.colorMask)

            # draw a circle on the feed around the detected colors
            if tracker.x and tracker.y and tracker.radius:
                # ok this is weird, for some reason there are floats involved
                if self.showFeed:
                    cv2.circle(
                        frame,
                        (int(tracker.x), int(tracker.y)),
                        int(tracker.radius),
                        tracker.trackingColor.bgr,
                        1,
                    )
                cv2.circle(
                    self.canvas,
                    (int(tracker.x), int(tracker.y)),
                    int(tracker.radius),
                    tracker.trackingColor.bgr,
                    -1,
                )
        self.timers.stop("trackers")
        self.timers.start("post-process")
        for postProcessor in self.postProcessors:
            self.canvas = postProcessor.process(self.canvas, self.tick_count)
        self.timers.stop("post-process")
        if self.showCanvas:
            cv2.imshow("Canvas", self.canvas)
            cv2.waitKey(10) & 0xFF

        if self.showFeed:
            cv2.imshow("Feed", frame)
            cv2.waitKey(10) & 0xFF

def main():
    outputSize = (16, 40)
    effect = AirDraw()
    effect.showCanvas = False
    effect.start()
    while effect.running:
        effect.tick()
        outputSurface = cv2.resize(effect.canvas, outputSize)
        cv2.imshow("Matrix Scale", outputSurface)
        # cv2.imshow("Canvas", effect.canvas)
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            effect.stop()

        if not effect.tick_count % 400:
            print(effect.timers.get("loop"))

def debug():
#    cap = cv2.VideoCapture(0)
#    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 64)
#    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 40)
#    _, v = cap.read()
# originalBGR = v[0][0]
    originalBGR = (255, 75, 0)
    print("originalBGR", originalBGR)
    tmp = np.zeros((400, 640, 3), np.uint8)
    tmp[:] = originalBGR
    cv2.imshow("original BGR", tmp)

    hsv = bgrToHsv(originalBGR)
    print("hsv", hsv)
    tmp2 = np.zeros((400, 640, 3), np.uint8)
    tmp2[:] = hsv
    cv2.imshow("hsv", tmp)

    newBGR = hsvToBgr(hsv)
    print("newBGR", newBGR)
    tmp3 = np.zeros((400, 640, 3), np.uint8)
    tmp3[:] = newBGR
    cv2.imshow("newBGR", tmp3)

    while True:
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            break



    #v = cv2.cvtColor(v, cv2.COLOR_BGR2HSV)
    #print(v[0][0])
    #cap.release()
    # main()
    #bgrColor = originalBGR
    #print('#### bgr to hsv: ', bgrColor, ' --> ', bgrToHsv(bgrColor))
    #hsvColor = (90, 0.1, 0.3)
    #print('#### hsv to bgr: ', hsvColor, ' --> ', hsvToBgr(hsvColor))

if __name__ == "__main__":
    main()
