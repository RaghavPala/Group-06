# Group-06

Group project for CS 3354 - Smart Attendance Tracker.

> **Windows users read first.** The simplest, most compatible dev setup on Windows is to install **WSL 2 with Ubuntu** and do everything below inside the Ubuntu shell. This gives you a real Linux environment that avoids path / line-ending / toolchain differences, and lets Docker Desktop integrate natively.
>
> Open PowerShell as admin and run:
> ```powershell
> wsl --install -d Ubuntu
> ```
> Reboot, set up your Ubuntu username/password, then open the "Ubuntu" app and follow the rest of this README from there.

## Quick Start (Docker — recommended)

This is the fastest way to get a reproducible Postgres instance with the schema and seed data already loaded. Works identically on Linux, macOS, and WSL 2 Ubuntu.

### 0. Install Docker

Verify you already have it:

```bash
docker --version
docker compose version
```

If either command fails, install Docker:

**macOS** (requires macOS within the last 3 major releases, ≥4 GB RAM)
- Official: download the Apple Silicon or Intel `.dmg` from <https://www.docker.com/products/docker-desktop/>, drag Docker to Applications, launch it once, accept the terms.
- Unofficial shortcut: `brew install --cask docker-desktop` also works (community cask; installs the same app).


**Windows 10/11** (64-bit, 8 GB RAM, hardware virtualization enabled in BIOS/UEFI; Win 10 22H2 build 19045+ or Win 11 23H2 build 22631+)
- Install Docker Desktop from <https://www.docker.com/products/docker-desktop/>.
- Default backend is WSL 2 (installer will enable it; reboot may be required). Hyper-V backend also supported if preferred.
- Launch Docker Desktop once before using `docker` from PowerShell / terminal.

**Linux**

Ubuntu / Debian:
```bash
sudo apt-get update
sudo apt-get install -y docker.io docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # log out + back in so `docker` works without sudo
```

Fedora:
```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager addrepo --from-repofile=https://download.docker.com/linux/fedora/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER   # log out + back in
```

RHEL / CentOS Stream / Rocky / Alma:
```bash
sudo dnf -y install dnf-plugins-core
sudo dnf config-manager --add-repo https://download.docker.com/linux/rhel/docker-ce.repo
sudo dnf -y install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

Arch:
```bash
sudo pacman -S docker docker-compose
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
```

After install, confirm:

```bash
docker run --rm hello-world
```

### 1. Create and activate a Python virtual environment

A venv keeps this project's dependencies isolated from your system Python. Create it once inside the repo root:

```bash
python -m venv .venv          # or python3 on some systems, try if needed
```

Activate it every time you open a new terminal:

| Shell                         | Activate                           | Deactivate    |
|-------------------------------|------------------------------------|---------------|
| macOS / Linux / WSL (bash, zsh) | `source .venv/bin/activate`       | `deactivate`  |
| Windows PowerShell            | `.venv\Scripts\Activate.ps1`       | `deactivate`  |
| Windows cmd.exe               | `.venv\Scripts\activate.bat`       | `deactivate`  |

Your prompt should now show `(.venv)` at the front. If PowerShell blocks activation with an execution-policy error, run once in an admin PowerShell: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`.

If Python isn't installed: macOS `brew install python`, Ubuntu/WSL `sudo apt install python3 python3-venv`, Fedora `sudo dnf install python3`.

### 2. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 3. Start Postgres

From the project root:

```bash
docker compose up -d
```

This launches a Postgres container on `localhost:5432` and auto-runs
`db-schema-seeding/schema.sql` followed by `db-schema-seeding/seed.sql` the
first time it boots. The database is named `smart_attendance`, user
`postgres`, password `postgres`.

To reset to a clean, freshly-seeded DB at any time:

```bash
docker compose down -v && docker compose up -d
```

### 4. Point the app at the DB

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/smart_attendance
```

On Windows PowerShell:

```powershell
$env:DATABASE_URL="postgresql://postgres:postgres@localhost:5432/smart_attendance"
```

### 5. Run the app

```bash
python app.py
```

Then open <http://127.0.0.1:5000/>.

Seeded accounts (from `db-schema-seeding/seed.sql`):

| NetID       | Password         | Role       |
|-------------|------------------|------------|
| `proftest`  | `profpass1*`     | Instructor |
| `dal123456` | `password1234*`  | Student    |
| `abc123456` | `password1234*`  | Student    |

### 6. Run the test suite

```bash
pytest -q
```

Tests hit the same seeded DB as the app (no mocks / stubs).

---

## Alternate Setup (native Postgres, no Docker)

If you'd rather install Postgres directly:

1. Install PostgreSQL from <https://www.postgresql.org/download/>.
2. Create the database and load schema + seed:
   ```bash
   createdb smart_attendance
   psql -d smart_attendance -f db-schema-seeding/schema.sql
   psql -d smart_attendance -f db-schema-seeding/seed.sql
   ```
3. Set `DATABASE_URL` to match your install (replace user/password/host as needed):
   ```bash
   export DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/smart_attendance
   ```
4. `python app.py`.

---

## Notes

- The app requires `DATABASE_URL` at startup and will refuse to boot without it.
  Auth and attendance both read from Postgres — there is no in-memory fallback.
- `db-schema-seeding/schema.sql` defines the tables.
- `db-schema-seeding/seed.sql` inserts demo users, courses, enrollments, and a
  currently-active session for `CS3354.001` (the session's attendance window is
  5 minutes — re-seed with `docker compose down -v && docker compose up -d` if
  it expires while you're testing).
