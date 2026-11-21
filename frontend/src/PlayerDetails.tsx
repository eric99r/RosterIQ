import { useEffect, useRef, useState } from "react";
import { getJson, type Player } from "./api";

export default function PlayerDetails({
  id,
  onClose,
}: {
  id: string;
  onClose: () => void;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [player, setPlayer] = useState<Player | null>(null);
  const [error, setError] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    dialog.current?.showModal();
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    setPlayer(null);
    setError(false);
    getJson<Player>(
      `/api/v1/players/${encodeURIComponent(id)}`,
      controller.signal,
    )
      .then(setPlayer)
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, [id, attempt]);

  return (
    <dialog
      ref={dialog}
      aria-label="Player details"
      onCancel={onClose}
      onClick={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <div className="dialog-content">
        <div className="section-heading">
          <span className="eyebrow">PLAYER PROFILE</span>
          <button
            className="icon-button"
            onClick={onClose}
            aria-label="Close player details"
          >
            ×
          </button>
        </div>
        {error ? (
          <div role="alert">
            <h2>Couldn’t load this player.</h2>
            <p>Please try again.</p>
            <button
              className="button"
              onClick={() => setAttempt((value) => value + 1)}
            >
              Retry details
            </button>
          </div>
        ) : !player ? (
          <p role="status">Loading player details…</p>
        ) : (
          <>
            <div className="profile-avatar">
              {player.name
                .split(" ")
                .map((part) => part[0])
                .slice(0, 2)
                .join("")}
            </div>
            <h2>{player.name}</h2>
            <p className="profile-subtitle">
              {player.sport} · {player.position || "Position unavailable"}
            </p>
            <dl className="details-grid">
              <div>
                <dt>Team</dt>
                <dd>{player.team || "Not listed"}</dd>
              </div>
              <div>
                <dt>Sport</dt>
                <dd>{player.sport}</dd>
              </div>
              <div>
                <dt>Provider</dt>
                <dd>{player.provider}</dd>
              </div>
              <div>
                <dt>Provider player ID</dt>
                <dd>{player.provider_player_id}</dd>
              </div>
              <div className="full">
                <dt>Catalog ID</dt>
                <dd className="mono">{player.id}</dd>
              </div>
              <div className="full">
                <dt>Added to catalog</dt>
                <dd>{new Date(player.created_at).toLocaleString()}</dd>
              </div>
            </dl>
            <p className="fine-print">
              Provider records are separate identities. The same player may
              appear from more than one source.
            </p>
          </>
        )}
      </div>
    </dialog>
  );
}
