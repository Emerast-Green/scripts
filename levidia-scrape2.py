from bs4 import BeautifulSoup as bs
import requests
import wget
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import os
import time
import tqdm
import io
def get_show(url):
    d = bs(requests.get(url).content, 'html.parser').find('ul',class_='mfeed')
    ltmp = [x.get('href') for x in d.find_all('a')]
    d = {}
    c = 0
    for x in ltmp:
        if x.startswith('tv-show.php'):
            c = int(x[x.find("&s=")+3:])
            d[c]=[]
        else:
            d[c].append(x)
    d['name']=bs(requests.get(url).content, 'html.parser').find('h1',class_='onstat').find('a').contents[0]
    return d
def get_wootly_link(url,start='https://www.levidia.ch/'):
    d = bs(requests.get(start+url).content, 'html.parser').find('ul',class_='mfeed')
    for i,x in enumerate(d.find_all('li',class_='xxx0')):
        if x.find('span','kiri xxx1 xx12').find('b').contents[0]=='Wootly':
            l = x.find('span','mainlink kanan').find('a').get('href')
            name = x.find('h2','mainlink kiri xxx4').find('b').contents[0]
    return l,name
def download_as_bytes_with_progress(url: str,name: str,show_name: str):
    start = 0
    if f"{name}.mp4.incomplete" in os.listdir(f"{show_name}/"):
        with open(f"{show_name}/{name}.mp4.incomplete",'rb') as fs:
            start = len(fs.read())
    resp = requests.get(url, headers={"Range": f"bytes={start}-"}, stream=True)
    total = int(resp.headers.get('content-length', 0))
    bio = io.BytesIO()
    with tqdm.tqdm(
        desc=name,
        total=total,
        unit='b',
        unit_scale=True,
        unit_divisor=1024,
        leave=False
    ) as bar:
        for chunk in resp.iter_content(chunk_size=65536):
            bar.update(len(chunk))
            bio.write(chunk)
    return bio.getvalue(),total==len(bio.getvalue())
def download_season(url,nr,show=None):
    if show==None: show = get_show(url)
    try:
        os.mkdir(show['name'])
    except:
        pass
    with tqdm.tqdm(
        desc=f"{show['name']} Season {nr}",
        total=len(show[nr]),
        unit='ep',
        leave=False
    ) as bar:
        for ep in show[nr]:
            _,name = get_wootly_link(ep)
            if f"{name}.mp4" in os.listdir(f"{show['name']}/"):
                bar.update(1)
            else:
                finished=False
                while not finished:
                    finished=download_episode(ep,show['name'],name)
                    if finished: bar.update(1)

def download_episode(ep,show_name,name=None):
    if name==None:
        _,name = get_wootly_link(ep)
    driver = webdriver.Firefox()
    driver.get('https://www.levidia.ch/'+ep)
    driver.implicitly_wait(5)
    driver.set_script_timeout(5)
    main = driver.window_handles[0]
    driver.find_element(By.LINK_TEXT, 'Play in Flash').click()
    l = driver.window_handles
    l.remove(main)
    driver.switch_to.window(l[0])
    #time.sleep(5)
    driver.switch_to.frame(driver.find_element(By.TAG_NAME,'iframe'))
    driver.find_element(By.CLASS_NAME, "play-button").click()
    #time.sleep(5)
    src = driver.find_element(By.TAG_NAME, "video").get_attribute('src')
    driver.quit()
    filename = wget.download(src,f"{show_name}/{name}.mp4")
    return True

def download_seasons(url,*nrs):
    show = get_show(url)
    try:
        os.mkdir(show['name'])
    except:
        pass
    with tqdm.tqdm(
        desc=f"{show['name']}",
        total=len(nrs),
        unit='sn',
        leave=False
    ) as bar:
        for nr in nrs:
            download_season(url,nr,show)
            bar.update(1)
url = "https://www.levidia.ch/tv-show.php?watch=house-md"
#url = "https://www.levidia.ch/tv-show.php?watch=heartstopper"
download_seasons(url,3) 
