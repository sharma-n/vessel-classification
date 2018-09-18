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
import json
from . import abstract_models
from . import layers
from classification import utility
from classification.objectives import (
    FishingLocalizationObjectiveCrossEntropy, TrainNetInfo)
from classification import fishing_feature_generation
import logging
import math
import numpy as np
import os

import tensorflow as tf


class Model(abstract_models.MisconceptionWithFishingRangesModel):

    window_size = 3
    stride = 2
    feature_depths = [48, 64, 96, 128, 192, 256, 384, 512, 768]
    strides = [2] * 9
    assert len(strides) == len(feature_depths)

    initial_learning_rate = 1e-3
    learning_decay_rate = 0.5
    decay_examples = 50000

    window = (256, 1024)

    @property
    def number_of_steps(self):
        return 200000

    @property
    def max_window_duration_seconds(self):
        # A fixed-length rather than fixed-duration window.
        return 0

    @property
    def window_max_points(self):
        return 1024

    @property
    def max_replication_factor(self):
        return 10000.0

    @staticmethod
    def read_metadata(all_available_mmsis,
                      metadata_file,
                      fishing_ranges,
                      fishing_upweight=1.0):
        return utility.read_vessel_time_weighted_metadata(
            all_available_mmsis, metadata_file, fishing_ranges)

    def __init__(self, num_feature_dimensions, vessel_metadata, metrics):
        super(Model, self).__init__(num_feature_dimensions, vessel_metadata)

        def length_or_none(mmsi):
            length = vessel_metadata.vessel_label('length', mmsi)
            if length == '':
                return None

            return np.float32(length)

        self.fishing_localisation_objective = FishingLocalizationObjectiveCrossEntropy(
            'fishing_localisation',
            'Fishing-localisation',
            vessel_metadata,
            metrics=metrics,
            window=self.window)

        self.classification_training_objectives = []
        self.training_objectives = [self.fishing_localisation_objective]

    def build_training_file_list(self, base_feature_path, split):
        random_state = np.random.RandomState()
        training_mmsis = self.vessel_metadata.fishing_range_only_list(
            random_state, split, self.max_replication_factor)
        return [
            '%s/%s.tfrecord' % (base_feature_path, mmsi)
            for mmsi in training_mmsis
        ]

    def _build_net(self, features, timestamps, mmsis, is_training):
        layers.misconception_fishing(
            features,
            self.window_size,
            self.feature_depths,
            self.strides,
            self.fishing_localisation_objective,
            is_training,
            pre_count=128,
            post_count=128,
            post_layers=1)

    def build_training_net(self, features, timestamps, mmsis):
        self._build_net(features, timestamps, mmsis, True)


        loss_and_metrics = [
            self.fishing_localisation_objective.create_loss_and_metrics(timestamps,
                                                              mmsis)
        ]

        learning_rate = tf.train.exponential_decay(
            self.initial_learning_rate, tf.get_or_create_global_step(), 
            self.decay_examples, self.learning_decay_rate)

        optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)

        return (optimizer, loss_and_metrics)

    def build_inference_net(self, features, timestamps, mmsis):
        self._build_net(features, timestamps, mmsis, False)

        evaluations = [
            self.fishing_localisation_objective.build_evaluation(timestamps,
                                                                 mmsis)
        ]

        return evaluations



    def make_model_fn(self):
        def _model_fn(features, labels, mode, params):
            is_train = (mode == tf.estimator.ModeKeys.TRAIN)
            features, timestamps, time_bounds, mmsis = features
            features = features[:, None, :, :] # Still using 2d convs in
            self._build_net(features, timestamps, mmsis, is_train)

            if mode == tf.estimator.ModeKeys.PREDICT:
                raise NotImplementedError()

            global_step = tf.train.get_global_step()

            learning_rate = tf.train.exponential_decay(
                self.initial_learning_rate, global_step, 
                self.decay_examples, self.learning_decay_rate)

            loss_and_metrics = [
                self.fishing_localisation_objective.create_loss_and_metrics(labels)
            ]
            total_loss = 0
            eval_metrics = {}
            for l, em in loss_and_metrics:
                total_loss += l
                eval_metrics.update(em)

            if mode == tf.estimator.ModeKeys.TRAIN:
                optimizer = tf.train.AdamOptimizer(learning_rate=learning_rate)

                update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
                with tf.control_dependencies(update_ops):
                    train_op = optimizer.minimize(loss=total_loss, 
                                                  global_step=global_step)

                return tf.estimator.EstimatorSpec(
                    mode=mode, loss=total_loss, train_op=train_op,
                    eval_metric_ops=eval_metrics)

            return tf.estimator.EstimatorSpec(
              mode=mode,
              loss=total_loss,
              eval_metric_ops=eval_metrics)
        return _model_fn

    def make_estimator(self, checkpoint_dir):
        session_config = tf.ConfigProto(allow_soft_placement=True)
        return  tf.estimator.Estimator(
            config=tf.estimator.RunConfig(
                            model_dir=checkpoint_dir, 
                            save_summary_steps=20,
                            save_checkpoints_secs=300, 
                            keep_checkpoint_max=10,
                            session_config=session_config),
            model_fn=self.make_model_fn(),
            params={
            })   

    def make_input_fn(self, base_feature_path, split, num_parallel_reads):
        def input_fn():
            return (fishing_feature_generation.input_fn(
                        self.vessel_metadata,
                        self.build_training_file_list(base_feature_path, split),
                        self.num_feature_dimensions + 1,
                        self.max_window_duration_seconds,
                        self.window_max_points,
                        self.min_viable_timeslice_length,
                        select_ranges=self.use_ranges_for_training,
                        num_parallel_reads=num_parallel_reads)
                .prefetch(self.batch_size)
                .batch(self.batch_size)
                )
        return input_fn

    def make_training_input_fn(self, base_feature_path, num_parallel_reads):
        return self.make_input_fn(base_feature_path, utility.TRAINING_SPLIT, num_parallel_reads)


    def make_test_input_fn(self, base_feature_path, num_parallel_reads):
        return self.make_input_fn(base_feature_path, utility.TEST_SPLIT, num_parallel_reads)
