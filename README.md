# Gimbo

A personal game journaling and tracking desktop app. Track your backlog,
write session diaries, leave final reviews, and keep a screenshot photo
book — all in one moody pink/purple desktop app.

## Download (Windows / Linux)

Prebuilt versions are attached to the [Releases](../../releases) page —
no Python required.

1. Go to the latest release.
2. Download `Gimbo-windows.zip` or `Gimbo-linux.zip`.
3. Unzip it anywhere.
4. **Windows:** double-click `Gimbo.exe` inside the unzipped folder.
   **Linux:** make it executable and run it:
   ```bash
   chmod +x Gimbo
   ./Gimbo
   ```

Your data (`gimbo.db`) is stored separately from the app itself, so
updating to a new release later won't touch your library:
- **Windows:** `%APPDATA%\Gimbo\gimbo.db`
- **Linux:** `~/.local/share/Gimbo/gimbo.db`

> **Linux note:** the binary is built on a recent Ubuntu, so it needs a
> reasonably modern distro (glibc-wise). If it fails to launch on an
> older distro, running from source (below) always works regardless of
> distro version.

## Running from source

Requires Python 3.10+.

```bash
git clone https://github.com/<your-username>/gimbo.git
cd gimbo
pip install -r requirements.txt
python main.py
```

Works the same way on Windows, macOS, and Linux. `gimbo.db` is created
automatically next to the project on first run.

## Building your own executable

If you'd rather build it yourself instead of using a prebuilt release:

```bash
pip install -r requirements.txt
pip install pyinstaller
pyinstaller gimbo.spec
```

The finished app appears at `dist/Gimbo/` — ship the whole folder (it
contains the executable plus the Qt libraries, fonts, and assets it
needs). On Linux you may need `libegl1`, `libxkbcommon0`, and
`libxcb-cursor0` installed for Qt to run.

## Automated builds

Pushing a version tag (e.g. `git tag v1.0.0 && git push --tags`) triggers
[`.github/workflows/release.yml`](.github/workflows/release.yml), which
builds Windows and Linux binaries in CI and attaches them to a new
GitHub Release automatically. You can also trigger it manually from the
**Actions** tab.

## Tech stack

- Python + PySide6 (Qt)
- SQLite (`db.py`, `schema.sql`)
- Custom QSS styling + ByteBounce pixel font

## License

Add a license of your choice here before making the repo public (MIT is
a common, permissive default if you're not sure).
