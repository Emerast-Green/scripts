from bs4 import BeautifulSoup as bs
import requests, tqdm
from selenium import webdriver
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.by import By
import os, sys
import io, json
options = webdriver.FirefoxOptions()
options.set_preference("media.volume_scale", "0.0");
os.environ['MOZ_HEADLESS'] = '1'
PATH = "./levidia/"
if not os.path.exists(PATH): os.mkdir(PATH)
def get_name(url,name=None):
    if name==None:
        name:str = bs(requests.get(url).content, 'html.parser').find('h1',class_='onstat').find('a').contents[0]
    if ": " in name:
        name=name.replace(":","")
    if ":" in name:
        name=name.replace(":"," ")
    if name.endswith("."):
        name=name.removesuffix(".")
    #print(name)
    return name

def get_show(url:str,overwrite=False,name=None):
    """
    url: link to the show
    overwrite: overwrite show file
    name: if show is already downloaded, pass name to use local data only
    Uses url to download data into a dict with name and int numered seasons with k-v:episode number-link.
    Data is saved for future use in a json format.
    """
    
    dt = {
        "name":None
    }
    if name==None:
        dt["name"]=get_name(url)
        #print(dt["name"])
        if not f"{dt['name']}.json" in os.listdir(f"{PATH}/"): overwrite = True
    else:
        overwrite=False
        dt["name"]=get_name(None,name)
    if overwrite:
        d = bs(requests.get(url).content, 'html.parser').find('ul',class_='mfeed')
        ltmp = [x.get('href') for x in d.find_all('a')]
        del d
        c = 0
        for x in ltmp:
            if x.startswith('tv-show.php'):
                c = int(x[x.find("&s=")+3:])
                dt[c]=[]
            else:
                dt[c].append(x)
        with open(f"{PATH}/{dt['name']}.json","w") as fs:
            json.dump(dt,fs)
        os.mkdir(dt["name"])
    else:
        with open(f"{PATH}/{dt['name']}.json","r") as fs:
            t: dict = json.load(fs)
            dt: dict = {"name":t["name"]}
            for k,v in t.items():
                if k!="name":
                    dt[int(k)]=v
    dt: dict
    return dt
def get_wootly_link(url:str,start='https://www.levidia.ch/'):
    """
    url: episode's part of site's url, stored in show dict as season's list's values
    start: domain
    Obtains link to the episode on wootly (not file) and it's name
    """
    d = bs(requests.get(start+url).content, 'html.parser').find('ul',class_='mfeed')
    for i,x in enumerate(d.find_all('li',class_='xxx0')):
        if x.find('span','kiri xxx1 xx12').find('b').contents[0]=='Wootly':
            l:str = x.find('span','mainlink kanan').find('a').get('href')
            name:str = get_name(None,x.find('h2','mainlink kiri xxx4').find('b').contents[0])
    return l,name
def download_as_bytes_with_progress(url: str,name: str,show_name: str):
    """
    Download and save a episode under name.
    url: direct link to the file
    name: episode's name for filename
    show_name: show's name for directory
    """
    start = 0
    name=get_name(None,name)
    show_name=get_name(None,show_name)
    if f"{name}.mp4.incomplete" in os.listdir(f"{PATH}/{show_name}/"):
        with open(f"{PATH}/{show_name}/{name}.mp4.incomplete",'rb') as fs:
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
    """
    Either gets show's data from url or show dict.
    url: show's url
    nr: number of the season
    show: show's dict (optional)
    """
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
            if f"{name}.mp4" in os.listdir(f"{PATH}/{show['name']}/"):
                bar.update(1)
            else:
                finished=False
                while not finished:
                    finished=download_episode(ep,show['name'],name)
                    if finished: bar.update(1)
def get_download_link(ep):
    """
    Get's direct link to the episode's file by episode's url.
    ep: episode's url
    Can raise error if proper url is not obtained in 5 attempts
    """
    driver = webdriver.Firefox(options=options)
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
    tries=0
    while not src.startswith("https://go.wootly.ch/"):
        src = driver.find_element(By.TAG_NAME, "video").get_attribute('src')
        tries+=1
        if tries>5:
            raise ConnectionError("Cannot obtain valid link, domain is repeatedly invalid.")
    driver.quit()
    return src
def download_episode(ep,show_name,name=None):
    """
    Download an episode
    ep: episode url
    show_name: show's name
    name: episode's name, by default obtained automaticaly
    """
    if name==None:
        _,name = get_wootly_link(ep)
    _data,_finished=download_as_bytes_with_progress(get_download_link(ep),name,show_name)
    with open(f"{PATH}/{show_name}/{name}.mp4.incomplete",'ab') as fs:
        fs.write(_data)
    if _finished:
        os.rename(f"{show_name}/{name}.mp4.incomplete",f"{show_name}/{name}.mp4")
    return _finished
def download_seasons(url,*nrs,show=None):
    """
    Download multpile seasons in a row.
    url: show's url
    nrs: any number of season numerals
    It has no overwrite, too many numbers will break it and repeats could do something.
    """
    if show==None: show = get_show(url)
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
def search_result(text,page=1,domain="https://www.levidia.ch/"):
    """
    text: query to send
    page: number of result's page
    domain: site's domain
    Get results, if any choosen, download episode's data.
    """
    url = f"{domain}/search.php?q={text}&v=episodes&page={page}"
    d = bs(requests.get(url).content, 'html.parser').find('ul',class_='mfeed')
    ltmp = {}
    for x in d.find_all('li',class_='mlist'):
        ltmp[x.find('div','mainlink').find('strong').contents[0]]=x.find('a',class_='kiri mkan3').get('href')
    for i,k in enumerate(ltmp.keys()):
        print(i+1,k)
    print("Choose by number 1-20 or q to quit.")
    r = input(":")
    if r=="q":
        return None
    else:
        name = list(ltmp.keys())[int(r)-1]
        get_show(domain+ltmp[name])
        print(f"Pass --show '{name}' in further commands to reference your choice.")
url = None
show = None
#print(sys.argv)
if "--search" in sys.argv:
    text = sys.argv[sys.argv.index("--search")+1]
    search_result(text)
else:
    if "--url" in sys.argv:
        url = sys.argv[sys.argv.index("--url")+1]
    if "--show" in sys.argv:
        show=get_show("",False,get_name(None,sys.argv[sys.argv.index("--show")+1]))
    if "--seasons" in sys.argv:
        seasons = [int(x) for x in sys.argv[sys.argv.index("--seasons")+1].split(',')]
        download_seasons(url,*seasons,show=show) 
    if "--episode" in sys.argv:
        season = int(sys.argv[sys.argv.index("--episode")+1])
        episode = int(sys.argv[sys.argv.index("--episode")+2])-1
        if show==None: show = get_show(url)
        download_episode(show[season][episode],show['name'])