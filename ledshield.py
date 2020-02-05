#!/usr/bin/env python
import time
from artnetmatrix import (
    ArtNetMatrix,
    START_PIXEL_BOTTOM,
    START_PIXEL_LEFT,
    DIRECTION_COLUMNS,
    LAYOUT_SNAKE,
    COLOR_ORDER_RGB,
)
from effects import airdraw

OPTS = START_PIXEL_BOTTOM | START_PIXEL_LEFT | DIRECTION_COLUMNS | LAYOUT_SNAKE

import cv2
import numpy as np
from collections import deque


def blit(dest, src, loc):
    pos = [i if i >= 0 else None for i in loc]
    neg = [-i if i < 0 else None for i in loc]
    target = dest[tuple([slice(i, None) for i in pos])]
    src = src[tuple([slice(i, j) for i, j in zip(neg, target.shape)])]
    target[tuple([slice(None, i) for i in src.shape])] = src
    return dest


def main():
    matrix = ArtNetMatrix((16, 40), OPTS, COLOR_ORDER_RGB)
    matrix.fill((255, 0, 0))
    # matrix.fill((255,255,255))
    # matrix.fill((255,255,255))
    for i in range(128, -1, -1):
        matrix.fill((i, i, 255))
        # img = cv2.cvtColor(matrix.surface.astype('uint8'), cv2.COLOR_BGR2RGB)
        matrix.update()
        img = matrix.surface
        # print(img[0][0])
        cv2.imshow("shield", cv2.resize(img, (320, 800)))
        k = cv2.waitKey(1) & 0xFF
        if k == 27:
            cv2.destroyAllWindows()
            return
        # time.sleep(.1)
    print("done")
    while 1:
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            break

    cv2.destroyAllWindows()


def testopencv2():
    print("initializing matrix")
    SHIELD_WIDTH = 16
    SHIELD_HEIGHT = 40
    matrix = ArtNetMatrix((SHIELD_WIDTH, SHIELD_HEIGHT), OPTS, COLOR_ORDER_RGB)
    print("initializing camera")
    cap = cv2.VideoCapture(0)
    camwidth = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    capheight = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    fgbg = cv2.createBackgroundSubtractorMOG2(
        history=12000, varThreshold=32, detectShadows=False
    )
    while 1:
        ret, frame = cap.read()
        # fgmask = fgbg.apply(firstFrame)
        fgmask = fgbg.apply(frame)

        outputFrame = cv2.bitwise_and(frame, frame, mask=fgmask)
        outputFrame = cv2.resize(outputFrame, (16, 40), fx=0, fy=0)

        # cv2.imshow('shield',cv2.resize(blit(matrix.surface, outputFrame, (0,0)),(320,800), interpolation=cv2.INTER_NEAREST))
        # matrix.update()
        # just the mask
        # cv2.imshow('frame',fgmask)
        # color image, bg removed via mask
        # cv2.imshow('frame', outputFrame)
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


def testopencv3():
    cap = cv2.VideoCapture(0)
    while 1:
        ret, frame = cap.read()
        imgray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        ret, thresh = cv2.threshold(imgray, 127, 255, 0)
        # im2, contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours, hierarchy = cv2.findContours(
            thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE
        )
        img = frame  # cv2.cvtColor(imgray, cv2.COLOR_BGR2GRAY)
        img2 = cv2.drawContours(img, contours, -1, (0, 255, 0), 3)
        cv2.imshow("frame", img2)
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


def testopencv3():
    cap = cv2.VideoCapture(0)
    fgbg = cv2.createBackgroundSubtractorMOG2(
        history=500, varThreshold=16, detectShadows=False
    )
    i = 0
    ARC_THRESHOLD = 10
    while 1:
        i += 1
        ret, frame = cap.read()
        fgmask = fgbg.apply(frame)
        contours, hierarchy = cv2.findContours(
            fgmask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE
        )
        # defects = cv2.convexityDefects(contours,hull)
        img = frame
        cv2.drawContours(img, contours, -1, (0, 255, 0), 3)
        # indexes of hullpoints w/ defects
        # hullIndexes = [cv2.convexHull(contour, returnPoints=False) for contour in contours]
        # print(hullIndexes)
        hulls = [
            cv2.convexHull(contour)
            for contour in contours
            if cv2.arcLength(contour, True) > ARC_THRESHOLD
        ]
        # hulls = [cv2.convexHull(contour) for contour in contours]
        cv2.drawContours(img, hulls, -1, (255, 0, 0), 3)
        cv2.imshow("frame", cv2.flip(img, 1))
        # cv2.imshow('frame',cv2.flip(fgmask, 1))
        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            break

    cap.release()
    cv2.destroyAllWindows()


def testairdraw():
    print("starting air draw effect")
    outputSize = (16, 40)
    matrix = ArtNetMatrix((16, 40), OPTS, COLOR_ORDER_RGB)
    effect = airdraw.AirDraw()
    effect.showCanvas = False
    effect.start()
    tick_samples = deque()
    current_fps = 0
    MAX_SAMPLES = 100
    while effect.running:
        start_time = time.time()
        effect.tick()
        outputSurface = cv2.resize(effect.canvas, outputSize)
        cv2.imshow("Matrix Scale", outputSurface)
        # cv2.imshow("Canvas", effect.canvas)

        # matrix.surface = outputSurface
        blit(matrix.surface, outputSurface, (0, 0))
        matrix.update()

        k = cv2.waitKey(30) & 0xFF
        if k == 27:
            effect.stop()
        end_time = time.time()
        tick_samples.append(end_time - start_time)
        if len(tick_samples) > MAX_SAMPLES:
            tick_samples.popleft()
            # current_fps = statistics.mean(tick_samples)
            current_fps = MAX_SAMPLES / sum(tick_samples)
            if effect.tick_count % 400:
                print(current_fps)


if __name__ == "__main__":
    print("starting air draw effect")
    # main()
    # testopencv()
    # testopencv2()
    # testopencv3()
    testairdraw()
