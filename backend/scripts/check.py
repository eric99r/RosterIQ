"""Run the same Linux-container checks locally and in CI. Fail at the first error."""

import os
import subprocess
import sys


def run(*args: str, env: dict[str, str]) -> None:
    print(f"\nRunning: {' '.join(args)}", flush=True)
    subprocess.run([sys.executable, "-m", *args], check=True, env=env)


def main() -> int:
    env = os.environ.copy()
    env.pop("TEST_DATABASE_URL", None)
    try:
        run("ruff", "check", ".", "--no-cache", env=env)
        run("ruff", "format", "--check", ".", "--no-cache", env=env)
        run("pytest", "-q", "-p", "no:cacheprovider", env=env)
        run("alembic", "upgrade", "head", env=env)
        run("alembic", "check", env=env)
        run(
            "pytest",
            "-q",
            "-p",
            "no:cacheprovider",
            env={**env, "TEST_DATABASE_URL": env["DATABASE_URL"]},
        )
        run("alembic", "downgrade", "base", env=env)
        run("alembic", "upgrade", "head", env=env)
        run("alembic", "check", env=env)
    except subprocess.CalledProcessError as exc:
        return exc.returncode
    return 0


if __name__ == "__main__":
    sys.exit(main())
