# coding: UTF-8
import xbmc, xbmcgui

import sys, re
import json
import requests
import urllib3
from datetime import datetime, timedelta
import base64
from resources.lib.brotlipython import brotlidec


if sys.version_info >= (3,0,0):
# for Python 3
    to_unicode = str

    from urllib.parse import unquote, quote

else:
    # for Python 2
    to_unicode = unicode

    from urllib import unquote, quote


def resp_text(resp):
    """Return decoded response text."""
    if resp and resp.headers.get('content-encoding') == 'br':
        out = []
        # terrible implementation but it's pure Python
        return brotlidec(resp.content, out).decode('utf-8')
    return resp.text


urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def debug_write(name, text):
    if 0:
        with open('/tmp/%s' % name, 'wb') as f:
            f.write(text.encode('utf-8'))


class Televio:
    def __init__(self, plugin, fanartx, ikona ):

    
        self.plugin = plugin
        self.fanart  = fanartx
        self.ikona  = ikona
        self.datapath = self.plugin.translate_path(self.plugin.get_path('profile'))
        try:
            self.kukis = self.plugin.load_file(self.datapath+'kukis', isJSON=True)
        except:
            self.kukis = {}

        self.UA ='Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:93.0) Gecko/20100101 Firefox/93.0'

        self.headers = {
            'User-Agent': self.UA,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Accept-Language': 'pl,en-US;q=0.7,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'close',
        }

        self.login = self.plugin.get_setting('login')
        self.password = self.plugin.get_setting('password')
        self._sess = None

    @property
    def sess(self):
        if self._sess is None:
            self._sess = requests.Session()
            if self.kukis:
                self._sess.cookies.update(self.kukis)
        return self._sess

    def home(self):
        user = self.logowanie()
        if user is None:
            self.plugin.add_item('film', 'Zaloguj', 'DefaultUser.png', "loguj", folder=False, fanart=self.fanart)
        else:
            self.plugin.add_item('film', 'Zalogowany jako: %s' % user, 'DefaultUser.png', "  ", folder=True, infoLabels={'plot': user}, fanart=self.fanart)
            self.plugin.add_item('film', 'Telewizja', 'DefaultMovies.png', "listtv", folder=True, fanart=self.fanart)
            self.plugin.add_item('film', 'Radio', 'DefaultMovies.png', "listradio", folder=True, fanart=self.fanart)
        self.plugin.EOD()

    def request_sess(self, url, method='get', headers={}, data='', cookies={}, result=True, json=False, allow=True):
        if method == 'get':
            resp = self.sess.get(url, headers=headers, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
        elif method == 'post':
            resp = self.sess.post(url, headers=headers, data=data, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
        elif method == 'delete':
            resp = self.sess.delete(url, headers=headers, cookies=cookies, timeout=15, verify=False, allow_redirects=allow)
        if result:
            return resp.json() if json else resp_text(resp)
        else:
            return resp

    def logowanie(self):
        if self.login and self.password:
            if self.kukis and 'PHPSESSID' in self.kukis:
                # check if loged - try to get profile (small page)
                html = self.request_sess('https://televio.pl/account/profile', 'get', headers=self.headers)
                if 'Kod pocztowy' in html:
                    return self.login
            data = 'username={}&password={}&save=on&login=Zaloguj+si%C4%99&_do=userLoginControl-signInForm-submit'.format(
                quote(self.login), quote(self.password))
            headers = dict(self.headers)
            headers.update({'Content-Type': 'application/x-www-form-urlencoded', 'Referer': 'https://televio.pl/welcome/login'})
            resp = self.request_sess('https://televio.pl/welcome/login', 'post', headers=headers, data=data, result=False)
            html = resp_text(resp)
            debug_write('a.html', html)

            r = re.search(r'/profile/edit/(\d+)', html)
            if r:
                resp = self.request_sess('https://televio.pl/profile/default/%s?do=switchProfile' % r.group(1),
                                         'get', headers=self.headers, result=False)
                self.plugin.save_file(file=self.datapath+'kukis', data=self.sess.cookies.get_dict(), isJSON=True)
                debug_write('a2.html', resp_text(resp))
                return self.login

            # stare, chyba już nie działa
            if self.login in html:
                self.plugin.save_file(file=self.datapath+'kukis', data=self.sess.cookies.get_dict(), isJSON=True)
                return self.login

            if 'href="/home/logout"' in html:
                xbmc.log('Login without data, strange...', xbmc.LOGWARNING)
                self.plugin.save_file(file=self.datapath+'kukis', data=self.sess.cookies.get_dict(), isJSON=True)
                return self.login

            self.plugin.notification_dialog('[B]Uwaga[/B]', '[B]Błąd logowania[/B]', xbmcgui.NOTIFICATION_INFO, 8000, False)
        else:
            self.plugin.notification_dialog('[B]Uwaga[/B]', '[B]Brak danych logowania[/B]', xbmcgui.NOTIFICATION_INFO, 8000, False)

    def listTV(self):
        html = self.request_sess('https://televio.pl/home', 'get', headers=self.headers, cookies=self.kukis)
        debug_write('b.html', html)

        js = re.search('var options = ({.*?});\s*?var PLAYBACK', html, re.DOTALL)
        if not js:
            raise ValueError('TELEVIO: "options" not found')
        js = re.sub(r"'([^']*)'", r'"\1"', js.group(1))
        debug_write('b1.json', js)
        debug_write('b.html', html)
        js = json.loads(js)

        drmId = js.get('drmId', None)
        format = js.get('format', None)
        playSession = js.get('playSession', None)
        licenseUrl = (js.get('drmData', None).get('licenseUrl', None)).split('{')[0]

        epglist = self.request_sess('https://televio.pl/playback/epg-playing?playlist=1', 'get', headers=self.headers, cookies = self.kukis, json=True)
        
        js = re.search('var livePlaylist = ({.*?});\s*?PLAYBACK', html, re.DOTALL)
        if not js:
            raise ValueError('TELEVIO: "livePlaylist" not found')
        js = re.sub(r"'([^']*)':", r'"\1":', js.group(1))
        debug_write('c1.json', js)
        debug_write('c.html', html)
        js = json.loads(js)
        livePlaylist = re.findall('var liveplaylist = ({.*?});.*?playback.set',html,re.DOTALL+re.I)
        livePlaylist = livePlaylist[0].replace("\'",'"').replace("\n            ",'').replace("\n",'')
        livePlaylist = json.loads(livePlaylist)

        snippet = re.findall('snippet\-\-channels(.*?)class="grid"',html,re.DOTALL)[0]
        items = re.findall('item_(.*?)".*?url\((\/.*?)\)',snippet,re.DOTALL)
        for x,y in items:
            val=livePlaylist.get(x,None)

            name = val.get('name', None)
            url = val.get('url', None)
            drm = val.get('drm', None)
            canSeek = val.get('canSeek', None)
            plotmain = epglist.get(x, None)#name
            if plotmain:
                p1 = plotmain.get("title", None)
                p2 = re.findall('(\d+\:.*?)$',plotmain.get("startTime", None))[0]
                p3 = re.findall('(\d+\:.*?)$',plotmain.get("endTime", None))[0]
                plot = '[COLOR khaki]%s - %s[/COLOR] : %s '%(p2, p3, p1)
            else:
                plot =''
            kukz=''.join(['%s=%s;'%(cn, cv) for (cn,cv) in (self.kukis).items()])
            hea= '&'.join(['%s=%s' % (xz, yz) for (xz, yz) in (self.headers).items()])  
            id = url+'|'+hea+'&Cookie='+kukz
            
            poster = 'https://televio.pl/cache/logos/%s.png'%x

            if drm:
            
                if sys.version_info >= (3,0,0):
                    ad = base64.b64encode(url.encode(encoding='utf-8', errors='strict'))
                

                    ad = ad.decode(encoding='utf-8', errors='strict')
                else:
                    ad = base64.b64encode(url)
                id +='#'+licenseUrl + ad#base64.b64encode(url)

            mode = 'playvid'
            fold = False
            ispla = True
            if canSeek:
                mode = 'listkeczup'
                fold = True
                ispla = False
                id+='!!'+x
                name+=' [COLOR gold](+)[/COLOR]'
            self.plugin.add_item(name=self.plugin.PLchar(name), url=id, mode=mode, image=poster, folder=fold, IsPlayable=ispla, fanart = self.fanart, infoLabels={'plot':self.plugin.PLchar(plot)})

        self.plugin.EOD()
        
    def ListRadio(self):
        
        url = 'https://televio.pl/home/radio'
        html = self.request_sess(url, 'get', headers=self.headers, cookies = self.kukis)

        js = re.findall('var options = ({.*?});.*?var PLAYBACK',html,re.DOTALL)
        js = js[0].replace("\'",'"').replace("\n            ",'').replace("\n",'')
        js = json.loads(js)

        drmId = js.get('drmId', None)
        format = js.get('format', None)
        playSession = js.get('playSession', None)
        licenseUrl = (js.get('drmData', None).get('licenseUrl', None)).split('{')[0]

        livePlaylist = re.findall('var liveplaylist = ({.*?});.*?playback.set',html,re.DOTALL+re.I)
        livePlaylist = livePlaylist[0].replace("\'",'"').replace("\n            ",'').replace("\n",'')
        livePlaylist = json.loads(livePlaylist)

        snippet = re.findall('snippet\-\-channels(.*?)class="grid"',html,re.DOTALL)[0]
        items = re.findall('item_(.*?)".*?url\((\/.*?)\)',snippet,re.DOTALL)
        for x,y in items:
            val=livePlaylist.get(x,None)
        
            name = val.get('name', None)
            url = val.get('url', None)
            drm = val.get('drm', None)
            canSeek = val.get('canSeek', None)

            plot = name
            kukz=''.join(['%s=%s;'%(cn, cv) for (cn,cv) in (self.kukis).items()])
            hea= '&'.join(['%s=%s' % (xz, yz) for (xz, yz) in (self.headers).items()])  
            id = url+'|'+hea+'&Cookie='+kukz
            
            poster = 'https://televio.pl/cache/logos/%s.png'%x

            if drm:
                if sys.version_info >= (3,0,0):
                    ad = base64.b64encode(url.encode(encoding='utf-8', errors='strict'))
                    ad = ad.decode(encoding='utf-8', errors='strict')
                else:
                    ad = base64.b64encode(url)
                
                id +='#'+licenseUrl + ad#base64.b64encode(url)
            mode = 'playvid'
            fold = False
            ispla = True

            self.plugin.add_item(name=self.plugin.PLchar(name), url=id, mode=mode, image=poster, folder=fold, IsPlayable=ispla, fanart = self.fanart, infoLabels={'plot':self.plugin.PLchar(plot)})

        self.plugin.EOD()
    
    
    
    
    def CreateDays(self):

        out = []
        dnitygodnia = ("poniedziałek","wtorek","środa","czwartek","piątek","sobota","niedziela")
        for a in range(7):
            
        
            x=datetime.utcnow()+timedelta(days=-a)
            day = x.weekday()
        
            dzientyg = dnitygodnia[day]
            
            dzien = (x.strftime('%d.%m.'))
            dzien2 = x.strftime('%Y-%m-%d')
            out.append({'dzien':dzientyg+ ' '+dzien, 'tstamp':dzien2}) 
        return out

    def listKeczup(self, idt, program, img):
        program = program.replace('(+)','(na żywo)')

        id,x = idt.split('!!')
        epglist = self.request_sess('https://televio.pl/playback/epg-playing?playlist=1', 'get', headers=self.headers, cookies = self.kukis, json=True)
        plotmain = epglist.get(x, None)
        p1 = plotmain.get("title", None)
        p2 = re.findall('(\d+\:.*?)$',plotmain.get("startTime", None))[0]
        p3 = re.findall('(\d+\:.*?)$',plotmain.get("endTime", None))[0]
        plot = '[COLOR khaki]%s - %s[/COLOR] : %s '%(p2, p3, p1)

        self.plugin.add_item(name=program , url=id, mode='playvid', image=self.ikona, folder=False, IsPlayable=True, fanart = self.fanart, infoLabels={'plot':plot})
        
        out = self.CreateDays()
        for x in out:
            uid = idt+'!!'+str(x.get('tstamp',None))
            self.plugin.add_item(name=x.get('dzien',None) , url=uid, mode='listekczup2', image=img, folder=True, IsPlayable=False, fanart = self.fanart, infoLabels={})

        self.plugin.EOD()
    
    
    def listKeczup2(self, idts, img):
        id,id1,id2 = idts.split('!!')# = 
        url = 'https://televio.pl/epg/part-epg/'+id2+'?limit=12000' 
        html = self.request_sess(url, 'get', headers=self.headers, cookies = self.kukis)
        data = re.findall('id\="channel\-'+id1+'(.*?)<\/tr>',html, re.DOTALL)[0]

        epgs=re.findall('time">([^<]+).*?">(.*?)<\/a>.*?href="([^"]+)',data,re.DOTALL)
        for epg in epgs:

            uid = id+'!!'+epg[2]#+'|'+referenceProgramId
            tit = '[COLOR khaki]%s [/COLOR] %s'%(epg[0], epg[1])
            self.plugin.add_item(name=self.plugin.PLchar(tit) , url=uid, mode='playvid', image=img, folder=False, IsPlayable=True, fanart = self.fanart, infoLabels={'plot':self.plugin.PLchar(tit) })
        self.plugin.EOD()

    def PlayVid(self, id):
        lic_url=''
        license_url = ''
        protocol = 'hls' if not '.mp3' in id else ''
        drm = ''
        mpdurl = id

        if '#' in id:
            if '/home#event' in id:
                mpdurl, id2 = mpdurl.split('!!/home#event%3A')
                mpdurl = re.sub('\/channel\/.+?\?','/timeshift-info?event='+id2+'&',mpdurl)
                mpdurl = re.sub('format\=m3u8', 'format=m3u8%2Fm3u8',mpdurl)  #  format=m3u8

                url,hea = mpdurl.split('|')#[0]

                html = self.request_sess(url, 'get', headers=self.headers, cookies = self.kukis, json=True)
                mpdurl = html.get( 'url', None)
                if '#' in hea:
                    hea,license_url = hea.split('#')

                    if sys.version_info >= (3,0,0):
                        mpdx = base64.b64encode(mpdurl.encode(encoding='utf-8', errors='strict'))
                        mpdx = mpdx.decode(encoding='utf-8', errors='strict')
                    else:
                        mpdx = base64.b64encode(mpdurl)
                    license_url = re.sub('streamURL=.+?','streamURL='+mpdx,license_url)
                mpdurl+='|'+hea
            else:
                mpdurl, license_url = mpdurl.split('#')
            if license_url:
                lic_url = license_url+'|Content-Type=|R{SSM}|'
                drm = 'com.widevine.alpha'

        # xbmc.log(f'TELEVIO: mpdurl={mpdurl!r}, lic={lic_url!r}, proto={protocol!r}, drm={drm!r}', xbmc.LOGWARNING)
        self.plugin.PlayVid(mpdurl, lic_url=lic_url, PROTOCOL=protocol, DRM=drm)

        # https://televio.pl/playback/timeshift?channel=NationalGeographicHD&eventId=NationalGeographicHD:20211210a2cfab1df84ba9c74c5ccc0f8f7a7c53&format=m3u8&session=f2x7yhlmnyt1z3mtv69ui10ue58mozbq&eventStart=2021-12-10+23:00:00&duration=4500&drm=widevine
        # https://4dc-cdn2.hm.cdn.moderntv.eu/ovigo/stream/National_Geographic_HD/20-hls/1639174782-001t-01415541-02250719.m4v?_cdn_attrs=account%3Dovigo%2Cresource%3DNational_Geographic_HD_stream_ln&_cdn_meta=userID%3D672632142%2CdeviceID%3D1601501849&_cdn_session=143697628&_cdn_timestamp=1639607558&_cdn_token=3cc4c321b72af040a16466e1f0ae0a02b221e99d&contentId=ch_nationalgeographichd&contentType=&drmProvider=mdrm_ovigo&drmTypes=widevine&packager=1&stream=video%3A0&trackType=HD
        # https://televio.pl/account/devices?deviceId=965393583&do=removeDevice

