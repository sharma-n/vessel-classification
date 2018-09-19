# Copyright 2017 Google Inc. and Skytruth Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import absolute_import
import argparse
import logging
import os
import sys
import importlib
import tensorflow as tf
from pkg_resources import resource_filename
from . import utility

def main(args):
    logging.getLogger().setLevel(logging.DEBUG)
    tf.logging.set_verbosity(tf.logging.DEBUG)

    logging.info("Running with Tensorflow version: %s", tf.__version__)

    logging.info("Loading model: %s", args.model_name)

    module = "classification.models.{}".format(args.model_name)
    try:
        Model = importlib.import_module(module).Model
    except:
        logging.fatal("Could not load model: {}".format(module))
        raise

    metadata_file = os.path.abspath(
        resource_filename('classification.data', args.metadata_file))
    if not os.path.exists(metadata_file):
        logging.fatal("Could not find metadata file: %s.", metadata_file)
        sys.exit(-1)

    fishing_range_file = os.path.abspath(
        resource_filename('classification.data', args.fishing_ranges_file))
    if not os.path.exists(fishing_range_file):
        logging.fatal("Could not find fishing range file: %s.",
                      fishing_range_file)
        sys.exit(-1)

    fishing_ranges = utility.read_fishing_ranges(fishing_range_file)

    all_available_mmsis = utility.find_available_mmsis(args.root_feature_path)

    vessel_metadata = Model.read_metadata(
        all_available_mmsis, metadata_file,
        fishing_ranges, int(args.fishing_range_training_upweight))

    feature_dimensions = int(args.feature_dimensions)
    chosen_model = Model(feature_dimensions, vessel_metadata, args.metrics)

    train_input_fn = chosen_model.make_training_input_fn(args.root_feature_path, args.num_parallel_readers)
    test_input_fn = chosen_model.make_test_input_fn(args.root_feature_path, args.num_parallel_readers)
    estimator = chosen_model.make_estimator(args.training_output_path)
    train_spec = tf.estimator.TrainSpec(
                    input_fn=train_input_fn, 
                    max_steps=chosen_model.number_of_steps)
    eval_spec = tf.estimator.EvalSpec(
                    input_fn=test_input_fn,
                    start_delay_secs=120,
                    throttle_secs=300
                    )

    tf.estimator.train_and_evaluate(estimator, train_spec, eval_spec)



def parse_args():
    """ Parses command-line arguments for training."""
    argparser = argparse.ArgumentParser('Train fishing classification model.')

    argparser.add_argument('model_name')

    argparser.add_argument(
        '--root_feature_path',
        required=True,
        help='The root path to the vessel movement feature directories.')

    argparser.add_argument(
        '--training_output_path',
        required=True,
        help='The working path for model statistics and checkpoints.')

    argparser.add_argument(
        '--feature_dimensions',
        required=True,
        help='The number of dimensions of a classification feature.')

    argparser.add_argument(
        '--fishing_range_training_upweight',
        default=1.0,
        help='The amount to upweight vessels that have fishing ranges when training.')

    argparser.add_argument('--metadata_file', help='Path to metadata.')

    argparser.add_argument(
        '--fishing_ranges_file', help='Path to fishing range file.')

    argparser.add_argument(
        '--metrics',
        default='all',
        help='How many metrics to dump ["all" | "minimal"]')

    argparser.add_argument(
        '--num_parallel_readers',
        default=32, type=int,
        help='How many parallel readers to employ reading data')

    return argparser.parse_args()


if __name__ == '__main__':
    args = parse_args()
    main(args)