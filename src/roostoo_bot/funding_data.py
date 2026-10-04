"""Public realized-funding archives; no account client, credentials or orders."""
from __future__ import annotations

import argparse
from bisect import bisect_right
from concurrent.futures import ThreadPoolExecutor
import csv
from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import io
import math
from pathlib import Path
import re
from urllib.request import urlopen
import zipfile

BASE = "https://data.binance.vision/data/futures/um/monthly/fundingRate"
SYMBOLS = ("BTCUSDT", "ETHUSDT", "XRPUSDT", "BNBUSDT", "SOLUSDT")
MONTHS = ("2024-12", "2025-01", "2025-02", "2025-03")
HOUR_US = 3_600_000_000
LAG_US = 300_000_000


@dataclass(frozen=True)
class Funding:
    timestamp_us: int
    interval_hours: int
    rate: float


def archive_parts(name: str) -> tuple[str, str]:
    match = re.fullmatch(r"([A-Z0-9]+USDT)-fundingRate-(\d{4}-\d{2})\.zip", name)
    if not match or match[1] not in SYMBOLS:
        raise ValueError("unexpected funding archive name or symbol")
    date.fromisoformat(match[2]+"-01")
    return match[1], match[2]


def verified_payload(path: Path) -> bytes:
    expected = path.with_name(path.name+".CHECKSUM").read_text().split()[0]
    data = path.read_bytes()
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected) or hashlib.sha256(data).hexdigest() != expected.lower():
        raise ValueError("funding archive checksum mismatch")
    return data


def parse_archive(name: str, data: bytes) -> list[Funding]:
    _, month = archive_parts(name)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        if archive.namelist() != [name[:-4]+".csv"]:
            raise ValueError("funding archive must contain its one expected CSV")
        member = archive.infolist()[0]
        if member.file_size > 5_000_000:
            raise ValueError("unexpectedly large funding archive")
        with archive.open(member) as stream:
            reader = csv.DictReader(io.TextIOWrapper(stream, encoding="utf-8"))
            if reader.fieldnames != ["calc_time", "funding_interval_hours", "last_funding_rate"]:
                raise ValueError("unexpected funding schema")
            rows = []
            for row in reader:
                if set(row) != set(reader.fieldnames) or any(v is None for v in row.values()):
                    raise ValueError("malformed funding record")
                milliseconds = int(row["calc_time"])
                interval, rate = int(row["funding_interval_hours"]), float(row["last_funding_rate"])
                if (not 10**12 <= milliseconds < 10**14 or not 1 <= interval <= 24
                        or not math.isfinite(rate) or not -1 < rate < 1):
                    raise ValueError("invalid funding timestamp, interval or rate")
                if datetime.fromtimestamp(milliseconds / 1000, timezone.utc).strftime("%Y-%m") != month:
                    raise ValueError("funding record outside archive month")
                rows.append(Funding(milliseconds * 1000, interval, rate))
    if not rows or any(a.timestamp_us >= b.timestamp_us for a, b in zip(rows, rows[1:])):
        raise ValueError("empty, duplicated or unordered funding records")
    return rows


def load_funding(paths: list[Path]) -> list[Funding]:
    rows = []
    symbols = set()
    for path in paths:
        symbols.add(archive_parts(path.name)[0])
        rows.extend(parse_archive(path.name, verified_payload(path)))
    if len(symbols) != 1:
        raise ValueError("funding input must contain exactly one symbol")
    rows.sort(key=lambda row: row.timestamp_us)
    if any(a.timestamp_us >= b.timestamp_us for a, b in zip(rows, rows[1:])):
        raise ValueError("duplicate funding records across archives")
    return rows


def asof(rows: list[Funding], timestamps: list[int], decision_us: int) -> Funding | None:
    index = bisect_right(timestamps, decision_us - LAG_US) - 1
    if index < 0:
        return None
    row = rows[index]
    if decision_us - row.timestamp_us > row.interval_hours * HOUR_US:
        return None
    return row


def download(destination: Path, name: str) -> str:
    symbol, month = archive_parts(name)
    if month not in MONTHS:
        raise ValueError("only the frozen screening months may be downloaded")
    url = f"{BASE}/{symbol}/{name}"
    with urlopen(url+".CHECKSUM", timeout=25) as response:
        expected = response.read().decode().split()[0]
    if not re.fullmatch(r"[0-9a-fA-F]{64}", expected):
        raise ValueError("invalid published checksum")
    path = destination / name
    if path.exists():
        payload = path.read_bytes()
    else:
        with urlopen(url, timeout=25) as response:
            payload = response.read()
    if hashlib.sha256(payload).hexdigest() != expected.lower():
        raise ValueError("downloaded funding checksum mismatch")
    parse_archive(name, payload)
    if not path.exists():
        temporary = path.with_suffix(".download")
        temporary.write_bytes(payload)
        temporary.replace(path)
    checksum_path = path.with_name(path.name+".CHECKSUM")
    if checksum_path.exists() and checksum_path.read_text().split()[0].lower() != expected.lower():
        raise ValueError("saved checksum changed; preserve old research inputs")
    if not checksum_path.exists():
        checksum_path.write_text(expected.lower()+"  "+name+"\n")
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    names = [f"{symbol}-fundingRate-{month}.zip" for symbol in SYMBOLS for month in MONTHS]
    with ThreadPoolExecutor(max_workers=2) as pool:
        for name in pool.map(lambda name: download(args.output, name), names):
            print("verified", name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
