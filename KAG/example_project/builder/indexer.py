# Copyright 2023 OpenSPG Authors
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may not use this file except
# in compliance with the License. You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software distributed under the License
# is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express
# or implied.

import asyncio
import os
import logging
import time
import sys
from pathlib import Path

from kag.common.registry import import_modules_from_path
from kag.builder.runner import BuilderChainRunner
from kag.interface.common.llm_client import LLMCallCcontext, TokenMeterFactory

TIO_EXPERIMENT_ROOT = Path(__file__).resolve().parents[3]
if str(TIO_EXPERIMENT_ROOT) not in sys.path:
    sys.path.insert(0, str(TIO_EXPERIMENT_ROOT))

from token_usage import record_usage_counts, reset_usage_ledger  # noqa: E402

logger = logging.getLogger(__name__)


def token_usage_path() -> Path:
    return TIO_EXPERIMENT_ROOT / "phase1" / "token_usage" / "token_usage_kag.json"


async def buildKB(dir_path):
    from kag.common.conf import KAG_CONFIG

    start = time.time()
    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    reset_usage_ledger(token_usage_path(), "prep")
    task_id = "kag-prep-builder"
    TokenMeterFactory().clear_all()
    with LLMCallCcontext(task_id, True):
        await runner.ainvoke(dir_path)
    end = time.time()

    token_meter = TokenMeterFactory().get_meter(task_id)
    stat = token_meter.to_dict()
    record_usage_counts(
        token_usage_path(),
        experiment="kag",
        ledger="prep",
        case_id=None,
        stage="kg_builder",
        model=os.getenv("GRAPHRAG_LLM_MODEL", "gpt-5.4"),
        api="kag.llm_meter",
        input_tokens=stat.get("prompt_tokens", 0),
        output_tokens=stat.get("completion_tokens", 0),
        total_tokens=stat.get("total_tokens", 0),
        usage_source="kag.LLMClient.TokenMeter",
    )
    logger.info(
        f"\n\nbuildKB successfully for {dir_path}\n\nTimes cost:{end-start}s\n\nTokens cost: {stat}"
    )


def buildKB_debug(dir_path):
    from kag.common.conf import KAG_CONFIG

    runner = BuilderChainRunner.from_config(
        KAG_CONFIG.all_config["kag_builder_pipeline"]
    )
    runner.invoke(dir_path)


if __name__ == "__main__":
    dir_path = os.path.dirname(os.path.abspath(__file__))
    module_path = os.path.dirname(dir_path)
    import_modules_from_path(module_path)

    data_dir_path = os.path.join(dir_path, "data")
    asyncio.run(buildKB(data_dir_path))
    # buildKB_debug(data_dir_path)
