# Copyright 2018 DT42
#
# This file is part of BerryNet.
#
# BerryNet is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# BerryNet is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with BerryNet.  If not, see <http://www.gnu.org/licenses/>.

"""Utility Functions.
"""

import math

import cv2

from berrynet.comm import payload


def generate_class_color(class_num=20):
    """Generate a RGB color set based on given class number.

    Args:
        class_num: Default is VOC dataset class number.

    Returns:
        A tuple containing RGB colors.
    """
    colors = [(1, 0, 1), (0, 0, 1), (0, 1, 1),
              (0, 1, 0), (1, 1, 0), (1, 0, 0)]
    const = 1234567  # only for offset calculation

    colorset = []
    for cls_i in range(class_num):
        offset = cls_i * const % class_num

        ratio = (float(offset) / class_num) * (len(colors) - 1)
        i = math.floor(ratio)
        j = math.ceil(ratio)
        ratio -= i

        rgb = []
        for ch_i in range(3):
            r = (1 - ratio) * colors[i][ch_i] + ratio * colors[j][ch_i]
            rgb.append(math.ceil(r * 255))
        colorset.append(tuple(rgb[::-1]))
    return tuple(colorset)


def draw_bb(bgr_nparr, infres, class_colors, labels):
    """Draw bounding boxes on an image.

    Args:
        bgr_nparr: image data in numpy array format
        infres: Darkflow inference results
        class_colors: Bounding box color candidates, list of RGB tuples.

    Returens:
        Generalized result whose image data is drew w/ bounding boxes.
    """
    for res in infres['annotations']:
        left = int(res['left'])
        top = int(res['top'])
        right = int(res['right'])
        bottom = int(res['bottom'])
        label = res['label']
        color = class_colors[labels.index(label)]
        confidence = res['confidence']
        imgHeight, imgWidth, _ = bgr_nparr.shape
        thick = int((imgHeight + imgWidth) // 300)

        cv2.rectangle(bgr_nparr,(left, top), (right, bottom), color, thick)
        cv2.putText(bgr_nparr, label, (left, top - 12), 0, 1e-3 * imgHeight,
            color, thick//3)
    #cv2.imwrite('prediction.jpg', bgr_nparr)
    infres['bytes'] = payload.stringify_jpg(
                                    cv2.imencode('.jpg', bgr_nparr)[1])
    return infres


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
        if 'track_id' in anno.keys():
            label = 'ID:{} {}'.format(anno['track_id'], anno['label'])
        else:
            label = anno['label']
        label_text = '{} ({} %)'.format(label,
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


def draw_label(bgr_nparr, infres, class_color, save_image_path=None):
    """Draw bounding boxes on an image.

    Args:
        bgr_nparr: image data in numpy array format
        infres: Inference results followed generic format specification.
        class_color: Label color, a RGB tuple.

    Returens:
        Generalized result whose image data is drew w/ labels.
    """
    left = 0
    top = 0
    for res in infres['annotations']:
        imgHeight, imgWidth, _ = bgr_nparr.shape
        thick = int((imgHeight + imgWidth) // 300)

        # putText can not handle newline char yet,
        # so we have to put multiple texts manually.
        cv2.putText(bgr_nparr,
                    '{0}: {1}'.format(res['label'], res['confidence']),
                    (left + 10, top + 20),  # bottom-left corner of text
                    0,                      # fontFace
                    1e-3 * imgHeight,       # fontScale
                    class_color,
                    thick // 3)
        top += 20
    infres['bytes'] = payload.stringify_jpg(
                                    cv2.imencode('.jpg', bgr_nparr)[1])

    if save_image_path:
        cv2.imwrite(save_image_path, bgr_nparr)

    return infres
