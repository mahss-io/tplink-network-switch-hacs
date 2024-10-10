
# Home Assistant - TP Link Managed Switch Integration

This is a custom component to allow networking statistics to be pulled from TP-Link Managed Switches. This is based on a script wirtten by

### Features
* Creates a device for the switch and a device for each port currently in use by the switch with an active network connection
* The network switch device shows total number of network ports as well as network ports currently in use.
* Each active port on the switch gets a device where it has the transmitted, received, failed transmitted, and failed received packets.

### Known Supported Devices

* TL-SG108E
* TL-SG1016PE

### Devices That Will Probability Work
* TL-SG10*

### Potential Downsides

* Due to how the web portal on theses TP-Link switches authenticates and most likely other reason, using this integration will reduce the time it will keep you logged in to the web interface.
    * This can be circumvented by temporarily disabling this custom component.

## Installation (HACS) - Highly Recommended

1. Have HACS installed, this will allow you to easily update
   repository as Type: Integration
1. Click install under "TP Link Managed Switch Integration" in the Integration tab
1. Restart HA.
1. Navigate to _Integrations_ in the config interface.
1. Click _ADD INTEGRATION_.
1. Search for _TP Link Managed Switch Integration_.
1. Enter your ip address, username and password.
1. Click _SUBMIT_.

## Reporting an Issue

1. Setup your logger to print debug messages for this component by adding this to your `configuration.yaml`:
    ```yaml
    logger:
     default: warning
     logs:
       custom_components.tp-link-managed-switch: debug
       tp-link-managed-switch: debug
    ```
1. Restart HA
1. Verify you're still having the issue
1. File an issue in this Github Repository (being sure to fill out every provided field)

