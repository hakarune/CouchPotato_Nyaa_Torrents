from bs4 import BeautifulSoup
from couchpotato.core.helpers.encoding import tryUrlencode, toUnicode
from couchpotato.core.helpers.variable import tryInt
from couchpotato.core.logger import CPLog
from couchpotato.core.providers.torrent.base import TorrentMagnetProvider
from urlparse import parse_qs
import re
import traceback

log = CPLog(__name__)


class NyaaTorrents(TorrentMagnetProvider):

    urls = {
         'test': 'http://www.nyaa.eu/',
         'detail': 'http://www.nyaa.eu/?page=view&tid=%s',
         'search': 'http://www.nyaa.eu/?page=search&cats=1_37&filter=0&term=%s&sort=2'
    }
    http_time_between_calls = 0

    def search(self, movie, quality):

        if not quality.get('hd', False):
            return []

        return super(NyaaTorrents, self).search(movie, quality)

    def _searchOnTitle(self, title, movie, quality, results):

        params = tryUrlencode({
            'page':'torrents',
            'search': '%s %s' % (title, movie['library']['year']),
            'active': 1,
        })

        data = self.getHTMLData('%s?%s' % (self.urls['search'], params))

        if data:

            try:
                soup = BeautifulSoup(data)

                results_table = soup.find('table', attrs = {'id': 'tlist'})
                entries = results_table.find_all('tr')

                for result in entries[2:len(entries) - 1]:
                    info_url = result.find(href = re.compile('view'))
                    download = result.find(href = re.compile('download'))

                    if info_url and download:

                        url = parse_qs(info_url['href'])

                        results.append({
                            'id': url['id'][0],
                            'name': info_url.string,
                            'url': download['href'],
                            'detail_url': self.urls['detail'] % url['id'][0],
                            'size': self.parseSize(result.find_all('td')[3].string),
                            'seeders': tryInt(result.find_all('td')[4].string),
                            'leechers': tryInt(result.find_all('td')[5].string),
                            'get_more_info': self.getMoreInfo
                        })

            except:
                log.error('Failed getting results from %s: %s', (self.getName(), traceback.format_exc()))

    def getMoreInfo(self, item):
        full_description = self.getCache('nyaa.%s' % item['id'], item['detail_url'], cache_timeout = 25920000)
        html = BeautifulSoup(full_description)
        nfo_pre = html.find('div', attrs = {'class':'remake'})
        description = toUnicode(nfo_pre.text) if nfo_pre else ''

        item['description'] = description
        return item