"""Run with python -m app.providers.import_players [--file snapshot.json]."""

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db import build_engine, build_session_factory
from app.providers.sleeper import CatalogError, import_catalog, load_catalog


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Sleeper NFL players (cached for 24h)")
    parser.add_argument(
        "--file", type=Path, help="Import a saved Sleeper JSON snapshot without HTTP"
    )
    parser.add_argument("--cache", type=Path, default=Path(".local/sleeper-nfl.json"))
    args = parser.parse_args()
    engine = None
    try:
        payload = load_catalog(args.file or args.cache, offline=args.file is not None)
        engine = build_engine(get_settings().database_url)
        with build_session_factory(engine)() as session:
            result = import_catalog(session, payload)
        print(json.dumps(result))
        return 0
    except (CatalogError, OSError, URLError, ValueError) as exc:
        print(f"Import failed: {exc}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("Import failed: database error; transaction rolled back", file=sys.stderr)
        return 1
    finally:
        if engine is not None:
            engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
