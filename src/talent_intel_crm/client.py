from __future__ import annotations

from temporalio.client import Client

from talent_intel_crm.config import TemporalConfig


async def connect_temporal() -> Client:
    config = TemporalConfig()
    return await Client.connect(
        config.target_host,
        namespace=config.namespace,
        api_key=config.api_key,
        tls=True if (config.use_tls or config.api_key) else None,
        identity=config.identity,
    )
