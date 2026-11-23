"""Identity operations flush but never commit: the caller owns the transaction."""

from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from app.identities.models import AssetType, FantasyAsset, ProviderIdentity
from app.identities.schemas import IdentityInput, SourceIdentity
from app.players.models import Player, Sport


class IdentityConflictError(ValueError):
    pass


def find_identity(
    session: Session, source: SourceIdentity, *, lock: bool = False
) -> ProviderIdentity | None:
    query = select(ProviderIdentity).where(
        ProviderIdentity.provider == source.provider,
        ProviderIdentity.sport == source.sport,
        ProviderIdentity.provider_player_id == source.provider_player_id,
    )
    if lock:
        query = query.with_for_update().execution_options(populate_existing=True)
    return session.scalar(query)


def seed_catalog_identities(
    session: Session, *, provenance: str, player_ids: list[UUID] | None = None
) -> int:
    """Give unmapped catalog rows independent identities; never infer a cross-source match.

    UUIDs are deterministic (the original player UUID) in each new table. Existing
    mappings, including unresolved ones, are retained on repeated imports/backfills.
    """
    query = select(Player, ProviderIdentity).outerjoin(
        ProviderIdentity,
        and_(
            Player.provider == ProviderIdentity.provider,
            Player.sport == ProviderIdentity.sport,
            Player.provider_player_id == ProviderIdentity.provider_player_id,
        ),
    )
    if player_ids is not None:
        query = query.where(Player.id.in_(player_ids))
    mappings = []
    for player, identity in session.execute(query).all():
        if identity is not None:
            if identity.asset_type != AssetType.ATHLETE:
                raise IdentityConflictError("Catalog player identity belongs to a team defense")
            if identity.player_id not in (None, player.id):
                raise IdentityConflictError("Identity already belongs to another catalog record")
            identity.player_id = player.id
            continue
        session.add(
            FantasyAsset(
                id=player.id, sport=player.sport, asset_type=AssetType.ATHLETE, name=player.name
            )
        )
        # Flush assets before mappings because this module uses explicit IDs, not ORM relationships.
        mappings.append(
            ProviderIdentity(
                id=player.id,
                provider=player.provider,
                sport=player.sport,
                provider_player_id=player.provider_player_id,
                asset_type=AssetType.ATHLETE,
                source_name=player.name,
                asset_id=player.id,
                player_id=player.id,
                provenance=provenance,
                match_method="catalog_seed",
            )
        )
    session.flush()
    session.add_all(mappings)
    session.flush()
    return len(mappings)


def resolve_identity(
    session: Session,
    data: IdentityInput,
    *,
    trusted_references: tuple[SourceIdentity, ...] = (),
) -> ProviderIdentity:
    """Only vetted adapters may supply trusted references; this is not a public write API.

    A single name match is still unresolved. Every supplied reference must resolve
    consistently before a new mapping can link; conflicts never merge canonical assets.
    """
    if data.asset_type == AssetType.TEAM_DEFENSE and data.sport != Sport.NFL:
        raise ValueError("Team defenses must be NFL assets")
    identity = find_identity(session, data, lock=True)
    if identity is not None and identity.asset_type != data.asset_type:
        raise IdentityConflictError("Source ID already has another asset type")
    targets: set[UUID] = set()
    reason = "no_trusted_match"
    incomplete = False
    for reference in trusted_references:
        if reference.sport != data.sport:
            raise IdentityConflictError("Trusted reference belongs to another sport")
        match = find_identity(session, reference)
        if match is not None and match.asset_type != data.asset_type:
            raise IdentityConflictError("Trusted reference belongs to another asset type")
        if match is None or match.asset_id is None:
            incomplete = True
        else:
            targets.add(match.asset_id)
    if len(targets) > 1:
        reason = "conflicting_trusted_ids"
    elif incomplete:
        reason = "unresolved_trusted_id"
    target = next(iter(targets)) if len(targets) == 1 and not incomplete else None
    if identity is not None and identity.asset_id is not None:
        if targets - {identity.asset_id}:
            raise IdentityConflictError("Trusted evidence conflicts with an existing mapping")
        return identity
    if identity is None:
        identity = ProviderIdentity(**data.model_dump(), review_reason=reason)
        session.add(identity)
    identity.trusted_references = [ref.model_dump(mode="json") for ref in trusted_references]
    identity.asset_id = target
    identity.match_method = "trusted_id" if target else None
    identity.review_reason = None if target else reason
    identity.resolution_evidence = data.provenance if target else None
    session.flush()
    return identity


def create_asset_for_identity(
    session: Session, identity_id: UUID, *, reason: str
) -> ProviderIdentity:
    """Explicitly establish a new athlete/defense after review found no existing asset."""
    if not reason.strip() or len(reason) > 500:
        raise ValueError("A nonempty evidence note of at most 500 characters is required")
    identity = session.scalar(
        select(ProviderIdentity)
        .where(ProviderIdentity.id == identity_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if identity is None:
        raise ValueError("Identity not found")
    if identity.asset_id is not None:
        return identity
    asset = FantasyAsset(
        name=identity.source_name, sport=identity.sport, asset_type=identity.asset_type
    )
    session.add(asset)
    session.flush()
    return manually_link(session, identity.id, asset.id, reason=reason)


def manually_link(
    session: Session, identity_id: UUID, asset_id: UUID, *, reason: str
) -> ProviderIdentity:
    """Resolve an unlinked record with evidence; never reassign an existing link."""
    if not reason.strip() or len(reason) > 500:
        raise ValueError("A nonempty evidence note of at most 500 characters is required")
    identity = session.scalar(
        select(ProviderIdentity)
        .where(ProviderIdentity.id == identity_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    asset = session.get(FantasyAsset, asset_id)
    if identity is None or asset is None:
        raise ValueError("Identity or asset not found")
    if (identity.sport, identity.asset_type) != (asset.sport, asset.asset_type):
        raise IdentityConflictError("Sport and asset type must match")
    if identity.asset_id is not None:
        if identity.asset_id == asset.id:
            return identity
        raise IdentityConflictError("Already linked; reassignment is not supported")
    identity.asset_id = asset.id
    identity.match_method = "manual"
    identity.review_reason = None
    identity.resolution_evidence = reason
    session.flush()
    return identity


def list_identities(
    session: Session,
    *,
    unresolved_only: bool = False,
    sport: Sport | None = None,
    player_id: UUID | None = None,
    limit: int = 20,
    offset: int = 0,
):
    filters = []
    if unresolved_only:
        filters.append(ProviderIdentity.asset_id.is_(None))
    if sport is not None:
        filters.append(ProviderIdentity.sport == sport)
    if player_id is not None:
        filters.append(ProviderIdentity.player_id == player_id)
    return {
        "items": session.scalars(
            select(ProviderIdentity)
            .where(*filters)
            .order_by(ProviderIdentity.id)
            .limit(limit)
            .offset(offset)
        ).all(),
        "total": session.scalar(select(func.count()).select_from(ProviderIdentity).where(*filters)),
        "limit": limit,
        "offset": offset,
    }
