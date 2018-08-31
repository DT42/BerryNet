import random
import sys
import time

from queue import Queue
from threading import Lock
from threading import Thread
from time import sleep

import cv2

from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *


cam = cv2.VideoCapture(0)
#cam = cv2.VideoCapture('/home/pi/codes/MobileNet-SSD/peoplecar_video_input_01.mp4')
#cam = cv2.VideoCapture('/home/pi/codes/MobileNet-SSD/20180411_01.mp4')

if cam.isOpened() != True:
    print("Camera/Movie Open Error!!!")
    quit()

windowWidth = 320
windowHeight = 240
cam.set(cv2.CAP_PROP_FRAME_WIDTH, windowWidth)
cam.set(cv2.CAP_PROP_FRAME_HEIGHT, windowHeight)

lock = Lock()
frameBuffer = []
results = Queue()
lastresults = None
devices = 1


def gl_draw_fbimage(rgbimg):
    h, w = rgbimg.shape[:2]

    glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, w, h, 0, GL_RGB, GL_UNSIGNED_BYTE, rgbimg)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glColor3f(1.0, 1.0, 1.0)
    glEnable(GL_TEXTURE_2D)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
    glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
    glBegin(GL_QUADS)
    glTexCoord2d(0.0, 1.0)
    glVertex3d(-1.0, -1.0,  0.0)
    glTexCoord2d(1.0, 1.0)
    glVertex3d( 1.0, -1.0,  0.0)
    glTexCoord2d(1.0, 0.0)
    glVertex3d( 1.0,  1.0,  0.0)
    glTexCoord2d(0.0, 0.0)
    glVertex3d(-1.0,  1.0,  0.0)
    glEnd()
    glFlush()
    glutSwapBuffers()


def init():
    glClearColor(0.7, 0.7, 0.7, 0.7)


def idle():
    glutPostRedisplay()


def keyboard(key, x, y):
    key = key.decode('utf-8')
    if key == 'q':
        lock.acquire()
        while len(frameBuffer) > 0:
            frameBuffer.pop()
        lock.release()
        print("\n\nFinished\n\n")
        sys.exit()


def camThread():
    """Draw last updated result on image.
    """
    global lastresults

    s, img = cam.read()
    if not s:
        print("Could not get frame")
        return 0

    lock.acquire()
    if len(frameBuffer)>10:
        for i in range(10):
            del frameBuffer[0]
    frameBuffer.append(img)
    print('camThread appends fb')
    lock.release()
    res = None

    if not results.empty():
        print('results is not empty')
        res = results.get(False)
        img = overlay_on_image(img, res)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        gl_draw_fbimage(img)
        lastresults = res
    else:
        print('results is empty')
        imdraw = overlay_on_image(img, lastresults)
        imdraw = cv2.cvtColor(imdraw, cv2.COLOR_BGR2RGB)
        gl_draw_fbimage(imdraw)


def inferencer(results, lock, frameBuffer):
    print('inferencer is created')

    failure = 0
    #sleep(3)
    #while failure < 100:
    while True:
        lock.acquire()
        if len(frameBuffer) == 0:
            lock.release()
            failure += 1
            print('empty framebuffer')
            continue

        img = frameBuffer[-1].copy()
        del frameBuffer[-1]
        print('inferencer pops fb')
        failure = 0
        lock.release()

        now = time.time()
        out = [
            {
                'label': 'hello',
                'confidence': 0.42,
                'left': random.randint(50, 60),
                'top': random.randint(50, 60),
                'right': random.randint(300, 400),
                'bottom': random.randint(300, 400)
            }
        ]
        results.put(out)
        print("elapsedtime = ", time.time() - now)
    print('Too many failures, inferencer is terminated')


def draw_box(image, annotations):
    """Draw information of annotations onto image.

    Args:
        image: Image nparray.
        annotations: List of detected object information.

    Returns: Image nparray containing object information on it.
    """
    print('draw_box, annotations: {}'.format(annotations))
    img = image.copy()

    for anno in annotations:
        # draw bounding box
        box_color = (0, 0, 255)
        box_thickness = 1
        cv2.rectangle(img,
                      (anno['left'], anno['top']),
                      (anno['right'], anno['bottom']),
                      box_color,
                      box_thickness)

        # draw label
        label_background_color = box_color
        label_text_color = (255, 255, 255)
        label_text = '{} ({} %)'.format(anno['label'],
                                        int(anno['confidence'] * 100))
        label_size = cv2.getTextSize(label_text,
                                     cv2.FONT_HERSHEY_SIMPLEX,
                                     0.5,
                                     1)[0]
        label_left = anno['left']
        label_top = anno['top'] - label_size[1]
        if (label_top < 1):
            label_top = 1
        label_right = label_left + label_size[0]
        label_bottom = label_top + label_size[1]
        cv2.rectangle(img,
                      (label_left - 1, label_top - 1),
                      (label_right + 1, label_bottom + 1),
                      label_background_color,
                      -1)
        cv2.putText(img,
                    label_text,
                    (label_left, label_bottom),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    label_text_color,
                    1)
    return img


def overlay_on_image(display_image, object_info):
    """Modulized version of overlay_on_image function
    """
    if isinstance(object_info, type(None)):
        print('WARNING: object info is None')
        return display_image

    return draw_box(display_image, object_info)


def main():
    glutInitWindowPosition(0, 0)
    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_RGBA | GLUT_DOUBLE)
    glutCreateWindow("Framebuffer I/O demo, q to quit")
    #glutFullScreen()
    glutDisplayFunc(camThread)
    glutKeyboardFunc(keyboard)
    init()
    glutIdleFunc(idle)

    threads = []
    for devnum in range(devices):
        t = Thread(target=inferencer, args=(results, lock, frameBuffer))
        t.start()
        threads.append(t)

    glutMainLoop()


if __name__ == '__main__':
    main()
