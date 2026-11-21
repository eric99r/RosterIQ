import { useEffect, useState } from "react";
import { getJson, listPlayers, type PlayerPage, type Sport } from "./api";
import PlayerDetails from "./PlayerDetails";

const format = (value: number) => value.toLocaleString();

export default function App() {
  const [sport, setSport] = useState<Sport | "">("");
  const [input, setInput] = useState("");
  const [query, setQuery] = useState("");
  const [offset, setOffset] = useState(0);
  const [page, setPage] = useState<PlayerPage | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [refresh, setRefresh] = useState(0);
  const [counts, setCounts] = useState<{
    all: number;
    nfl: number;
    nba: number;
  } | null>(null);
  const [ready, setReady] = useState<"checking" | "online" | "offline">(
    "checking",
  );
  const [selected, setSelected] = useState<string | null>(null);

  useEffect(() => {
    if (input.trim() === query) return;
    const timer = setTimeout(() => {
      setQuery(input.trim());
      setOffset(0);
    }, 300);
    return () => clearTimeout(timer);
  }, [input, query]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError(false);
    listPlayers(sport, query, offset, controller.signal)
      .then(setPage)
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [sport, query, offset, refresh]);

  useEffect(() => {
    const controller = new AbortController();
    setCounts(null);
    Promise.all(
      ["", "NFL", "NBA"].map((value) =>
        getJson<PlayerPage>(
          `/api/v1/players?limit=1${value ? `&sport=${value}` : ""}`,
          controller.signal,
        ),
      ),
    )
      .then(([all, nfl, nba]) =>
        setCounts({ all: all.total, nfl: nfl.total, nba: nba.total }),
      )
      .catch(() => {
        /* Catalog remains usable when summary requests fail. */
      });
    return () => controller.abort();
  }, [refresh]);

  useEffect(() => {
    const controller = new AbortController();
    const check = () =>
      getJson<{ status: string }>("/health/ready", controller.signal)
        .then(() => setReady("online"))
        .catch(() => {
          if (!controller.signal.aborted) setReady("offline");
        });
    void check();
    const timer = setInterval(check, 30000);
    return () => {
      controller.abort();
      clearInterval(timer);
    };
  }, [refresh]);

  const chooseSport = (value: Sport | "") => {
    setSport(value);
    setOffset(0);
  };
  const clear = () => {
    setInput("");
    setQuery("");
    setSport("");
    setOffset(0);
  };
  const hasFilters = !!(sport || input);

  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to player catalog
      </a>
      <aside className="sidebar">
        <a href="/" className="brand" aria-label="RosterIQ home">
          <span className="brand-mark">
            R<span>↗</span>
          </span>
          Roster<span className="brand-iq">IQ</span>
        </a>
        <div className="sidebar-body">
          <p className="nav-label">WORKSPACE</p>
          <nav aria-label="Main navigation">
            <a className="nav-item active" href="#main" aria-current="page">
              <span aria-hidden="true">▦</span> Player catalog{" "}
              <span className="nav-arrow">↗</span>
            </a>
            <a
              className="nav-item"
              href="/docs"
              target="_blank"
              rel="noreferrer"
            >
              <span aria-hidden="true">⌘</span> API reference{" "}
              <span className="nav-arrow">↗</span>
            </a>
          </nav>
        </div>
        <div className="sidebar-note">
          <span className="mini-ball" aria-hidden="true">
            ✳
          </span>
          <strong>
            The foundation for
            <br />
            your next great roster.
          </strong>
          <p>NFL + NBA · Learning edition</p>
          <span className="version">ROSTERIQ / 0.1</span>
        </div>
      </aside>
      <div className="workspace">
        <header className="topbar">
          <span>
            Workspace <span className="breadcrumb-separator">/</span>{" "}
            <strong>Player catalog</strong>
          </span>
          <span className={`connection ${ready}`} role="status">
            <i />
            {ready === "online"
              ? "Backend connected"
              : ready === "offline"
                ? "Backend unavailable"
                : "Checking backend"}
          </span>
        </header>
        <main id="main">
          <section className="page-heading">
            <div>
              <p className="eyebrow">YOUR ROSTER STARTS HERE</p>
              <h1>Know the field.</h1>
              <p className="intro">Explore the players. Find your edge.</p>
            </div>
            <button
              className="button refresh"
              onClick={() => setRefresh((value) => value + 1)}
            >
              <span aria-hidden="true">↻</span> Refresh catalog
            </button>
          </section>
          <section className="stats" aria-label="Catalog summary">
            {[
              {
                title: "Players in catalog",
                value: counts?.all,
                label: "Across all sports",
                icon: "↗",
                kind: "total",
              },
              {
                title: "NFL players",
                value: counts?.nfl,
                label: "Football",
                icon: "◈",
                kind: "nfl",
              },
              {
                title: "NBA players",
                value: counts?.nba,
                label: "Basketball",
                icon: "◎",
                kind: "nba",
              },
            ].map((stat) => (
              <article className={`stat-card ${stat.kind}`} key={stat.title}>
                <div className="stat-top">
                  <span>{stat.title}</span>
                  <span className="stat-icon" aria-hidden="true">
                    {stat.icon}
                  </span>
                </div>
                <strong>
                  {stat.value === undefined ? "—" : format(stat.value)}
                </strong>
                <p>{stat.label}</p>
              </article>
            ))}
          </section>
          <section className="catalog" aria-labelledby="catalog-heading">
            <div className="catalog-title">
              <div>
                <h2 id="catalog-heading">
                  Player catalog <span className="small-badge">NFL + NBA</span>
                </h2>
                <p>Your player directory, connected to the source.</p>
              </div>
              <span className="catalog-decoration" aria-hidden="true">
                ↗
              </span>
            </div>
            <div className="toolbar">
              <div
                className="sport-tabs"
                role="group"
                aria-label="Filter by sport"
              >
                {(["", "NFL", "NBA"] as const).map((value) => (
                  <button
                    key={value}
                    aria-pressed={sport === value}
                    className={sport === value ? "selected" : ""}
                    onClick={() => chooseSport(value)}
                  >
                    {value || "All sports"}
                  </button>
                ))}
              </div>
              <div className="search-field">
                <span aria-hidden="true">⌕</span>
                <input
                  aria-label="Search players by name"
                  placeholder="Search players by name…"
                  value={input}
                  maxLength={150}
                  onChange={(event) => setInput(event.target.value)}
                />
                {input && (
                  <button
                    aria-label="Clear search"
                    onClick={() => setInput("")}
                  >
                    ×
                  </button>
                )}
              </div>
            </div>
            <div className="result-meta">
              <span aria-live="polite">
                {loading
                  ? "Loading players…"
                  : error
                    ? "Catalog unavailable"
                    : `${format(page?.total ?? 0)} ${hasFilters ? "matching players" : "players"}`}
              </span>
              {hasFilters && (
                <button className="text-button" onClick={clear}>
                  Clear filters
                </button>
              )}
            </div>
            {loading ? (
              <div className="table-state" role="status">
                <span className="spinner" />
                Loading your player catalog…
              </div>
            ) : error ? (
              <div className="table-state" role="alert">
                <span className="state-symbol">↻</span>
                <h3>Couldn’t load the catalog.</h3>
                <p>Check the backend connection and try again.</p>
                <button
                  className="button"
                  onClick={() => setRefresh((value) => value + 1)}
                >
                  Try again
                </button>
              </div>
            ) : page?.items.length ? (
              <>
                <div className="table-scroll">
                  <table>
                    <thead>
                      <tr>
                        <th>PLAYER</th>
                        <th>SPORT</th>
                        <th>TEAM</th>
                        <th>POSITION</th>
                        <th>SOURCE</th>
                        <th>
                          <span className="sr-only">Details</span>
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {page.items.map((player) => (
                        <tr key={player.id}>
                          <td>
                            <button
                              className="player-name"
                              onClick={() => setSelected(player.id)}
                            >
                              <span
                                className={`avatar ${player.sport.toLowerCase()}`}
                                aria-hidden="true"
                              >
                                {player.name
                                  .split(" ")
                                  .map((part) => part[0])
                                  .slice(0, 2)
                                  .join("")}
                              </span>
                              <span>{player.name}</span>
                            </button>
                          </td>
                          <td>
                            <span
                              className={`sport-badge ${player.sport.toLowerCase()}`}
                            >
                              <span aria-hidden="true">
                                {player.sport === "NFL" ? "◈" : "◎"}
                              </span>{" "}
                              {player.sport}
                            </span>
                          </td>
                          <td>
                            {player.team || (
                              <span className="muted">Not listed</span>
                            )}
                          </td>
                          <td>
                            <span className="position">
                              {player.position || "—"}
                            </span>
                          </td>
                          <td>
                            <span className="source">{player.provider}</span>
                          </td>
                          <td>
                            <button
                              className="row-arrow"
                              aria-label={`View ${player.name}`}
                              onClick={() => setSelected(player.id)}
                            >
                              ↗
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
                <div className="pagination">
                  <span>
                    Showing{" "}
                    <strong>
                      {format(offset + 1)}–{format(offset + page.items.length)}
                    </strong>{" "}
                    of <strong>{format(page.total)}</strong>
                  </span>
                  <div>
                    <button
                      className="button"
                      disabled={offset === 0}
                      onClick={() =>
                        setOffset((value) => Math.max(0, value - 20))
                      }
                    >
                      ← Previous
                    </button>
                    <button
                      className="button"
                      disabled={offset + page.limit >= page.total}
                      onClick={() => setOffset((value) => value + 20)}
                    >
                      Next →
                    </button>
                  </div>
                </div>
              </>
            ) : (
              <div className="table-state">
                <span className="state-symbol">⌕</span>
                <h3>
                  {hasFilters
                    ? "No players match your search."
                    : "A fresh start for your roster."}
                </h3>
                <p>
                  {hasFilters
                    ? "Try another name or choose a different sport."
                    : "Import a player catalog to start exploring."}
                </p>
                {hasFilters && (
                  <button className="button" onClick={clear}>
                    Clear filters
                  </button>
                )}
              </div>
            )}
          </section>
          <footer className="page-footer">
            <span>
              <span className="footer-dot" /> Built on real player data.
            </span>
            <span>One player. Every possibility.</span>
          </footer>
        </main>
      </div>
      {selected && (
        <PlayerDetails
          key={selected}
          id={selected}
          onClose={() => setSelected(null)}
        />
      )}
    </div>
  );
}
