import unittest

import cv2

from berrynet.engine.tensorflow_engine import TensorFlowEngine


class TestTensorFlowEngine(unittest.TestCase):
    def test_engine(self):
        model = 'berrynet/engine/inception_v3_2016_08_28_frozen.pb'
        label = 'berrynet/engine/imagenet_slim_labels.txt'
        jpg_filepath = 'berrynet/engine/grace_hopper.jpg'
        input_layer = 'input:0'
        output_layer = 'InceptionV3/Predictions/Reshape_1:0'

        tfe = TensorFlowEngine(model, label, input_layer, output_layer)
        tfe.create()
        rgb_array = cv2.cvtColor(
            cv2.imread(jpg_filepath),
            cv2.COLOR_BGR2RGB)
        tfe.process_output(tfe.inference(tfe.process_input(rgb_array)))
        #self.assertEqual('foo'.upper(), 'FOO')

    #def test_isupper(self):
    #    self.assertTrue('FOO'.isupper())
    #    self.assertFalse('Foo'.isupper())

    #def test_split(self):
    #    s = 'hello world'
    #    self.assertEqual(s.split(), ['hello', 'world'])
    #    # check that s.split fails when the separator is not a string
    #    with self.assertRaises(TypeError):
    #        s.split(2)


if __name__ == '__main__':
    unittest.main()
