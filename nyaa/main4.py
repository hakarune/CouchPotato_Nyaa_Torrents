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
         'detail': '%s/?page=view&tid=%s',
         'search': '%s/?page=search&cats=1_37&filter=0&term=%s&sort=2'
    }

    cat_ids = [
        (['1_37'], ['English-translated Anime'])
    ]

    http_time_between_calls = 1 #seconds
    cat_backup_id = None

    def _search(self, movie, quality, results):

        data = self.getHTMLData(self.urls['search'] % ('m', movie['library']['identifier'].replace('tt', '')))

        if data:

            cat_ids = self.getCatId(quality['identifier'])
            table_order = ['category', 'name', 'download', 'size', 'seeds', 'leechers']

            try:
                html = BeautifulSoup(data)
                resultdiv = html.find('div', attrs = {'class':'tabs'})
                for result in resultdiv.find_all('div', recursive = False):
                    if result.get('id').lower() not in cat_ids:
                        continue

                    try:
                        for temp in result.find_all('tr'):
                            if temp['class'] is 'firstr' or not temp.get('id'):
                                continue

                            new = {}

                            nr = 0
                            for td in temp.find_all('td'):
                                column_name = table_order[nr]
                                if column_name:

                                    if column_name is 'name':
                                        link = td.find('td', {'class': 'tlistname'}).find_all('a')[1]
                                        new['id'] = temp.get('id')[-8:]
                                        new['name'] = link.text
                                        new['url'] = td.find('a', 'tlistdownload')['href']
                                        new['detail_url'] = self.urls['detail'] % link['href'][1:]
                                        new['score'] = 20 if td.find('a', 'iverif') else 0
                                    elif column_name is 'size':
                                        new['size'] = self.parseSize(td.text)
                                    elif column_name is 'seeds':
                                        new['seeders'] = tryInt(td.text)
                                    elif column_name is 'leechers':
                                        new['leechers'] = tryInt(td.text)

                                nr += 1

                            results.append(new)
                    except:
                        log.error('Failed parsing NyaaTorrents: %s', traceback.format_exc())

            except AttributeError:
                log.debug('No search results found.')

    def ageToDays(self, age_str):
        age = 0
        age_str = age_str.replace('&nbsp;', ' ')

        regex = '(\d*.?\d+).(sec|hour|day|week|month|year)+'
        matches = re.findall(regex, age_str)
        for match in matches:
            nr, size = match
            mult = 1
            if size == 'week':
                mult = 7
            elif size == 'month':
                mult = 30.5
            elif size == 'year':
                mult = 365

            age += tryInt(nr) * mult

        return tryInt(age)