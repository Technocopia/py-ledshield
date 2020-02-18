import cv2
import threading
import tkinter
from tkinter import colorchooser
import imutils
from PIL import Image, ImageTk

from airdraw import TrackingColor, Tracker, BLUE, bgrToHsv

MARKER_THICKNESS = 2
# Blue color in BGR
MARKER_COLOR = (255, 0, 0)
MARKER_SIZE = [40, 40]


class CalibrationApp:
    def __init__(self):
        self.root = tkinter.Tk()
        self.capturePanel = None
        self.palettePanel = None

        self.hSlider = tkinter.Scale(
            self.root,
            from_=0,
            to=179,
            orient="horizontal",
            length=200,
            label="Hue",
            command=self.handleColorSliderUpdate,
        )
        self.hSlider.grid(row=0, column=1)
        self.hThreshSlider = tkinter.Scale(
            self.root,
            from_=0,
            to=20,
            orient="horizontal",
            length=200,
            label="(Threshold)",
            command=self.handleColorSliderUpdate,
        )
        self.hThreshSlider.grid(row=0, column=2)

        self.sSliderMin = tkinter.Scale(
            self.root,
            from_=0,
            to=255,
            orient="horizontal",
            length=200,
            label="Value (Min)",
            command=self.handleColorSliderUpdate,
        )
        self.sSliderMin.grid(row=2, column=1)
        self.sSliderMax = tkinter.Scale(
            self.root,
            from_=0,
            to=255,
            orient="horizontal",
            length=200,
            label="(Max)",
            command=self.handleColorSliderUpdate,
        )
        self.sSliderMax.grid(row=2, column=2)

        self.vSliderMin = tkinter.Scale(
            self.root,
            from_=0,
            to=255,
            orient="horizontal",
            length=200,
            label="Saturation (Min)",
            command=self.handleColorSliderUpdate,
        )
        self.vSliderMin.grid(row=4, column=1)
        self.vSliderMax = tkinter.Scale(
            self.root,
            from_=0,
            to=255,
            orient="horizontal",
            length=200,
            label="(Max)",
            command=self.handleColorSliderUpdate,
        )
        self.vSliderMax.grid(row=4, column=2)

        btn = tkinter.Button(self.root, text="Calibrate", command=self.takeSample)
        btn.grid(row=7, column=0, columnspan=2, padx=10, pady=10)

        self.colorButton = tkinter.Button(
            self.root, text="Change Color", command=self.changeTrackingColor
        )
        # self.colorButton.place(x=320, y=20)
        self.colorButton.grid(row=6, column=1, padx=10, pady=10)

        # set a callback to handle when the window is closed
        self.root.wm_title("AirDraw Calibration")
        self.root.wm_protocol("WM_DELETE_WINDOW", self.onClose)

        cv2.destroyAllWindows()
        cv2.waitKey(30)
        self.cap = cv2.VideoCapture(0)

        self.trackingColor = BLUE

        self.trackers = [
            Tracker(
                TrackingColor(
                    bgrToHsv(self.trackingColor),
                    threshold=15,
                    saturationRange=(80, 255),
                    valueRange=(80, 255),
                ),
                "Tracking Color A",
            ),
        ]

        self.stopEvent = threading.Event()
        self.thread = threading.Thread(target=self.loop, args=())
        self.thread.start()

        self.root.mainloop()

        try:
            self.root.destroy()
        except:
            pass

    # def updateSliders(self, v):
    #    print('v',v)
    #    print('g', self.hueSlider.get())

    def changeTrackingColor(self):
        print("launching chooser")
        b, g, r = self.trackingColor
        clr = colorchooser.askcolor(
            title="select color", initialcolor=(int(r), int(g), int(b))
        )
        #'#%02x%02x%02x' % (r, g, b)
        print("launched!")
        print(clr)
        r, g, b = clr[0]
        print(r, g, b)
        self.trackingColor = (b, g, r)
        print("setting new bgr", self.trackingColor)
        print("hsv before", self.trackers[0].trackingColor.hsv)
        self.trackers[0].trackingColor.bgr = self.trackingColor
        print("hsv after", self.trackers[0].trackingColor.hsv)

        h, s, v = self.trackers[0].trackingColor.hsv
        self.hSlider.set(h)
        self.sSliderMin.set(s)
        self.vSliderMin.set(v)

    def handleColorSliderUpdate(self, _):
        h = self.hSlider.get()
        thresh = self.hThreshSlider.get()

        sMin = self.sSliderMin.get()
        sMax = self.sSliderMax.get()
        sMinNew = min(sMin, sMax)
        sMaxNew = max(sMin, sMax)
        self.sSliderMin.set(sMinNew)
        self.sSliderMax.set(sMaxNew)

        vMin = self.vSliderMin.get()
        vMax = self.vSliderMax.get()
        vMinNew = min(vMin, vMax)
        vMaxNew = max(vMin, vMax)
        self.vSliderMin.set(vMinNew)
        self.vSliderMax.set(vMaxNew)

        self.trackers[0].trackingColor.hsv = [
            h,
            sMinNew + sMaxNew / 2,
            vMinNew + vMaxNew / 2,
        ]
        self.trackers[0].trackingColor.threshold = thresh
        self.trackers[0].trackingColor.saturationRange = (sMinNew, sMaxNew)
        self.trackers[0].trackingColor.valueRange = (vMinNew, vMaxNew)

    def loop(self):
        try:
            while not self.stopEvent.is_set():
                _, frame = self.cap.read()
                frame = cv2.flip(frame, 1)
                frame = imutils.resize(frame, width=300)

                h, w, channels = frame.shape
                x, y = [w / 2, h / 2]
                start_point = (int(x - MARKER_SIZE[0] / 2), int(y - MARKER_SIZE[1] / 2))
                end_point = (int(x + MARKER_SIZE[0] / 2), int(y + MARKER_SIZE[1] / 2))
                frame = cv2.rectangle(
                    frame, start_point, end_point, MARKER_COLOR, MARKER_THICKNESS
                )

                hsvFrame = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
                self.trackers[0].update(hsvFrame)
                if True:  # Show mask
                    # print( self.trackers[0].trackingColor.hsv)
                    # frame = self.trackers[0].colorMask
                    frame = cv2.bitwise_and(
                        frame, frame, mask=self.trackers[0].colorMask
                    )
                # lmain.imgtk = imgtk
                # lmain.configure(image=imgtk)
                # lmain.after(10, show_frame)
                # if the panel is not None, we need to initialize it
                image = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                image = Image.fromarray(image)
                image = ImageTk.PhotoImage(image)

                # if self.palettePanel is None:
                #   self.palettePanel = tkinter.Label(width=200, bg="green")
                #   self.palettePanel.pack(side="right", padx=10, pady=10)

                if self.capturePanel is None:
                    self.capturePanel = tkinter.Label(image=image)
                    # self.capturePanel.pack(side="left", padx=10, pady=10)
                    self.capturePanel.grid(row=0, column=0, rowspan=7, padx=10, pady=10)

                self.capturePanel.configure(image=image)
                self.capturePanel.image = image

        except RuntimeError:
            print("oops")

    def takeSample(self):
        print("beep beep")

    def mouseRGB(event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:  # checks mouse left button down condition
            colorsB = frame[y, x, 0]
            colorsG = frame[y, x, 1]
            colorsR = frame[y, x, 2]
            colors = frame[y, x]
            print("Red: ", colorsR)
            print("Green: ", colorsG)
            print("Blue: ", colorsB)
            print("BRG Format: ", colors)
            print("Coordinates of pixel: X: ", x, "Y: ", y)

    def onClose(self):
        print("[INFO] closing...")
        self.cap.release()
        self.stopEvent.set()
        self.root.quit()


if __name__ == "__main__":
    print("calibrating items for airdraw effect")
    # run()
    app = CalibrationApp()
    print("done")
