"""
Ingestion of blocks and their contained transactions from RPC.
"""

import asyncio
from collections import defaultdict
import multiprocessing as mp
import os
import queue
from typing import Union, Optional

import aiohttp
import pyarrow as pa
import pyarrow.parquet as pq


from ..rpc.utils import PoktRPCError, PortalRPCError
from ..rpc.models import BlockHeader, Transaction
from ..rpc.data.async_block import async_get_block_transactions, async_get_block
from .schema import (
    block_header_schema,
    tx_schema,
    flatten_header,
    flatten_tx,
    flatten_tx_message,
    schema_for_msg,
)

QueueT = Union[queue.Queue, mp.Queue]


class RetriesExceededError(Exception):
    pass


async def async_ingest_txs_by_block(
    block_no: int,
    rpc_url: str,
    session: Optional[aiohttp.ClientSession] = None,
    page: int = 1,
    retries: int = 100,
    progress_queue: Optional[QueueT] = None,
):
    try:
        block_txs = await async_get_block_transactions(
            rpc_url, height=block_no, per_page=1000, page=page, session=session
        )
    except (PoktRPCError, PortalRPCError, Exception):
        if progress_queue:
            progress_queue.put(("error", "txs", block_no, page))
        if retries < 0:
            raise RetriesExceededError(
                "Out of retries getting block {} transactions page {}".format(
                    block_no, page
                )
            )
        yield async_ingest_txs_by_block(
            block_no,
            rpc_url,
            session=session,
            page=page,
            retries=retries - 1,
            progress_queue=progress_queue,
        )
    while block_txs:
        if block_txs.txs:
            yield block_txs.txs
        if block_txs.page_total is None or block_txs.txs is None:
            yield None
            break
        page += 1
        try:
            block_txs = await async_get_block_transactions(
                rpc_url, height=block_no, per_page=1000, page=page, session=session
            )
        except (PoktRPCError, PortalRPCError, Exception):
            if progress_queue:
                progress_queue.put(("error", "txs", block_no, page))
            if retries < 0:
                raise RetriesExceededError(
                    "Out of retries getting block {} transactions page {}".format(
                        block_no, page
                    )
                )
            yield async_ingest_txs_by_block(
                block_no,
                rpc_url,
                session=session,
                page=page,
                retries=retries - 1,
                progress_queue=progress_queue,
            )


async def async_ingest_block_header(
    block_no: int,
    rpc_url: str,
    session: Optional[aiohttp.ClientSession] = None,
    retries: int = 100,
    progress_queue: Optional[QueueT] = None,
) -> BlockHeader:
    try:
        block = await async_get_block(rpc_url, height=block_no, session=session)
    except (PoktRPCError, PortalRPCError):
        if progress_queue:
            progress_queue.put(("error", "block", block_no))
        if retries < 0:
            raise RetriesExceededError(
                "Out of retries getting block {}".format(block_no)
            )
        return await async_ingest_block_header(
            block_no, rpc_url, session=session, retries=retries - 1
        )
    except Exception as e:
        if progress_queue:
            progress_queue.put(("error", "block", block_no))
        raise (e)

    else:
        if block.block is None and retries > 0:
            return await async_ingest_block_header(
                block_no,
                rpc_url,
                session=session,
                retries=retries - 1,
                progress_queue=progress_queue,
            )
    return block.block.header


def _block_headers_to_table(headers):
    record_dict = defaultdict(list)
    for header in headers:
        for k, v in header.items():
            record_dict[k].append(v)
    return pa.Table.from_pydict(record_dict).cast(block_header_schema)


def _txs_to_table(txs):
    record_dict = defaultdict(list)
    for tx in txs:
        for k, v in tx.items():
            record_dict[k].append(v)
    return pa.Table.from_pydict(record_dict).cast(tx_schema)


def flatten_tx_messages(txs):
    msgs = {
        "apps": defaultdict(list),
        "gov": defaultdict(list),
        "pos": defaultdict(list),
        "pocketcore": defaultdict(list),
    }
    for tx in txs:
        record, module, type_ = flatten_tx_message(tx)
        if record is not None:
            msgs[module][type_].append(record)
    return msgs


def _msgs_to_tables(msgs):
    tables = {
        "apps": {},
        "gov": {},
        "pos": {},
        "pocketcore": {},
    }
    for module, items in msgs.items():
        for type_, msgs in items.items():
            record_dict = defaultdict(list)
            for msg in msgs:
                for k, v in msg.items():
                    record_dict[k].append(v)
            tables[module][type_] = pa.Table.from_pydict(record_dict).cast(
                schema_for_msg(module, type_)
            )
    return tables


def _append_msg_tables(msgs_dir, tables, start_block, end_block):
    for module, items in tables.items():
        for type_, table in items.items():
            parquet_dir = os.path.join(msgs_dir, module, type_)
            _parquet_append(parquet_dir, table, start_block, end_block)


def _parquet_append(parquet_dir, table, start_block, end_block):
    basename = "block_{}-{}".format(start_block, end_block) + "-{i}.parquet"
    pq.write_to_dataset(
        table,
        parquet_dir,
        basename_template=basename,
    )


async def async_ingest_block(
    block_no: int,
    rpc_url: str,
    session: Optional[aiohttp.ClientSession] = None,
    progress_queue: Optional[QueueT] = None,
):
    flat_txs = []
    msgs = {
        "apps": defaultdict(list),
        "gov": defaultdict(list),
        "pos": defaultdict(list),
        "pocketcore": defaultdict(list),
    }
    async for tx_set in async_ingest_txs_by_block(
        block_no, rpc_url, session, progress_queue=progress_queue
    ):

        if tx_set is None:
            continue
        flat_txs.extend([flatten_tx(tx) for tx in tx_set])
        flat_msgs = flatten_tx_messages(tx_set)
        for k, d in flat_msgs.items():
            for mod, vals in d.items():
                msgs[k][mod].extend(vals)

    header = await async_ingest_block_header(
        block_no, rpc_url, session, progress_queue=progress_queue
    )
    flat_header = flatten_header(header)
    return flat_txs, flat_header, msgs


async def async_ingest_block_range(
    starting_block: int,
    ending_block: int,
    rpc_url: str,
    block_parquet,
    tx_parquet,
    msgs_parquet,
    batch_size=1000,
    session: Optional[aiohttp.ClientSession] = None,
    progress_queue: Optional[QueueT] = None,
) -> Optional[QueueT]:
    if session is None:  # Just pipe back into this with a session
        async with aiohttp.ClientSession(rpc_url) as session:
            return await async_ingest_block_range(
                starting_block,
                ending_block,
                rpc_url,
                block_parquet,
                tx_parquet,
                msgs_parquet,
                batch_size=batch_size,
                session=session,
                progress_queue=progress_queue,
            )

    txs = []
    headers = []
    msgs = {
        "apps": defaultdict(list),
        "gov": defaultdict(list),
        "pos": defaultdict(list),
        "pocketcore": defaultdict(list),
    }
    group_start = block_no = starting_block
    for i, block_no in enumerate(range(starting_block, ending_block + 1)):
        if i != 0 and i % batch_size == 0:
            header_table = _block_headers_to_table(headers)
            txs_table = _txs_to_table(txs)
            msgs_tables = _msgs_to_tables(msgs)
            _parquet_append(block_parquet, header_table, group_start, block_no)
            _parquet_append(tx_parquet, txs_table, group_start, block_no)
            _append_msg_tables(msgs_parquet, msgs_tables, group_start, block_no)
            if progress_queue:
                progress_queue.put(("block", len(headers)))
                progress_queue.put(("txs", len(txs)))
            group_start = block_no
            txs = []
            headers = []
            msgs = {
                "apps": defaultdict(list),
                "gov": defaultdict(list),
                "pos": defaultdict(list),
                "pocketcore": defaultdict(list),
            }
        block_txs, block_header, block_msgs = await async_ingest_block(
            block_no, rpc_url, session=session
        )
        txs.extend(block_txs)
        headers.append(block_header)
        for mod, items in block_msgs.items():
            for t, ms in items.items():
                msgs[mod][t].extend(ms)
    if headers:
        header_table = _block_headers_to_table(headers)
        _parquet_append(block_parquet, header_table, group_start, block_no)
    if txs:
        txs_table = _txs_to_table(txs)
        _parquet_append(tx_parquet, txs_table, group_start, block_no)
    if msgs:
        msgs_tables = _msgs_to_tables(msgs)
        _append_msg_tables(msgs_parquet, msgs_tables, group_start, block_no)
    if progress_queue:
        progress_queue.put(("block", len(headers)))
        progress_queue.put(("txs", len(txs)))
    return progress_queue
