"""The JuiceNet integration."""
import asyncio
import logging

from pyjuicenet import Api
import requests
import voluptuous as vol

from homeassistant.components.juicenet.const import DOMAIN
from homeassistant.components.juicenet.device import JuiceNetApi
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv

_LOGGER = logging.getLogger(__name__)

PLATFORMS = ["sensor", "switch"]

CONFIG_SCHEMA = vol.Schema(
    {DOMAIN: vol.Schema({vol.Required(CONF_ACCESS_TOKEN): cv.string})},
    extra=vol.ALLOW_EXTRA,
)


async def async_setup(hass: HomeAssistant, config: dict):
    """Set up the JuiceNet component."""
    conf = config.get(DOMAIN)
    hass.data.setdefault(DOMAIN, {})

    if not conf:
        return True

    hass.async_create_task(
        hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_IMPORT}, data=conf
        )
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Set up JuiceNet from a config entry."""

    config = entry.data

    # Configure API
    access_token = config[CONF_ACCESS_TOKEN]
    api = Api(access_token)

    juicenet = JuiceNetApi(api)

    try:
        await hass.async_add_executor_job(juicenet.setup)
    except ValueError as error:
        _LOGGER.error("JuiceNet Error %s", error)
        return False
    except requests.exceptions.ConnectionError as error:
        _LOGGER.error("Could not reach the JuiceNet API %s", error)
        raise ConfigEntryNotReady

    if not juicenet.devices:
        _LOGGER.error("No JuiceNet devices found for this account")
        return False
    _LOGGER.info("%d JuiceNet device(s) found", len(juicenet.devices))

    hass.data[DOMAIN][entry.entry_id] = juicenet

    for component in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, component)
        )

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry):
    """Unload a config entry."""
    unload_ok = all(
        await asyncio.gather(
            *[
                hass.config_entries.async_forward_entry_unload(entry, component)
                for component in PLATFORMS
            ]
        )
    )
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    return unload_ok
