"""python -m app.identities.cli review | backfill | link | create --help"""

import argparse
import sys
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from app.core.config import get_settings
from app.db import build_engine, build_session_factory
from app.identities.schemas import IdentityPage, IdentityRead
from app.identities.service import (
    create_asset_for_identity,
    list_identities,
    manually_link,
    seed_catalog_identities,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Review and resolve provider identities")
    commands = parser.add_subparsers(dest="command", required=True)
    review = commands.add_parser("review")
    review.add_argument("--limit", type=int, choices=range(1, 101), default=20, metavar="1..100")
    review.add_argument("--offset", type=int, default=0)
    commands.add_parser("backfill")
    link = commands.add_parser("link")
    link.add_argument("--identity-id", type=UUID, required=True)
    link.add_argument("--asset-id", type=UUID, required=True)
    link.add_argument("--reason", required=True)
    create = commands.add_parser(
        "create", help="Explicitly create a new asset for an unresolved ID"
    )
    create.add_argument("--identity-id", type=UUID, required=True)
    create.add_argument("--reason", required=True)
    args = parser.parse_args()
    if args.command == "review" and args.offset < 0:
        parser.error("offset must be nonnegative")
    engine = build_engine(get_settings().database_url)
    try:
        with build_session_factory(engine)() as session, session.begin():
            if args.command == "review":
                result = IdentityPage.model_validate(
                    list_identities(
                        session, unresolved_only=True, limit=args.limit, offset=args.offset
                    )
                ).model_dump_json()
            elif args.command == "backfill":
                count = seed_catalog_identities(session, provenance="catalog backfill CLI")
                result = f'{{"created": {count}}}'
            elif args.command == "link":
                result = IdentityRead.model_validate(
                    manually_link(session, args.identity_id, args.asset_id, reason=args.reason)
                ).model_dump_json()
            else:
                result = IdentityRead.model_validate(
                    create_asset_for_identity(session, args.identity_id, reason=args.reason)
                ).model_dump_json()
        print(result)
        return 0
    except ValueError as exc:
        print(f"Identity operation failed: {exc}", file=sys.stderr)
        return 1
    except SQLAlchemyError:
        print("Identity operation failed: database error; transaction rolled back", file=sys.stderr)
        return 1
    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())
