# Android (Termux)

Experimentally, Guidebook runs on Android phones via [Termux](https://termux.dev) using
the pre-built Linux ARM64 binary inside a Debian proot environment.
The web UI is usable on phone touch screens, or you can use the phone just as the server, and have other devices access it. Guidebook is primarily
designed for desktop browsers.

```bash
# Install Termux from F-Droid, then:
pkg install proot-distro
proot-distro install debian
proot-distro login debian

# Inside Debian:
apt update && apt install -y wget
wget https://github.com/EnigmaCurry/guidebook/releases/latest/download/guidebook-linux-arm64
chmod +x guidebook-linux-arm64
```

**Important:** Android suspends background apps aggressively. Before
starting guidebook, acquire a wake lock so Termux stays alive when you
switch to the browser:

```bash
# In the debian proot (proot-distro login debian)
termux-wake-lock
./guidebook-linux-arm64
```

While termux is still running in the background, open your Android web browser and go to `http://127.0.0.1:8073` to access mobile Guidebook.

You can also use your phone as just the server, and access Guidebook from
another computer's browser on the same network.  This gives you the full
desktop experience while you keep Guidebook running in your pocket.
Set `GUIDEBOOK_HOST=0.0.0.0` before starting guidebook to listen on all interfaces:

```bash
# Warning: this allows any device to access your phone on port 8073 :
export GUIDEBOOK_HOST=0.0.0.0
termux-wake-lock
./guidebook-linux-arm64
```

Then open `http://<phone-ip>:8073` from any browser on the LAN.

**Warning:** Guidebook has no authentication or encryption — only do
this on trusted networks.
