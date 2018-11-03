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

"""Movidius classification inference engine.
"""

from __future__ import print_function

from berrynet.engine import DLEngine
from berrynet.engine import movidius as mv


class MovidiusEngine(DLEngine):
    def __init__(self, model, label):
        super(MovidiusEngine, self).__init__()
        self.mvng = mv.MovidiusNeuralGraph(model, label)

    def process_input(self, tensor):
        return mv.process_inceptionv3_input(tensor)

    def inference(self, tensor):
        return self.mvng.inference(tensor)

    def process_output(self, output):
        return mv.process_inceptionv3_output(
                   output,
                   self.mvng.get_labels())

    def save_cache(self):
        with open(self.cache['model_output_filepath'], 'w') as f:
            for i in self.cache['model_output']:
                print("%s (score = %.5f)" % (i[0], i[1]), file=f)


class MovidiusMobileNetSSDEngine(DLEngine):
    def __init__(self, model, label):
        super(MovidiusMobileNetSSDEngine, self).__init__()
        self.mvng = mv.MovidiusNeuralGraph(model, label)
        self.labels = self.mvng.get_labels()
        self.classes = len(self.labels)

    def process_input(self, tensor):
        self.img_w = tensor.shape[1]
        self.img_h = tensor.shape[0]
        return mv.process_mobilenetssd_input(tensor)

    def inference(self, tensor):
        return self.mvng.inference(tensor)

    def process_output(self, output):
        return mv.process_mobilenetssd_output(
                   output,
                   self.img_w,
                   self.img_h,
                   self.mvng.get_labels())
