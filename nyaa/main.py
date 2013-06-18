from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import toUnicode, tryUrlencode
from couchpotato.core.helpers.variable import tryInt, cleanHost
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentMagnetProvider
from couchpotato.environment import Env
import re
import time
import traceback

log = CPLog(__name__)


class NyaaTorrents(TorrentMagnetProvider):

    urls = {
         'test': 'http://www.nyaa.eu/',
         'detail': 'http://www.nyaa.eu/?page=view&tid=%s',
         'search': 'http://www.nyaa.eu/?page=search&cats=1_37&filter=0&term=%s&sort=2'
    }

    cat_ids = [
       (['1_37'], ['English-translated Anime'])
    ]

    cat_backup_id = None
    disable_provider = False
    http_time_between_calls = 0

    proxy_list = [
        'http://www.nyaa.eu/',
    ]

    def __init__(self):
        self.domain = self.conf('domain')
        super(NyaaTorrents, self).__init__()

    def _searchOnTitle(self, title, movie, quality, results):

        page = 0
        total_pages = 1

        while page < total_pages:

            search_url = self.urls['search'] % (self.getDomain(), tryUrlencode('"%s" %s' % (title, movie['library']['year'])), page, self.getCatId(quality['identifier'])[0])
            page += 1

            data = self.getHTMLData(search_url)

            if data:
                try:
                    soup = BeautifulSoup(data)
                    results_table = soup.find('table', attrs = {'class': 'tlist'})

                    if not results_table:
                        return

                    try:
                        total_pages = len(soup.find('table', attrs = {'class': 'tlistpages'}).find_all('a'))
                    except:
                        pass

                    entries = results_table.find_all('tr')
                    for result in entries[2:]:
                        link = result.find(href = re.compile('torrent\/\d+\/'))
                        download = result.find(href = re.compile('download'))

                        try:
                            size = re.search('Size (?P<size>.+),', unicode(result.select('td.tlistsize')[0])).group('size')
                        except:
                            continue

                        if link and download:

                            def extra_score(item):
                                trusted = (0, 10)[result.find('tr', attrs = {'class': 'trusted'}) != None]
                                vip = (0, 20)[result.find('tr', attrs = {'class': 'trusted'}) != None]
                                confirmed = (0, 30)[result.find('tr', attrs = {'class': 'remake'}) != None]
                                moderated = (0, 50)[result.find('tr', attrs = {'class': 'aplus'}) != None]

                                return confirmed + trusted + vip + moderated

                            results.append({
                                'id': re.search('/(?P<id>\d+)/', link['href']).group('id'),
                                'name': link.string,
                                'url': download['href'],
                                'detail_url': self.getDomain(link['href']),
                                'size': self.parseSize(size),
                                'seeders': tryInt(result.find_all('td')[4].string),
                                'leechers': tryInt(result.find_all('td')[5].string),
                                'extra_score': extra_score,
                                'get_more_info': self.getMoreInfo
                            })

                except:
                    log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))


    def isEnabled(self):
        return super(NyaaTorrents, self).isEnabled() and self.getDomain()

    def getDomain(self, url = ''):

        if not self.domain:
            for proxy in self.proxy_list:

                prop_name = 'tpb_proxy.%s' % proxy
                last_check = float(Env.prop(prop_name, default = 0))
                if last_check > time.time() - 1209600:
                    continue

                data = ''
                try:
                    data = self.urlopen(proxy, timeout = 3, show_error = False)
                except:
                    log.debug('Failed nyaa proxy %s', proxy)

                if 'title="Nyaa Search"' in data:
                    log.debug('Using proxy: %s', proxy)
                    self.domain = proxy
                    break

                Env.prop(prop_name, time.time())

        if not self.domain:
            log.error('No Nyaa proxies left, please add one in settings, or let us know which one to add on the forum.')
            return None

        return cleanHost(self.domain).rstrip('/') + url

    def getMoreInfo(self, item):
        full_description = self.getCache('nya.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class':'viewdescription'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item