# Research: Phase 20 — Private VPN Remote Deployment

## Context
Convert the hardened local tool into a persistent service accessible via a Private VPN (e.g., Tailscale, WireGuard). The app should not be public and must not expose its port to the open internet.

## Goals
- Identify how to bind the server to a specific VPN IP instead of just `localhost`.
- Manage configuration (IP, Port, Origins) via environment variables or a dedicated config file.
- Ensure OAuth tokens and credentials are treated as server secrets.
- Define a "headless" mode (no automatic browser opening).
- Establish security rules for remote access (restricting origins to the VPN network).

## Technical Considerations

### 1. Network Binding
Currently, `ThreadingHTTPServer` is hardcoded to `('localhost', PORT)`.
- Change to: `(os.getenv('HOST', 'localhost'), int(os.getenv('PORT', 8765)))`.
- Binding to `0.0.0.0` is discouraged unless strictly firewall-protected; binding to the VPN's internal IP is safer.

### 2. CORS & Security
- `LOCAL_ORIGINS` must include the VPN IP/hostname to allow the browser to talk to the API.
- `LOCAL_HOSTS` must be expanded to include the VPN address.

### 3. Headless Operation
- Disable `webbrowser.open` if a flag (e.g., `HEADLESS=1`) is set.
- Ensure the OAuth flow can still be completed (requires a manual URL copy-paste if no browser is available on the server).

### 4. Environment Variables
Supported variables should include:
- `HOST`: IP to bind (e.g., `100.x.y.z` for Tailscale).
- `PORT`: Port to listen (default `8765`).
- `ALLOWED_ORIGINS`: Comma-separated list of additional allowed origins (VPN IPs).
- `HEADLESS`: `1` to disable auto-browser.
- `ENABLE_PERMANENT_DELETE`: (Existing) `1` to allow destructive actions.

## Deployment Strategy
- Use a `systemd` unit or a simple background process for persistence.
- Document how to set up Tailscale/VPN for the user.
- Document how to handle the initial OAuth handshake in a remote environment.

## Verification Plan
- Run the server bound to a specific IP and verify it's unreachable from other interfaces.
- Verify that authorized VPN origins can access the UI and API.
- Verify that the app starts correctly without attempting to open a browser in headless mode.
