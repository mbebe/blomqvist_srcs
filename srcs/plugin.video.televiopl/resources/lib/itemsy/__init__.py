# coding: UTF-8

import sys

if sys.version_info >= (3,0,0):
    from urllib.parse import urlencode
    to_unicode = str

else:
    from urllib import urlencode
    to_unicode = unicode
    
import xbmcplugin, xbmcgui
import xbmcvfs, xbmc

import io, os
import calendar
import iso8601
import inputstreamhelper
import json

import collections

from datetime import datetime, timedelta

class Itemsy:
    def __init__(self, addon=None, addon_handle=None, base_url=None):

        self.addon = addon
        self.addon_handle = addon_handle
        self.base_url = base_url

        xbmcplugin.addSortMethod( self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_UNSORTED, label2Mask = "%R, %P, %Y")
        xbmcplugin.addSortMethod(self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_DATE, label2Mask = "%R, %P, %Y")
        xbmcplugin.addSortMethod(self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_TITLE, label2Mask = "%R, %P, %Y")
        xbmcplugin.addSortMethod(self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_LABEL, label2Mask = "%R, %P, %Y")
        xbmcplugin.addSortMethod(self.addon_handle, sortMethod=xbmcplugin.SORT_METHOD_LASTPLAYED, label2Mask = "%R, %P, %Y")
        
        
        
    def EOD (self):
        return xbmcplugin.endOfDirectory(self.addon_handle)
        
    def setContent(self, typ):
        return xbmcplugin.setContent(self.addon_handle, typ)
        
    def build_url(self, query):
        return self.base_url + '?' + urlencode(query)

    def add_item(self, url, name, image, mode, folder=False, IsPlayable=False, infoLabels=False, movie=True, fanart=False,itemcount=1, page=0,moviescount=0):
        list_item = xbmcgui.ListItem(label=name)
        fanart = fanart if fanart else ''

        if IsPlayable:
            list_item.setProperty("IsPlayable", 'True')
        if not infoLabels:
            infoLabels={'title': name,'plot':name}
        list_item.setInfo(type="video", infoLabels=infoLabels)    
        list_item.setArt({'thumb': image, 'poster': image, 'banner': image, 'icon': image, 'fanart': fanart})
        ok=xbmcplugin.addDirectoryItem(
            handle=self.addon_handle,
            url = self.build_url({'mode': mode, 'url' : url, 'page' : page, 'moviescount' : moviescount,'movie':movie,'title':name,'image':image}),            
            listitem=list_item,
            isFolder=folder)
        return ok
        
    def get_path(self ,data):    
        return self.addon.getAddonInfo(data)
        
    def get_setting(self, setting_id):
        setting = self.addon.getSetting(setting_id)
        if setting == 'true':
            return True
        elif setting == 'false':
            return False
        else:
            return setting
    
    def set_setting(self, key, value):
        return self.addon.setSetting(key, value)
        
    def open_settings(self):
        return self.addon.openSettings()

    def translate_path(self ,data):
        try:
            return xbmcvfs.translatePath(data)
        except:
            return xbmc.translatePath(data).decode('utf-8')
            
    def notification_dialog(self ,heading, text,typ, czas, sound):
        return xbmcgui.Dialog().notification(heading,text,typ,czas,sound)
        
    def yesno_dialog(self,heading, text, yeslabel, nolabel):
        return xbmcgui.Dialog().yesno(heading, text,yeslabel=yeslabel, nolabel=nolabel)
        
    def select_dialog(self,heading, label):
        return xbmcgui.Dialog().select(heading, label)
        
    def input_dialog(self, text, typ=None):
        typ = xbmcgui.INPUT_ALPHANUM if not typ else typ
        return xbmcgui.Dialog().input(text, type=typ)
        
        
    def PlayVid (self, mpdurl, lic_url='', PROTOCOL='', DRM=''):

        play_item = xbmcgui.ListItem(path=mpdurl)

        if PROTOCOL:

            is_helper = inputstreamhelper.Helper(PROTOCOL, drm=DRM)
            if is_helper.check_inputstream():
                if sys.version_info >= (3,0,0):
                    play_item.setProperty('inputstream', is_helper.inputstream_addon)
                else:
                    play_item.setProperty('inputstreamaddon', is_helper.inputstream_addon)
                if 'mpd' in PROTOCOL:
                    play_item.setMimeType('application/xml+dash')
                else:
                    play_item.setMimeType('application/vnd.apple.mpegurl')
                play_item.setProperty('inputstream.adaptive.manifest_type', PROTOCOL)
                if DRM and lic_url:
                    play_item.setProperty('inputstream.adaptive.license_type', DRM)
                    play_item.setProperty('inputstream.adaptive.manifest_update_parameter', 'full')
                    play_item.setProperty('inputstream.adaptive.license_key', lic_url)
                play_item.setProperty('inputstream.adaptive.license_flags', "persistent_storage")
                #playitem.setProperty('inputstream.adaptive.play_timeshift_buffer', 'true')
                play_item.setContentLookup(False)
        xbmcplugin.setResolvedUrl(self.addon_handle, True, listitem=play_item)
        
    def PLchar(self, char):
        if type(char) is not str:
            char=char.encode('utf-8')
        char = char.replace('\\u0105','\xc4\x85').replace('\\u0104','\xc4\x84')
        char = char.replace('\\u0107','\xc4\x87').replace('\\u0106','\xc4\x86')
        char = char.replace('\\u0119','\xc4\x99').replace('\\u0118','\xc4\x98')
        char = char.replace('\\u0142','\xc5\x82').replace('\\u0141','\xc5\x81')
        char = char.replace('\\u0144','\xc5\x84').replace('\\u0144','\xc5\x83')
        char = char.replace('\\u00f3','\xc3\xb3').replace('\\u00d3','\xc3\x93')
        char = char.replace('\\u015b','\xc5\x9b').replace('\\u015a','\xc5\x9a')
        char = char.replace('\\u017a','\xc5\xba').replace('\\u0179','\xc5\xb9')
        char = char.replace('\\u017c','\xc5\xbc').replace('\\u017b','\xc5\xbb')
        char = char.replace('&#8217;',"'").replace('&#215;',"x")
        char = char.replace('&#8211;',"-")    
        char = char.replace('&#8230;',"...")    
        char = char.replace('&#8222;','"').replace('&#8221;','"').replace('&#8220;','"')        
        char = char.replace('[&hellip;]',"...")
        char = char.replace('&#038;',"&")    
        char = char.replace('&#039;',"'")
        char = char.replace('&quot;','"').replace('&oacute;','ó').replace('&rsquo;',"'")
        char = char.replace('&nbsp;',".").replace('&amp;','&').replace('&eacute;','e')
        
        return char     
        
        
        
    def parse_datetime(self, iso8601_string, localize=False):
        """Parse ISO8601 string to datetime object."""
        datetime_obj = iso8601.parse_date(iso8601_string)
        if localize:
            return self.utc_to_local(datetime_obj)
        else:
            return datetime_obj
    
    
    def utc_to_local(self, utc_dt):
        # get integer timestamp to avoid precision lost
        timestamp = calendar.timegm(utc_dt.timetuple())
        local_dt = datetime.fromtimestamp(timestamp)
        assert utc_dt.resolution >= timedelta(microseconds=1)
        return local_dt.replace(microsecond=utc_dt.microsecond)
        
        
        
    def save_file(self, file, data, isJSON=False):
        with io.open(file, 'w', encoding="utf-8") as f:
            if isJSON == True:
                str_ = json.dumps(data,indent=4, sort_keys=True,separators=(',', ': '), ensure_ascii=False)
                f.write(to_unicode(str_))
            else:
                f.write(data)
    
        #str_ = json.dumps(jsondata,
        #    indent=4, sort_keys=True,
        #    separators=(',', ': '), ensure_ascii=False)
        #f.write(to_unicode(str_))


    
    def load_file(self, file, isJSON=False):

        if not os.path.isfile(file):
            return None
    
        with io.open(file, 'r', encoding='utf-8') as f:
            if isJSON == True:
                return json.load(f, object_pairs_hook=collections.OrderedDict)
            else:
                return f.read()                
                
