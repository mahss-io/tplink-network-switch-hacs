from datetime import timedelta, datetime
import async_timeout
import aiohttp
import asyncio
import logging
import re
import json

from bs4 import BeautifulSoup

from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.exceptions import ConfigEntryNotReady

_LOGGER = logging.getLogger(__name__)

from .const import (
    DOMAIN,
    LOGON_ENDPOINT,
    LOGOUT_ENDPOINT,
    PORT_STATISTICS_ENDPOINT,
    SYSTEM_INFO_ENDPOINT,

    DESCRIPTION_KEY,
    MAC_ADDRESS_KEY,
    FIRMWARE_VERSION_KEY,
    HARDWARE_VERSION_KEY
)

TPlinkStatus = {'0': "Link Down", '1': "LS 1", '2': "10M Half", '3': "10M Full", '4': "LS 4", '5': "100M Full", '6': "1000M Full"}
TPstate = {'0': 'Disabled', '1': 'Enabled'}

class NetworkSwitchDataUpdateCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, host, username, password):
        """Initialize the coordinator."""
        self.base_url = "http://" + host
        self.username = username
        self.password = password
        self.session = aiohttp.ClientSession(headers={'Referer': self.base_url})

        self.getInitData = False

        update_interval = timedelta(seconds=60)
        super().__init__(
            hass,
            _LOGGER,
            name="TP-Link Network Switch",
            update_interval=update_interval,
        )

    async def _async_update_data(self):
        toReturn = {}
        await self.getAuthCookies()

        if not self.getInitData:
            toReturn.update(await self.getSystemStats())
        toReturn.update(await self.getPortStats())

        return toReturn

    async def getAuthCookies(self):
        data = {"logon": "Login", "username": self.username, "password": self.password}
        postHeaders = { 'Referer': f'{self.base_url}{LOGOUT_ENDPOINT}'}
        try:
            async with self.session.post(f'{self.base_url}{LOGON_ENDPOINT}', data=data, headers=postHeaders, timeout=5) as postResponse:
                if postResponse.status != 200:
                    raise UpdateFailed(f"Error {postResponse.status} from switch login")
                post_data = await postResponse.text()
                self.session.cookie_jar.update_cookies(postResponse.cookies)
        except Exception as err:
            raise UpdateFailed(f"Error fetching session cookie: {err}")

    async def getPortStats(self):
        getHeaders = {'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                      'Upgrade-Insecure-Requests': "1" }
        toReturn = {}

        try:
            async with self.session.get(f'{self.base_url}{PORT_STATISTICS_ENDPOINT}', headers=getHeaders, timeout=6) as getResponse:
                if getResponse.status != 200:
                    raise UpdateFailed(f"Error {getResponse.status} from API")

                soup = BeautifulSoup(await getResponse.text(), 'html.parser')

                convoluted = (soup.script == soup.head.script)     #TL-SG1016DE and TL-SG108E models have a script before the HEAD block
                if convoluted:
                    # This is the 24 port TL-SG1024DE model with the stats in a different place (and convoluted coding)
                    _LOGGER.debug(soup.head.find_all("script"))
                    _LOGGER.debug(soup.body.script)
                else:
                    # This should be a TL-SG1016DE or a TL-SG108E
                    _LOGGER.debug(soup.script)

                pattern = re.compile(r"var (max_port_num) = (.*?);", re.MULTILINE)

                current_dt = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if convoluted:
                    max_port_num = int(pattern.search(str(soup.head.find_all("script"))).group(2))
                else:
                    max_port_num = int(pattern.search(str(soup.script)).group(2))

                _LOGGER.debug("max_port_num={0:d}".format(max_port_num))
                toReturn.update({
                    'total_ports': max_port_num
                })

                if convoluted:
                    i1 = re.compile(r'tmp_info = "(.*?)";$', re.MULTILINE | re.DOTALL).search(str(soup.body.script)).group(1)
                    i2 = re.compile(r'tmp_info2 = "(.*?)";$', re.MULTILINE | re.DOTALL).search(str(soup.body.script)).group(1)
                    # We simulate bug for bug the way the variables are loaded on the "normal" switch models. In those, each
                    # data array has two extra 0 cells at the end. To remain compatible with the balance of the code here,
                    # we need to add in these redundant entries so they can be removed later. (smh)
                    script_vars = ('tmp_info:[' + i1.rstrip() + ' ' + i2.rstrip() + ',0,0]').replace(" ", ",")
                else:
                    script_vars = re.compile(r"var all_info = {\n?(.*?)\n?};$", re.MULTILINE | re.DOTALL).search(str(soup.script)).group(1)

                entries = re.split(",?\n+", script_vars)

                edict = {}
                drop2 = re.compile(r"\[(.*),0,0]")
                for entry in entries:
                    e2 = re.split(":", entry)
                    edict[str(e2[0])] = drop2.search(e2[1]).group(1)

                if convoluted:
                    e3 = {}
                    e4 = {}
                    e5 = {}
                    ee = re.split(",", edict['tmp_info'])
                    for x in range (0, max_port_num):
                        e3[x] = ee[(x*6)]
                        e4[x] = ee[(x*6)+1]
                        e5[(x*4)] = ee[(x*6)+2]
                        e5[(x*4)+1] = ee[(x*6)+3]
                        e5[(x*4)+2] = ee[(x*6)+4]
                        e5[(x*4)+3] = ee[(x*6)+5]
                else:
                    e3 = re.split(",", edict['state'])
                    e4 = re.split(",", edict['link_status'])
                    e5 = re.split(",", edict['pkts'])

                pdict = {}
                for x in range(1, max_port_num+1):
                    #_LOGGER.debug(x, ((x-1)*4), ((x-1)*4)+1, ((x-1)*4)+2, ((x-1)*4)+3 )
                    pdict[x] = {}
                    pdict[x]['state'] = TPstate[e3[x-1]]
                    pdict[x]['link_status'] = TPlinkStatus[e4[x-1]]
                    pdict[x]['TxGoodPkt'] = e5[((x-1)*4)]
                    pdict[x]['TxBadPkt'] = e5[((x-1)*4)+1]
                    pdict[x]['RxGoodPkt'] = e5[((x-1)*4)+2]
                    pdict[x]['RxBadPkt'] = e5[((x-1)*4)+3]
                
                toReturn.update({
                    'port_data': pdict
                })

                return toReturn
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

    async def getSystemStats(self):
        getHeaders = {'Accept': "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                      'Upgrade-Insecure-Requests': "1" }
        toReturn = {}

        try:
            async with self.session.get(f'{self.base_url}{SYSTEM_INFO_ENDPOINT}', headers=getHeaders, timeout=6) as getResponse:
                if getResponse.status != 200:
                    raise UpdateFailed(f"Error {getResponse.status} from API")

                soup = BeautifulSoup(await getResponse.text(), 'html.parser')
                system_info_string = soup.script
                description = re.search(r'descriStr:\s*\[\s*"([^"]+)"\s*\]', str(system_info_string))
                mac_address = re.search(r'macStr:\[\s*"([0-9A-Fa-f:]+)"\s*\]', str(system_info_string))
                firmware_version = re.search(r'firmwareStr:\s*\[\s*"([^"]+)"\s*\]', str(system_info_string))
                hardware_version = re.search(r'hardwareStr:\s*\[\s*"([^"]+)"\s*\]', str(system_info_string))
                _LOGGER.debug("-----------------------MAC ADDRESS HERE------------------------------")
                _LOGGER.debug(mac_address.group(1))
                toReturn.update({
                    'description': description.group(1),
                    'mac_address': mac_address.group(1),
                    'firmware_version': firmware_version.group(1),
                    'hardware_version': hardware_version.group(1),
                })
                self.getInitData = True
                return {'switch_data': toReturn}
        except Exception as err:
            raise UpdateFailed(f"Error fetching data: {err}")

