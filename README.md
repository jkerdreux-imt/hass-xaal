# xAAL Integration for Home Assistant

This project integrates the xAAL protocol into Home Assistant, allowing you to control and monitor xAAL-compatible smart devices (lights, sensors, shutters, etc.) directly from the Home Assistant interface.

## Overview

xAAL is an open protocol for home automation, designed for interoperability between connected devices. This integration exposes xAAL devices as Home Assistant entities and synchronizes states and commands between Home Assistant and the xAAL network.

## Prerequisites

- A working Home Assistant installation
- An accessible xAAL metadata server on your network ([metadata server documentation](https://gitlab.imt-atlantique.fr/xaal/code/python/-/tree/main/core/metadb))
  - Only the UUID of the metadata server is required for configuration.
(Home Assistant will automatically install the required Python dependencies, including `xaal.monitor`.)

## Installation

1. Copy the `xaal/` folder into the `custom_components/` directory of your Home Assistant installation.
2. Restart Home Assistant.

## Configuration

Configure the xAAL integration via the Home Assistant UI:

1. Go to **Settings > Integrations**.
2. Add a new integration and search for "xAAL".
3. Enter the UUID of your xAAL metadata server.

## Supported Features

- **Lights**: on/off, color, brightness, color temperature
- **Switches/Outlets**: on/off
- **Sensors**: temperature, humidity, pressure, battery, power, current, voltage, CO2, illuminance, link quality, etc.
- **Binary sensors**: motion, contact, button
- **Covers/Shutters**: open/close, position, stop
- **Sirens**: activate/deactivate, duration
- **TTS (Text-to-Speech)**: send voice messages via xAAL

## Example Usage

Once configured, xAAL devices will automatically appear as entities in Home Assistant. You can:
- Control your xAAL lights from the dashboard
- Automate shutter opening based on weather
- Receive notifications from sensors
- Use xAAL buttons to trigger automations

## Useful Links

- [xAAL Documentation](https://recherche.imt-atlantique.fr/xaal/)
- [Home Assistant](https://www.home-assistant.io/)

## Support & Contribution

For questions or suggestions, open an issue on the repository or contact the code owner:
- @jkerdreux-imt

Contributions are welcome!

---

**License**: This project is open source. See the LICENSE file for details.
