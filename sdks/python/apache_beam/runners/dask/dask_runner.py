#
# Licensed to the Apache Software Foundation (ASF) under one or more
# contributor license agreements.  See the NOTICE file distributed with
# this work for additional information regarding copyright ownership.
# The ASF licenses this file to You under the Apache License, Version 2.0
# (the "License"); you may not use this file except in compliance with
# the License.  You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

"""DaskRunner, executing remote jobs on Dask.distributed.

The DaskRunner is a runner implementation that executes a graph of
transformations across processes and workers via Dask distributed's
scheduler.
"""
import functools
import itertools
import typing as t
import argparse
import dataclasses

from apache_beam import pvalue
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.pvalue import PValue
from apache_beam.runners.direct.consumer_tracking_pipeline_visitor import ConsumerTrackingPipelineVisitor
from apache_beam.utils.interactive_utils import is_in_notebook

from apache_beam.runners.direct.direct_runner import BundleBasedDirectRunner

from apache_beam.pipeline import PipelineVisitor, AppliedPTransform

import dask.bag as db


class DaskOptions(PipelineOptions):

    @classmethod
    def _add_argparse_args(cls, parser: argparse.ArgumentParser) -> None:
        # TODO: get Dask client options
        pass


@dataclasses.dataclass
class DaskExecutor:
    value_to_consumers: t.Dict[pvalue.PValue, t.Set[AppliedPTransform]]
    root_transforms: t.Set[AppliedPTransform]
    step_names:  t.Dict[AppliedPTransform, str]
    views: t.List[pvalue.AsSideInput]
    _root_nodes = None
    _all_nodes = None

    @property
    @functools.cached_property
    def root_nodes(self):
        return frozenset(self.root_transforms)

    @property
    @functools.cached_property
    def all_nodes(self):
        return itertools.chain(
            self.root_nodes, *itertools.chain(self.value_to_consumers.values())))

    def start(self) -> None:
        for root in self.root_nodes:



    def await_completion(self) -> None:
        pass

    def shutdown(self) -> None:
        pass


class DaskRunner(BundleBasedDirectRunner):
    """Executes a pipeline on a Dask distributed client."""

    @staticmethod
    def to_dask_bag_visitor(self) -> PipelineVisitor:

        @dataclasses.dataclass
        class DaskBagVisitor(PipelineVisitor):

            value_to_consumers = {
            }  # type: Dict[pvalue.PValue, Set[AppliedPTransform]]
            root_transforms = set()  # type: Set[AppliedPTransform]
            step_names = {}  # type: Dict[AppliedPTransform, str]

            def __post_init__(self):
                self._num_transforms = 0
                self._views = set()

            def visit_transform(self, applied_ptransform: AppliedPTransform) -> None:
                inputs = list(applied_ptransform.inputs)
                if inputs:
                    for input_value in inputs:
                        if isinstance(input_value, pvalue.PBegin):
                            self.root_transforms.add(applied_ptransform)
                        if input_value not in self.value_to_consumers:
                            self.value_to_consumers[input_value] = set()
                        self.value_to_consumers[input_value].add(applied_ptransform)
                else:
                    self.root_transforms.add(applied_ptransform)
                self.step_names[applied_ptransform] = 's%d' % (self._num_transforms)
                self._num_transforms += 1

                for side_input in applied_ptransform.side_inputs:
                    self._views.add(side_input)

        return DaskBagVisitor()



    @staticmethod
    def is_fnapi_compatible():
        return False

    def run_pipeline(self, pipeline, options):
        # TODO(alxr): Create interactive notebook support.
        if is_in_notebook():
            raise NotImplementedError('interactive support will come later!')

        try:
            import dask.bag as db
            import dask.distributed as ddist
        except ImportError:
            raise ImportError('DaskRunner is not available. Please install apache_beam[dask].')

        dask_options = options.view_as(DaskOptions)

        self.client = ddist.Client(**dask_options.get_all_options())

        self.consumer_tracking_visitor = ConsumerTrackingPipelineVisitor()
        pipeline.visit(self.consumer_tracking_visitor)

        dask_visitor = self.to_dask_bag_visitor()
        pipeline.visit(dask_visitor)


        # if pipeline:
        #     pass
        # else:
        #     raise ValueError('Proto or FunctionAPI environments are not supported.')
        # if pipeline:
        #
        #     # Flatten / Optimize graph?
        #
        #     # Trigger a traversal of all reachable nodes.
        #     self.visit_transforms(pipeline, options)
        #
        # Get API Client?