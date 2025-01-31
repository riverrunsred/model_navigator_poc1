# Copyright (c) 2021-2022, NVIDIA CORPORATION. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
from typing import Optional, Tuple

import tensorflow as tf  # pytype: disable=import-error

from model_navigator.framework_api.commands.core import Command, CommandType
from model_navigator.framework_api.commands.export import exporters
from model_navigator.framework_api.commands.export.base import ExportBase
from model_navigator.framework_api.common import TensorMetadata
from model_navigator.framework_api.execution_context import ExecutionContext
from model_navigator.framework_api.logger import LOGGER
from model_navigator.framework_api.utils import parse_kwargs_to_cmd
from model_navigator.model import Format


class ExportTF2SavedModel(ExportBase):
    def __init__(self, requires: Tuple[Command, ...] = ()):
        super().__init__(
            name="Export TensorFlow2 to SavedModel",
            command_type=CommandType.EXPORT,
            target_format=Format.TF_SAVEDMODEL,
            requires=requires,
        )

    def __call__(
        self,
        model: tf.keras.Model,
        model_name: str,
        input_metadata: TensorMetadata,
        output_metadata: TensorMetadata,
        workdir: Path,
        verbose: bool,
        forward_kw_names: Optional[Tuple[str, ...]] = None,
        **kwargs,
    ) -> Optional[Path]:
        LOGGER.info("TensorFlow2 to SavedModel export started")
        exported_model_path = workdir / self.get_output_relative_path()
        if exported_model_path.exists():
            LOGGER.info("Model already exists. Skipping export.")
            return self.get_output_relative_path()
        assert model is not None
        exported_model_path.parent.mkdir(parents=True, exist_ok=True)

        exporters.keras2savedmodel.get_model = lambda: model

        with ExecutionContext(
            workdir=workdir,
            script_path=exported_model_path.parent / "reproduce_export.py",
            cmd_path=exported_model_path.parent / "reproduce_export.sh",
            verbose=verbose,
        ) as context:

            kwargs = {
                "exported_model_path": exported_model_path.relative_to(workdir).as_posix(),
                "input_metadata": input_metadata.to_json(),
                "output_names": list(output_metadata.keys()),
                "keras_input_names": list(forward_kw_names) if forward_kw_names else None,
                "navigator_workdir": workdir.as_posix(),
            }

            args = parse_kwargs_to_cmd(kwargs)

            context.execute_local_runtime_script(
                exporters.keras2savedmodel.__file__, exporters.keras2savedmodel.export, args
            )

        return self.get_output_relative_path()


class UpdateSavedModelSignature(ExportBase):
    def __init__(self, requires: Tuple[Command, ...] = ()):
        super().__init__(
            name="Update SavedModel Signature",
            command_type=CommandType.EXPORT,
            target_format=Format.TF_SAVEDMODEL,
            requires=requires,
        )

    def __call__(
        self,
        model_name: str,
        input_metadata: TensorMetadata,
        output_metadata: TensorMetadata,
        workdir: Path,
        verbose: bool,
        **kwargs,
    ) -> Optional[Path]:
        LOGGER.info("TensorFlow2 to SavedModel export started")

        exported_model_path = workdir / self.get_output_relative_path()
        assert exported_model_path.exists()
        exported_model_path.parent.mkdir(parents=True, exist_ok=True)

        exporters.savedmodel2savedmodel.get_model = lambda: tf.keras.models.load_model(exported_model_path)

        with ExecutionContext(
            workdir=workdir,
            script_path=exported_model_path.parent / "reproduce_export.py",
            cmd_path=exported_model_path.parent / "reproduce_export.sh",
            verbose=verbose,
        ) as context:

            kwargs = {
                "exported_model_path": exported_model_path.relative_to(workdir).as_posix(),
                "input_metadata": input_metadata.to_json(),
                "output_names": list(output_metadata.keys()),
                "navigator_workdir": workdir.as_posix(),
            }

            args = parse_kwargs_to_cmd(kwargs)

            context.execute_local_runtime_script(
                exporters.savedmodel2savedmodel.__file__, exporters.savedmodel2savedmodel.export, args
            )

        return self.get_output_relative_path()
