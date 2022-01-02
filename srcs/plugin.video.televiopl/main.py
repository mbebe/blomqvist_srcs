# -*- coding: UTF-8 -*-

import sys, os

if sys.version_info >= (3,0,0):
# for Python 3
    from urllib.parse import parse_qsl
else:
    # for Python 2
    from urlparse import parse_qsl

import xbmcaddon

base_url = sys.argv[0]
addon_handle = int(sys.argv[1])

from resources.lib.itemsy import Itemsy
from resources.lib.televio import Televio

Items = Itemsy(
    addon=xbmcaddon.Addon('plugin.video.televiopl'),
    addon_handle=addon_handle,
    base_url=base_url
)


params = dict(parse_qsl(sys.argv[2][1:]))
exlink = params.get('url', None)
page = params.get('page',[1])
title = params.get('title', None)
icona  = params.get('image', None)

PATH        =    Items.get_path('path')
PROFILE        =    Items.get_path('profile')

DATAPATH    =    Items.translate_path(PROFILE)

if not os.path.exists(DATAPATH):
    os.makedirs(DATAPATH)
    
RESOURCES       = PATH+'/resources/'

FANART=RESOURCES+'../fanart.jpg'
ikona = RESOURCES+'../icon.png'

Televio = Televio(Items, FANART, ikona)

def router(paramstring):
    args = dict(parse_qsl(paramstring))
    
    if args:
        mode = args.get('mode', None)

        if mode  == 'loguj':
            Items.open_settings()
            xbmc.executebuiltin('Container.Refresh()')
            
        elif mode  == 'listtv':
            Televio.listTV()

        elif mode == 'playtv':
            Televio.PlayTV(exlink)

        elif mode == 'listkeczup':
            Televio.listKeczup(exlink, title, icona)
            
        elif mode == 'listekczup2':
            Televio.listKeczup2(exlink, icona)

        elif mode == 'playvid':
            Televio.PlayVid(exlink)

        elif mode == 'listradio':
            Televio.ListRadio()
            

    else:
        Televio.home()    
if __name__ == '__main__':
    router(sys.argv[2][1:])
