"""Preflight-independent bounded dispatch with explicit uncertain outcomes."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from godoo.client.errors import OdooError, OdooNetworkError, OdooRpcError

from .types import PropertyBatchCancelledError, PropertyReceipt, PropertyValueError, PropertyWriteUnknownError

if TYPE_CHECKING:
    from collections.abc import Mapping

    from .scope import PropertyScope


async def write_one(scope: PropertyScope, record_id: int, payload: dict[str, Any]) -> PropertyReceipt:
    try:
        result = await scope.call(scope.model, "write", [[record_id], {scope.field: payload}], {})
    except OdooNetworkError as exc:
        return PropertyReceipt(record_id, "unknown", PropertyWriteUnknownError(record_id, cause=exc))
    except OdooError as exc:
        return PropertyReceipt(record_id, "failed", exc)
    except Exception as exc:
        return PropertyReceipt(record_id, "unknown", PropertyWriteUnknownError(record_id, cause=exc))
    if result is True:
        return PropertyReceipt(record_id, "acknowledged")
    if result is False:
        return PropertyReceipt(record_id, "failed", OdooRpcError("Property write was rejected."))
    return PropertyReceipt(record_id, "unknown", PropertyWriteUnknownError(record_id))


async def dispatch(
    scope: PropertyScope,
    payloads: Mapping[int, dict[str, Any]],
    concurrency: int,
) -> list[PropertyReceipt]:
    if type(concurrency) is not int or concurrency <= 0:
        raise PropertyValueError("concurrency must be a positive integer.")
    queue = iter(payloads.items())
    receipts: dict[int, PropertyReceipt] = {}
    started: set[int] = set()

    async def worker() -> None:
        for rid, payload in queue:
            started.add(rid)
            receipts[rid] = await write_one(scope, rid, payload)

    workers = [asyncio.create_task(worker()) for _ in range(min(concurrency, len(payloads)))]
    try:
        await asyncio.gather(*workers)
    except asyncio.CancelledError:
        for task in workers:
            task.cancel()
        await asyncio.gather(*workers, return_exceptions=True)
        observed = [
            receipts.get(rid, PropertyReceipt(rid, "unknown", PropertyWriteUnknownError(rid)))
            for rid in payloads
            if rid in started
        ]
        raise PropertyBatchCancelledError(observed, [rid for rid in payloads if rid not in started]) from None
    return [receipts[rid] for rid in payloads]


def require_acknowledged(receipt: PropertyReceipt) -> None:
    if receipt.error is not None:
        raise receipt.error
