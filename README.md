# Owncast Parser

Custom component for [Home Assistant](https://www.home-assistant.io) which returns the status of an [Owncast](https://owncast.online) as an entity.

## Installation (via HACS as a custom repository)

1. In Home Assistant, go to your **HACS** Settings and add open **Custom Repositories**.
2. Enter this repository URL, set **Category = Integration**, then **Add**.
3. Find **Owncast Parser** in HACS, **Install**.
4. **Restart** Home Assistant.

## Configuration (UI)

Go to **Settings → Devices & Services → Add Integration**, search for **Owncast Parser**, and enter your server details.

## Configuration (YAML — deprecated)

YAML configuration still works but will auto-import as a config entry on startup. A deprecation warning will be logged. You may remove the YAML block after the first import.

```yaml
sensor:
  - platform: owncastparser
    name: "An Owncast Server"
    url: "https://an-owncast-server.net"
    timeout: 10
    verify_ssl: true
```

**Note:** `scan_interval` is no longer configurable per-sensor. The default polling interval is 1 minute.

## Thanks
A not-insignificant amount of the hass custom_component interface logic was cribbed from [Feedparser](https://github.com/custom-components/feedparser). Please show the project some love if you can.