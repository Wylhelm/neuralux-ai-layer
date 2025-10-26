# Overlay Assistant Guide

## Features

- GTK4 command palette with fuzzy search
- LLM integration via NATS
- File search (/search) and health (/health) shortcuts
- X11 hotkey support; Wayland-friendly control via signals
- Tray icon (Ayatana/AppIndicator) with toggle and quit

## Install prerequisites (Ubuntu/Debian)

```bash
sudo apt install -y python3-gi gir1.2-gtk-4.0 libgtk-4-1 libgtk-4-bin
# Optional tray support
sudo apt install -y gir1.2-ayatanaappindicator3-0.1 libayatana-appindicator3-1
```

## Launch

```bash
aish overlay                    # Start overlay (no hotkey)
aish overlay --hotkey           # Enable Ctrl+Space (X11 only)
aish overlay --hotkey --tray    # Enable both hotkey and tray (recommended)
```

**Note:** The `--hotkey` flag is **required** to enable the global Ctrl+Space hotkey. Without it, you can only toggle the overlay via tray icon or `aish overlay --toggle`.

## Control an existing instance

```bash
aish overlay --toggle    # Toggle visibility
aish overlay --show      # Show/focus
aish overlay --hide      # Hide
```

Bind these to a desktop shortcut on Wayland. The app listens on NATS subjects: `ui.overlay.toggle`, `ui.overlay.show`, `ui.overlay.hide`, `ui.overlay.quit`.

## Desktop integration

```bash
make desktop     # Install launcher "Neuralux Overlay"
make autostart   # Start on login (optional)
```

## Wayland notes

- Global hotkeys are restricted. Create a DE shortcut to run `aish overlay --toggle`.
- Tray availability depends on AppIndicator support in your DE.

## Troubleshooting

### Ctrl+Space not working
**Most common issue:** You must pass the `--hotkey` flag when launching:
```bash
aish overlay --hotkey --tray    # Correct
aish overlay --tray             # Wrong - no hotkey!
```

Check if hotkey is enabled:
```bash
ps aux | grep "aish overlay"
# Should show: aish overlay --hotkey --tray
```

### Other issues
- **"Failed to load GTK4 overlay"**: Install GTK bindings (see prerequisites).
- **Hotkey not capturing**: Ensure you're on X11 (not Wayland). Check `echo $XDG_SESSION_TYPE`.
- **Tray missing**: Install Ayatana AppIndicator packages; the app will try an external helper automatically.
- **Overlay behind windows on X11**: `sudo apt install -y wmctrl && wmctrl -x -r com.neuralux.overlay -b add,above,sticky`.

## Environment variables

```bash
export OVERLAY_ENABLE_TRAY=true
export OVERLAY_APP_NAME="Neuralux"
export OVERLAY_TRAY_ICON="$PWD/packages/overlay/assets/neuralux-tray.svg"
```


