"""Download official Binance 5m archives and verify their published SHA-256."""
from __future__ import annotations
import argparse
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta
import hashlib
import re
from pathlib import Path
from urllib.request import urlopen

BASE = "https://data.binance.vision/data/spot"


def archive_parts(name: str) -> tuple[str, str, str]:
    match = re.fullmatch(r"([A-Z0-9]{2,20}USDT)-(5m)-(\d{4}-\d{2}(?:-\d{2})?)\.zip", name)
    if not match:
        raise ValueError("invalid public archive filename")
    symbol, interval, period = match.groups()
    date.fromisoformat(period + "-01" if len(period) == 7 else period)
    return symbol, interval, "monthly" if len(period) == 7 else "daily"


def download(destination: Path, name: str) -> str:
    symbol, interval, kind = archive_parts(name)
    url = f"{BASE}/{kind}/klines/{symbol}/{interval}/{name}"
    with urlopen(url + ".CHECKSUM", timeout=30) as response:
        expected = response.read().decode().split()[0]
    path = destination / name
    payload = path.read_bytes() if path.exists() else None
    if payload is None:
        with urlopen(url, timeout=30) as response:
            payload = response.read()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise ValueError(f"checksum mismatch: {name}")
    if not path.exists():
        temporary = path.with_suffix(".download")
        temporary.write_bytes(payload)
        temporary.replace(path)
    (destination / (name + ".CHECKSUM")).write_text(expected + "  " + name + "\n")
    return name


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--months", nargs="*", default=[])
    parser.add_argument("--symbols", nargs="+", default=["BTCUSDT", "ETHUSDT"],
                        help="offline public archive symbols; does not change trading pairs")
    parser.add_argument("--start-date", type=date.fromisoformat)
    parser.add_argument("--end-date", type=date.fromisoformat)
    parser.add_argument("--verify-existing", action="store_true")
    args = parser.parse_args()
    if len(set(args.symbols)) != len(args.symbols) or any(not re.fullmatch(r"[A-Z0-9]{2,20}USDT", s) for s in args.symbols):
        parser.error("symbols must be unique uppercase USDT spot symbols")
    args.output.mkdir(parents=True, exist_ok=True)
    names = set()
    for month in args.months:
        if not re.fullmatch(r"\d{4}-\d{2}", month) or date.fromisoformat(month + "-01") >= date.today().replace(day=1):
            parser.error("monthly archives must be completed calendar months")
        for symbol in args.symbols:
            names.add(f"{symbol}-5m-{month}.zip")
    if args.end_date and not args.start_date:
        parser.error("end-date requires start-date")
    if args.start_date:
        if not args.end_date or args.end_date < args.start_date or args.end_date >= date.today():
            parser.error("provide a past, ordered date range")
        day = args.start_date
        while day <= args.end_date:
            for symbol in args.symbols:
                names.add(f"{symbol}-5m-{day.isoformat()}.zip")
            day += timedelta(days=1)
    if args.verify_existing:
        names.update(path.name for path in args.output.glob("*USDT-5m-*.zip"))
    with ThreadPoolExecutor(max_workers=4) as pool:
        for name in pool.map(lambda name: download(args.output, name), sorted(names)):
            print("verified", name, flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
