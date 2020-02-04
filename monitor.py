import sys
import cv2
from artnetreceiver import ArtNetReceiver
from artnetmatrix import ArtNetMatrix, START_PIXEL_BOTTOM, START_PIXEL_LEFT, DIRECTION_COLUMNS,LAYOUT_SNAKE, COLOR_ORDER_RGB
OPTS = START_PIXEL_BOTTOM | START_PIXEL_LEFT | DIRECTION_COLUMNS | LAYOUT_SNAKE

if __name__ == "__main__":
    print("artnet listner")
    artnet = ArtNetReceiver(ip="192.168.0.122")
    matrix = ArtNetMatrix((16,40), OPTS, COLOR_ORDER_RGB)
    matrix.setReceiveMode(artnet)

    scale_percent = 1000 # percent of original size
    width = int(16 * scale_percent / 100)
    height = int(40 * scale_percent / 100)
    dim = (width, height)

    while True:
        frame = matrix.receiveFrame()
        #print(frame[0][0][0:2])
        cv2.imshow("Monitor", cv2.resize(frame, dim, interpolation = cv2.INTER_AREA))
        k = cv2.waitKey(10) & 0xff
        if k == 27:
            cv2.destroyAllWindows()
            sys.exit()
    # print(frame)
