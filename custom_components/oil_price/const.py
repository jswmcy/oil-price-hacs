"""Constants for the China Oil Price integration."""

from datetime import timedelta

from homeassistant.const import Platform

DOMAIN = "oil_price"
PLATFORMS = [Platform.SENSOR]

ICON_STATION = "mdi:gas-station"
ICON_HINT = "mdi:information-outline"

UNIT_PRICE = "元/升"

CONF_REGION = "region"
CONF_SCAN_INTERVAL_HOURS = "scan_interval_hours"

DEFAULT_NAME = "油价"
DEFAULT_REGION = "jiangsu"
DEFAULT_SCAN_INTERVAL = timedelta(hours=8)
DEFAULT_TIMEOUT = 15  # seconds

BASE_URL = "http://www.qiyoujiage.com/{region}.shtml"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)

# key = the token we match against the page's <dt> text (e.g. "江苏92#汽油")
# label = human-readable suffix used in the entity name
OIL_TYPES = ("92#", "95#", "98#", "0#")
