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

        btn = tkinter.Button(self.root, text="Calibrate", command=self.takeSample)
        btn.pack(side="bottom", fill="both", expand="yes", padx=10, pady=10)

        # c1 = tkinter.IntVar()
        # tkinter.Checkbutton(self.root, text="Color 1", variable=c1).place(x=320, y=20)
        # c2 = tkinter.IntVar()
        # tkinter.Checkbutton(self.root, text="Color 2", variable=c2).place(x=320, y=45)
        # c3 = tkinter.IntVar()
        # tkinter.Checkbutton(self.root, text="Color 2", variable=c3).place(x=320, y=70)

        # self.hueSlider = tkinter.Scale(self.root, from_=0, to=100, orient="horizontal") #, command=self.updateSliders)
        # self.hueSlider.place(x=340, y=20)
        # self.hueSlider.pack()
        # w.get() to query
        self.colorButton = tkinter.Button(
            self.root, text="Change Color", command=self.changeTrackingColor
        )
        self.colorButton.place(x=320, y=20)

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
        print("hsv before",self.trackers[0].trackingColor.hsv)
        self.trackers[0].trackingColor.bgr = self.trackingColor
        print("hsv after", self.trackers[0].trackingColor.hsv)

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
                    #print( self.trackers[0].trackingColor.hsv)
                    #frame = self.trackers[0].colorMask
                    frame = cv2.bitwise_and(frame,frame,mask=self.trackers[0].colorMask)
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
                    self.capturePanel.pack(side="left", padx=10, pady=10)
                else:
                    self.capturePanel.configure(image=image)
                self.capturePanel.image = image

        except RuntimeError:
            print("oops")

    def takeSample(self):
        print("beep beep")

    def mouseRGB(event,x,y,flags,param):
        if event == cv2.EVENT_LBUTTONDOWN: #checks mouse left button down condition
            colorsB = frame[y,x,0]
            colorsG = frame[y,x,1]
            colorsR = frame[y,x,2]
            colors = frame[y,x]
            print("Red: ",colorsR)
            print("Green: ",colorsG)
            print("Blue: ",colorsB)
            print("BRG Format: ",colors)
            print("Coordinates of pixel: X: ",x,"Y: ",y)

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
