from urllib.parse import urlparse
from json import dumps, loads
from threading import Thread
from os import mkdir, path
from requests import get
from time import sleep
from re import search
import config

headers = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.108 Safari/537.36'
}

def getImage(post_id, profile_username):
    global headers
    with open('data/' + profile_username + '/list.txt') as f:
        if post_id in f.read().splitlines():
            print('Skipping ' + post_id)
        else:
            print('Downloading ' + post_id)
            with open('data/' + profile_username + '/list.txt', 'a') as l:
                l.write(post_id + '\n')
            response = get('https://api.vir.vn/instagram/p/' + post_id).json()
            for photo in response['data']:
                r = get(photo['src'], headers=headers)
                if r.status_code == 200:
                    with open('data/' + profile_username + '/' + urlparse(photo['src']).path.split('/')[-1], 'wb') as p:
                        p.write(r.content)

def next(profile_id, end_cursor, profile_username, threads):
    global headers
    payload = {'query_hash': '2c5d4d8b70cad329c4a6ebe3abb6eedd', 'variables': dumps({'id': profile_id, 'first': 12, 'after': end_cursor}) }
    endpoint = 'https://www.instagram.com/graphql/query/'
    res = get(endpoint, params=payload, headers=headers).json()
    for item in res['data']['user']['edge_owner_to_timeline_media']['edges']:
        if config.MULTITHREADING:
            t = Thread(target=getImage, args=(item['node']['shortcode'], profile_username))
            threads.append(t)
        else:
            getImage(item['node']['shortcode'], profile_username)
    if res['data']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page'] == True:
        next(profile_id, res['data']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor'], profile_username, threads)

def main_crawl(is_watch_mode=True):
    global headers
    threads = []

    for profile in config.PROFILE_LIST:
        response = get('https://www.instagram.com/' + profile, headers=headers).text
        _sharedData = loads(search('window\._sharedData = (.+);</script>', response)[1])

        if 'ProfilePage' in _sharedData['entry_data']:
            profile_id = _sharedData['entry_data']['ProfilePage'][0]['graphql']['user']['id']
            profile_username = _sharedData['entry_data']['ProfilePage'][0]['graphql']['user']['username']

            if path.isdir('data/' + profile_username) == False:
                mkdir('data/' + profile_username)
                open('data/' + profile_username + '/list.txt', 'a').close()

            for item in _sharedData['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['edges']:
                if config.MULTITHREADING and is_watch_mode == False:
                    t = Thread(target=getImage, args=(item['node']['shortcode'], profile_username))
                    threads.append(t)
                else:
                    getImage(item['node']['shortcode'], profile_username)

            if _sharedData['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['page_info']['has_next_page'] == True and is_watch_mode == False:
                next(profile_id, _sharedData['entry_data']['ProfilePage'][0]['graphql']['user']['edge_owner_to_timeline_media']['page_info']['end_cursor'], profile_username, threads)

    if len(threads) > 0:
        for x in threads:
            x.start()
        for x in threads:
            x.join()

if __name__ == '__main__':
    if path.isdir('data') == False:
        mkdir('data')

    main_crawl(is_watch_mode=False)
    print('Download completed!')

    if config.WATCH:
        print('Start watching')
        sleep(config.WATCH_INTERVAL)
        main_crawl()