# Copyright 2017 DT42
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

"""
DL Model Manager, following the DLModelBox model package
speccification.
"""

from __future__ import print_function

import argparse
import json
import os

from berrynet import logger


class DLModelManager(object):
    def __init__(self):
        self.basedir = '/usr/share/dlmodels'

    def get_model_names(self):
        return os.listdir(self.basedir)

    def get_model_meta(self, modelname):
        meta_filepath = os.path.join(self.basedir, modelname, 'meta.json')
        with open(meta_filepath, 'r') as f:
            meta = json.load(f)
        meta['model'] = os.path.join(self.basedir, modelname, meta['model'])
        meta['label'] = os.path.join(self.basedir, modelname, meta['label'])
        for k, v in meta['config'].items():
            meta['config'][k] = os.path.join(self.basedir, modelname,
                                             meta['config'][k])
        return meta


def parse_args():
    ap = argparse.ArgumentParser()
    ap.add_argument('--modelname',
                    help='Model package name (without version)')
    return vars(ap.parse_args())


if __name__ == '__main__':
    args = parse_args()
    logger.debug('model package name: ', args['modelname'])

    dlmm = DLModelManager()
    for name in dlmm.get_model_names():
        print(dlmm.get_model_meta(name))
