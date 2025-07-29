# Owncast Parser

Custom component for [Home Assistant](https://www.home-assistant.io) which returns the status of an [Owncast](https://owncast.online) as an entity.

## Installation (via HACS as a custom repository)

1. In Home Assistant, go to your **HACS** Settings and add open **Custom Repositories**.
2. Enter this repository URL, set **Category = Integration**, then **Add**.
3. Find **Owncast Parser** in HACS, **Install**.
4. **Restart** Home Assistant.

## Minimal Configuration (YAML)

```yaml
sensor:
  - platform: owncastparser
    name: "An Owncast Server"
    url: "https://an-owncast-server.net"
```

## Complete Configuration (YAML)

```yaml
sensor:
  - platform: owncastparser
    name: "Your Owncast Site"
    url: "https://your-owncast-site.online/"
    timeout: 10 # fetch limit in seconds
    verify_ssl: true # verify certificates
    scan_interval: 
      minutes: 5 # how often to poll status
```
