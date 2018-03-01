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

"""
Deep learning engine template provides unified interfaces for
different backends (e.g. TensorFlow, Caffe2, etc.)
"""

class DLEngine(object):
    def __init__(self):
        self.model_input_cache = []
        self.model_output_cache = []
        self.cache = {
            'model_input': [],
            'model_output': '',
            'model_output_filepath': ''
        }

    def create(self):
        # Workaround to posepone TensorFlow initialization.
        # If TF is initialized in __init__, and pass an engine instance
        # to engine service, TF session will stuck in run().
        pass

    def process_input(self, tensor):
        return tensor

    def inference(self, tensor):
        output = None
        return output

    def process_output(self, output):
        return output

    def cache_data(self, key, value):
        self.cache[key] = value

    def save_cache(self):
        with open(self.cache['model_output_filepath'], 'w') as f:
            f.write(str(self.cache['model_output']))
