"""

$python xmlTotxt.py -n $FOLDER -u $LABELME_USER
 --classes $CLASS_1 $CLASS_2 $CLASS_3...

FOLDER: LabelMe project folder name
LABELME_USER: LabelMe user name
CLASS_i: Class labels defined on LabelMe

"""
import argparse
import logging
import os
import xml.etree.ElementTree as ET

from os.path import join
from shutil import copyfile


def convert(size, in_x, in_y):
    dw = 1./size[0]
    dh = 1./size[1]
    x = (in_x[0] + in_x[1])/2.0
    y = (in_y[0] + in_y[1])/2.0
    w = in_x[1] - in_x[0]
    h = in_y[1] - in_y[0]
    x = x*dw
    w = w*dw
    y = y*dh
    h = h*dh
    return (x, y, w, h)


def convert_annotation(in_dir, out_dir, image_id, out_id, classes):
    in_file = open("%s/%s.xml" % (in_dir, image_id))
    o_file = open(out_dir + "/%s.txt" % out_id, "w")
    tree = ET.parse(in_file)
    root = tree.getroot()
    size = root.find("imagesize")
    h = float(size.find("nrows").text)
    w = float(size.find("ncols").text)

    for obj in root.iter("object"):
        X = []
        Y = []
        cls = obj.find("name").text
        if cls not in classes:
            logging.debug("%s is not in the selected class" % cls)
            continue
        cls_id = classes.index(cls)
        for pt in obj.find("polygon").findall("pt"):
            X.append(float(pt.find("x").text))
            Y.append(float(pt.find("y").text))
        if (len(X) < 2 or len(Y) < 2):
            logging.warning("%s doesn't have sufficient info, ignore" % cls)
            continue
        X = list(set(X))
        X.sort()
        Y = list(set(Y))
        Y.sort()
        bb = convert((w, h), X, Y)
        o_file.write(str(cls_id) + " " + " ".join([str(a) for a in bb]) + "\n")


def find_output_id(out_img_dir, image_id, suffix):
    counter = 0
    out_img_path = join(out_img_dir, image_id + "." + suffix)
    out_id = image_id
    while os.path.exists(out_img_path):
        logging.info("%s exists" % out_img_path)
        counter += 1
        out_id = image_id + "_" + str(counter)
        out_img_path = join(out_img_dir, out_id + "." + suffix)
    return out_id, out_img_path


def main():

    parser = argparse.ArgumentParser(
        description="Simple tool to make the scene image better."
        )
    parser.add_argument(
        "-v", "--verbosity", action="count",
        help="increase output verbosity"
        )
    parser.add_argument(
        "-r", "--root", type=str, default=None,
        help="Specify the root directory (default: PWD)"
        )
    parser.add_argument(
        "-n", "--name", type=str, default="youtube_09",
        help="Specify the name of the original video (default: youtube_09)"
        )
    parser.add_argument(
        "-u", "--user", type=str, default="V",
        help="Specify the username (default: V)"
        )
    parser.add_argument(
        "-o", "--outdir", type=str, default="test2017",
        help="Output dir in root, must end with 2017 (default: test2017)"
        )
    parser.add_argument(
        "--classes", nargs="+", type=str, default=["fighting", "dog"],
        help="Classes to be trained. Default: [fighting, dog]"
        )
    parser.add_argument(
        "-d", "--delete", action="store_true",
        help="Use this option to clean up train.txt"
        )

    args = parser.parse_args()

    log_level = logging.WARNING
    if args.verbosity == 1:
        log_level = logging.INFO
    elif args.verbosity >= 2:
        log_level = logging.DEBUG
    logging.basicConfig(level=log_level,
                        format="[xmlTotxt: %(levelname)s] %(message)s")

    logging.info(args.classes)

    if args.root is None:
        args.root = os.getcwd()
    in_dir = join(args.root, "Annotations", "users",
                  args.user, args.name)
    in_img_dir = join(args.root, "Images", "users",
                      args.user, args.name)
    out_dir = join(args.root, args.outdir, "labels")
    out_img_dir = join(args.root, args.outdir, "JPEGImages")

    if not os.path.exists(out_dir):
        os.makedirs(out_dir)

    if not os.path.exists(out_img_dir):
        os.makedirs(out_img_dir)

    foutput = join(args.root, "train.txt")
    if args.delete:
        output = open(foutput, "w")
    else:
        output = open(foutput, "a")

    for _img_path in os.listdir(in_img_dir):
        img_path = os.path.join(in_img_dir, _img_path)
        suffix = os.path.basename(_img_path).split(".")[1]
        logging.debug("Find %s" % img_path)
        image_id = os.path.basename(_img_path).split(".")[0]
        out_id, out_img_path = find_output_id(out_img_dir, image_id, suffix)
        convert_annotation(in_dir, out_dir, image_id, out_id, args.classes)
        logging.info("Copy %s to %s" % (img_path, out_img_path))
        copyfile(img_path, out_img_path)

        output.write(out_img_path + "\n")


if __name__ == '__main__':
    main()
