import argparse
import json
import logging

from os.path import join as pjoin

import cv2

from dyda.pipelines import pipeline as dydapl


logger = logging.getLogger('launcher')


class BerryNetPipelineLauncher(object):
    def __init__(self, config, dyda_config_path='',
                 output_dirpath='', verbosity=0, benchmark=False,
                 lab_flag=False):
        self.pipeline = dydapl.Pipeline(
            config,
            dyda_config_path=dyda_config_path,
            parent_result_folder=output_dirpath,
            verbosity=verbosity,
            lab_flag=lab_flag)
        self.benchmark = benchmark

    def run(self, bitmap, meta={}, base_name=None):
        """Run pipeline.

        Args:
            bitmap: Image data in BGR format (numpy array)

        Returns:
            Dictionary with contents or empty list.
        """
        self.pipeline.run(bitmap,
                          external_meta=meta,
                          benchmark=self.benchmark,
                          base_name=base_name)
        try:
            # You can get pipeline output(s) in two ways:
            #
            # 1. Simple (and single) output from pipeline.output.
            #    - 100% available
            #    - Data type is dynamic (it might be a JSON object, an image, etc.)
            #
            # 2. Multiple outputs from components defined in pipeline config.
            #    - Currently it is used in the scenario that
            #      you want to have JSON result and image simultaneously.
            #    - final_json_output and final_img_output are component name,
            #      not component types. We are considering to define them as standard.
            if all(key in self.pipeline.pipeline.keys()
                   for key in ['final_json_output', 'final_img_output']):
                logger.debug('Pipeline output type: multiple (launcher_berrynet)')
                output = {
                    'annotations': self.pipeline.pipeline['final_json_output']['output']['annotations'],
                    'bytes': self.pipeline.pipeline['final_img_output']['output']
                }
            else:
                logger.debug('Pipeline output type: simple (launcher_berrynet)')
                output = self.pipeline.output
        except Exception as e:
            logger.critical(e)
        return output


def get_args(argv=None):
    """ Prepare auguments for running the script. """

    parser = argparse.ArgumentParser(
        description='Pipeline.'
    )
    parser.add_argument(
        '-i', '--input',
        type=str,
        default=(
            '/home/shared/customer_data/acti/201711-ACTi-A/'
            '20171207_recording/acti_2017-12-07-1701/frame'),
        help='Input folder for ')
    parser.add_argument(
        '-o', '--output',
        type=str,
        default='/home/shared/DT42/test_data/'
        'test_auto_labeler_with_tracker/results/',
        help='Output folder for output_metadata')
    parser.add_argument(
        '--lab_flag',
        dest='lab_flag',
        action='store_true',
        default=False,
        help='True to enable related lab process.'
    )
    parser.add_argument(
        '-p', '--pipeline_config',
        type=str,
        default='/home/lab/dyda/pipeline.config',
        help='File contains the definition of pipeline application.'
    )
    parser.add_argument(
        '-t', '--dyda_config',
        type=str,
        default='',
        help='File contains the component definitions.'
    )
    parser.add_argument(
        "-v", "--verbosity",
        action="count",
        default=0,
        help="increase output verbosity"
    )
    return parser.parse_args(argv)


def main():
    """ Example for testing pipeline. """

    args = get_args()

    log_level = logging.WARNING
    if args.verbosity == 1:
        log_level = logging.INFO
    elif args.verbosity >= 2:
        log_level = logging.DEBUG
    formatter = logging.Formatter('[launcher] %(levelname)s %(message)s')
    console = logging.StreamHandler()
    console.setFormatter(formatter)
    logger.setLevel(log_level)
    logger.addHandler(console)

    logger.debug('lab_flag is %r' % args.lab_flag)

    pipeline = BerryNetPipelineLauncher(
        config=args.pipeline_config,
        dyda_config_path=args.dyda_config,
        output_dirpath=args.output,
        verbosity=args.verbosity,
        lab_flag=args.lab_flag
    )

    logger.debug('Running Reader and Selector for frames')
    source_dirpath = args.input
    input_number = 100
    for i in range(input_number):
        input_data = pjoin(source_dirpath, '00000{}.png'.format(570 + i))
        ext_data = cv2.imread(input_data)

        output_data = pipeline.run(ext_data)
        logger.debug('===== frame #{} ====='.format(i))
        logger.debug('input: {}'.format(input_data))
        if (len(output_data) > 0):
            with open('output_{}.json'.format(i), 'w') as f:
                json.dump(output_data, f, indent=4)


if __name__ == "__main__":
    main()
