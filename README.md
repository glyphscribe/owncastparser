# Owncast Parser

*this does stuff. update later.*

## Installation (via HACS as a custom repository)

1. In Home Assistant, go to **HACS → (⋮) → Custom repositories**.
2. Enter this repository URL, set **Category = Integration**, then **Add**.
3. Find **Owncast Parser** in HACS, **Install**.
4. **Restart** Home Assistant.

## Configuration (YAML)

```yaml
sensor:
  - platform: owncastparser
    name: "Your Owncast Site"
    url: "https://your-owncast-site.net/"
```
