ARCHIVE_NAME =   'Dogeparty Image Archive'
DB_FILE =        'dogeparty.db'
ARCHIVE_FOLDER = 'xdp_{max block}'
IMG_FILES =      ['jpg', 'jpeg', 'gif', 'png']
TEST_SAMPLE =    0     #set to 0 to download everything. 30 recommended for testing
SAVE_ORIGINAL =  True  #a smaller image copy is also made regardless
MAX_MB =         30    #abort download if image is larger
DOWNLOAD_WAIT =  1.0   #wait sec between every download
CHECK_JSON =     True  #try to extract image urls from json
DOWNSIZE_W =     500   #downsized image keeps original ratio
DOWNSIZE_H =     500   #  new size equals this width OR height, and less in other dimension
FORCE_JPEG =     True  #convert png and gif to jpeg? reduces size but occasionally fails 
DONT_SHOW =      ['A1477467785675714600', #No thumbnail made and not shown in archive. Only original image is saved
                 'A203444615565884220']  


import re
import requests
import hashlib
import shutil
import csv
import math
import codecs
import json
import os
import sqlite3
import time
import random

from PIL import Image #pip install pillow
from datetime import datetime

dir_path = os.path.dirname(os.path.realpath(__file__))
os.chdir(dir_path)


def get_url(text):
    urls = re.findall('(?:(?:https?|ftp):\/\/)?[\w/\-?=%.]+\.[\w/\-&?=%.]+', text)
    if urls:
        url = urls[0]
    else:
        return ''
    if url.startswith('imgur/'): #xchain format
        url = url.replace('imgur/', 'https://i.imgur.com/')
    if '://' not in url: #no scheme -> assume https://
        url = 'https://' + url  
    return url
    
    
def image_url(url): #Return True if ends with image file extension
    if isinstance(url, str) == False:
        return False
    filetype = url.rsplit('.',1)[-1].lower()
    if filetype in IMG_FILES:
        return True
    return False


def download(url: str, dest_folder: str, filename: str):
    time.sleep(DOWNLOAD_WAIT)
    if not os.path.exists(dest_folder):
        os.makedirs(dest_folder)  # create folder if it does not exist
    file_path = os.path.join(dest_folder, filename)
    try:
        r = requests.get(url, stream=True, timeout=(5, 15))
        if r.ok:
            i = 0
            with open(file_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=500000):
                    if chunk:
                        f.write(chunk)
                        f.flush()
                        os.fsync(f.fileno())
                    i += 1
                    if i >= MAX_MB * 2:
                        f.close()
                        os.remove(file_path)
                        return 'Error: File too large'
        else:
             # HTTP status code 4XX/5XX
            return 'Error: Download failed'
        return 'OK'
    except:
        return 'Error: Download failed'

    
def file_sha256(folder: str, filename: str):
    file_path = os.path.join(folder, filename)
    sha256_hash = hashlib.sha256()
    with open(file_path,"rb") as f:
        # Read and update hash string value in blocks of 4K
        for byte_block in iter(lambda: f.read(4096),b""):
            sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()


#Block timestamps  
ts = [None] * 8000000
con = sqlite3.connect(DB_FILE)
cur = con.cursor()
print('Opening DB')
for row in cur.execute('SELECT block_index, block_time FROM blocks;'):
    ts[row[0]] = row[1]
    max_index = row[0]
    max_ts = row[1]
print('Max block index:', str(max_index))
max_date = str(datetime.fromtimestamp(max_ts)) 
print('Max block time: ', max_date)


combos = []
x = []
for row in \
    cur.execute('SELECT tx_index, msg_index, block_index, asset, quantity, divisible, source, issuer, transfer, description, locked, asset_longname  FROM issuances WHERE status = "valid";'):
    tx_index = row[0]
    msg_index = row[1]
    block_ts = ts[row[2]]
    asset = row[3]
    quantity = str(row[4])
    divisible = row[5]
    source = row[6]
    issuer = row[7]
    transfer = row[8]
    description = row[9]
    locked = row[10]
    asset_longname = row[11]

    # so both regular and sub-assets go under real name
    asset_realname = asset_longname
    if asset_realname == None:
        asset_realname = asset

    # asset family = parent of subasset, else same as asset
    asset_family = asset_realname.split('.')[0]
    url = get_url(description)
    filetype = url.rsplit('.', 1)[-1].lower()
    if url != '':
        combo = asset + ' ' + url
        if combo not in combos:  # ignore subsequent issuances with same asset/url
            combos.append(combo)
            if image_url(url) or CHECK_JSON and filetype == 'json':
                x.append({
                    'asset_real': asset_realname,
                    'asset_family': asset_family,
                    'tx_index': tx_index,
                    'msg_index': msg_index,
                    'block_ts': block_ts,
                    'block_date': str(datetime.fromtimestamp(block_ts)),
                    'asset': asset,
                    'asset_longname': asset_longname,
                    'description': description,
                    'url': url,
                    'url_status': '',
                    'url_ok': True,
                    'filetype': filetype,
                    'filename': '',
                    'filename_path': '',
                    'filepath': '',
                    'file_sha256': '',
                    'file_sha256_b64': '',
                    'filesmall_sha256': '',
                    'filesmall_sha256_b64': '',
                    'filesmall_name': '',
                    'filesmall_path': '',
                    })

con.close()


#Create folder to save archive
ARCHIVE_FOLDER = ARCHIVE_FOLDER.replace('{max block}', str(max_index))
if not os.path.exists(ARCHIVE_FOLDER):
    os.makedirs(ARCHIVE_FOLDER)
os.chdir(ARCHIVE_FOLDER)


#Download in random order
#  reduces repeat requests to same domain 
random.shuffle(x)


#Test with a few assets
if TEST_SAMPLE > 0:
    del x[TEST_SAMPLE:]
    print(x)


#If json, try to load json and update image url
#   If json fails to open, leave error status
#   If json loads but no image url found, also leave error status
print('')
print('Get image URLs from JSON links')
for i in range(len(x)):
    url = x[i]['url']
    if url.lower().endswith('.json'):
        url_json = url
        try:
            time.sleep(DOWNLOAD_WAIT)
            url = requests.get(url, timeout=1.5)
            text = url.text
            data = json.loads(text)
            success = 1
        except:
            success = 0
        if success == 0:
            x[i]['url_status'] = 'Error: Cannot open json'
            x[i]['url_ok'] = False
        else: #try to get image url from json
            try:
                if 'image_large' in data: #Xchain's recommended format
                    url = data['image_large']
                elif 'image' in data:
                    url = data['image']
                else:
                    url = get_url(text)
                if image_url(url):
                    x[i]['url'] = url
                    x[i]['filetype'] = url.rsplit('.',1)[-1].lower()
                else:
                    x[i]['url_status'] = 'Error: No image url in json'
                    x[i]['url_ok'] = False
            except:
                x[i]['url_status'] = 'Error: Json format'
                x[i]['url_ok'] = False
        if x[i]['url_ok']:
            print('OK    ' + url_json + ' ---> ' + x[i]['url'])
        else:
            print('Error ' + url_json + ' ---> ' + x[i]['url_status'])


#Download images
issuances = 0
download_attempts = 0
download_fails = 0
downsize_fails = 0
pct = 0
print('')
print('Downloading images')
for i in range(len(x)):
    issuances += 1
    pct_prev = pct
    pct = round(100 * issuances / len(x))
    if pct > pct_prev:
        print(str(pct) + '% downloaded')
    # Save to temp folder
    if x[i]['url_ok'] == True:
        download_attempts += 1
        filename = 'original.' + x[i]['filetype']
        x[i]['url_status'] = download(x[i]['url'], 'temp', filename)
        if x[i]['url_status'].startswith('Error:'):
            download_fails += 1
            print('   '+x[i]['asset_real'] + '  ' + x[i]['url_status'])
            continue
        
        #Get sha256
        x[i]['file_sha256'] = file_sha256('temp', filename)
        x[i]['file_sha256_b64'] = codecs.encode(codecs.decode(x[i]['file_sha256'], 'hex'), 'base64').decode()     
        
        #Make downsized copy
        if not (x[i]['asset'] in DONT_SHOW or x[i]['asset_longname'] in DONT_SHOW): 
            filesmall = 'small.' + x[i]['filetype']
            try:
                img = Image.open('temp/'+filename)
                img.thumbnail((DOWNSIZE_W, DOWNSIZE_H))
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                img.save('temp/'+filesmall)
                #Get sha256
                x[i]['filesmall_sha256'] = file_sha256('temp', filesmall)
                x[i]['filesmall_sha256_b64'] = codecs.encode(codecs.decode(x[i]['filesmall_sha256'], 'hex'), 'base64').decode()
                #Rename and move
                sha = x[i]['filesmall_sha256']
                filenew = x[i]['asset_family'] + '_' + sha[0:16]
                if FORCE_JPEG:
                    filenew += '.jpg'
                else:
                    filenew += '.' + x[i]['filetype']
                filenew = filenew.lower()
                path = 'small/' + sha[0] + '/' + sha[0:2]
                if not os.path.exists(path):
                    os.makedirs(path)
                shutil.move('temp/'+filesmall, path+'/'+filenew)
                x[i]['filesmall_path'] = path
                x[i]['filesmall_name'] = filenew
            except:
                downsize_fails += 1
                print('   Unable to downsize ' + x[i]['asset_real'] + '  ' + x[i]['url'])
        
        #Rename and move original
        #  (or delete if SAVE_ORIGINAL == False)
        if SAVE_ORIGINAL:
            #Rename and move
            sha = x[i]['file_sha256']
            filenew = x[i]['asset_family'] + '_' + sha[0:16]
            filenew += '.' + x[i]['filetype']
            filenew = filenew.lower()
            path = 'original/' + sha[0] + '/' + sha[0:2]
            if not os.path.exists(path):
                os.makedirs(path)
            shutil.move('temp/'+filename, path+'/'+filenew)
            x[i]['filepath'] = path
            x[i]['filename'] = filenew
        
shutil.rmtree('temp')


#Stats
download_successes = download_attempts - download_fails
dowsize_successes = download_successes - downsize_fails
n_issuances = f'{issuances:,}'
n_download_attempts = f'{download_attempts:,}'
n_download_successes = f'{download_successes:,}'
n_dowsize_successes = f'{dowsize_successes:,}'
stat_max_len = len(n_issuances)


#Write receipt
print('')
print('Writing receipt')
x = sorted(x, key=lambda k: (k['tx_index'], k['msg_index'])) 
rec = []
rec.append(['tx_index','asset', 'asset_longname', 'url', 'status', 'original_sha256', 'downsized_sha256'])
for i in range(len(x)):
    if x[i]['url_ok']:
        rec.append([
            x[i]['tx_index'],
            x[i]['asset'],
            x[i]['asset_longname'],
            x[i]['url'],
            x[i]['url_status'],
            x[i]['file_sha256'],
            x[i]['filesmall_sha256']
            ])
filetemp = 'temp-csv.csv'
file = open(filetemp, 'w+', newline ='')
# writing the data into the file
with file:   
    write = csv.writer(file, quotechar='"', quoting=csv.QUOTE_ALL)
    write.writerows(rec)
sha_receipt = file_sha256('', filetemp)
file_receipt = 'archive_'+sha_receipt[0:32]+'.csv'
shutil.move(filetemp, file_receipt)
print('Receipt filename:       ', file_receipt)
print('Receipt sha256 checksum:', sha_receipt)
print('Checksum truncated:     ', sha_receipt[0:32])


#HTML directory
#   A very basic website with all assets/images
#   Albahebtical tree structure for SEO
print('')
print('Generating html directory')
x = sorted(x, key=lambda k: (k['asset_real'], k['tx_index'], k['msg_index']))

#common header and footer for all html files
header = """<!DOCTYPE html><html><head><title>{title}</title>
  <style>
    .content {
      font-family: "Consolas", "Lucida Console", "Courier New", monospace;
      max-width: 600px;
      margin: auto;
      white-space:pre;
    }
    td {
      padding-top:8px;
    }
    td:first-child {
      vertical-align: top; 
      text-align:center;
    }
    td:last-child {
      vertical-align: top; 
      text-align:left;
    }
    img {
      width: 280px;
    }
    span {
      font-size: small;
    }
  </style>
  </head><body><div class="content">"""
footer = '\n</div></body></html>';

#index.html in main directory; archive in sub-directory
path = 'html'
if not os.path.exists(path):
    os.makedirs(path)
    
#Each asset gets an html block
#   Code is complicated bcs one asset can have several images
assets = []
asset_block = [] 
html = ''
for i in range(len(x)):
    #Ignore if repeat url
    repeat = False
    if i>0 and x[i]['url'] == x[i-1]['url'] and x[i]['asset'] == x[i-1]['asset']:
        repeat = True
    if x[i]['url_ok'] and repeat == False:
        if x[i]['filesmall_name'] != '':
            html += '\n<tr><td><img src="../' + x[i]['filesmall_path'] + '/' + x[i]['filesmall_name'] + '"></td>'
        else:
            html += '<tr><td>&nbsp;</td>'
        html += '<td>'
        html += '<b>' + x[i]['asset_real'] + '</b><br>'
        if x[i]['asset_longname'] != None:
            html += 'Numeric: ' + x[i]['asset'] + '<br>'
        html += 'Date:    ' + x[i]['block_date'].split(' ')[0] + '<br>'
        html += 'URL:     <a href="' + x[i]['url'] + '">' + x[i]['url'] + '</a><br>'
        if x[i]['url_status'] == 'OK':
            html += 'Original sha256:<br> <span>' + x[i]['file_sha256'] + '</span><br>'
            html += 'Downsized sha256:<br> <span>' + x[i]['filesmall_sha256'] + '</span><br>'
        else:
            html += 'Status:  ' + x[i]['url_status'] + '<br>'
        html += '</td></tr>'
    if i == 0 or x[i]['asset_real'] != x[i-1]['asset_real'] or i == len(x) - 1:
        if html != '':
            assets.append(x[i]['asset_real']) 
            asset_block.append(html)
        html = ''

#Group N assets per html file
group_size = round(math.sqrt(len(asset_block)))
num_pages = math.ceil(math.sqrt(len(asset_block)))
start = 0
count = 0
archive_links = []
while start < len(asset_block):
    count += 1
    filename = str(count).zfill(4) + '.html'
    filename_prev = str(count-1).zfill(4) + '.html'
    filename_next = str(count+1).zfill(4) + '.html'
    end = min(start + group_size - 1, len(asset_block) - 1)
    asset_start = assets[start]
    asset_end = assets[end]
    archive_links.append('<a href="' + path + '/' + filename + '">' + asset_start[0:8].ljust(8) + ' &mdash; ' + asset_end[0:16] + '</a>')
    html = header
    nav = '<p>Page ' + str(count) + '/' + str(num_pages)
    nav += '  |  <a href="../index.html">Home</a>'
    if count > 1:
        nav += '  |  <a href="' + filename_prev + '">Previous</a>'
    if count < num_pages:
        nav += '  |  <a href="' + filename_next + '">Next</a>'
    nav += '</p>'
    html += '<h1>' + ARCHIVE_NAME +'</h1>'
    html += nav
    html += '<table>' 
    for i in range(start, end + 1): # +1 bcs range is not inclusive
        html += asset_block[i]
    html += '\n</table>'
    html += nav
    html +=  '<p>Blockchain date:   ' + str(max_date).split(' ')[0] + ', height ' + f'{max_index:,}'
    html += '<br>Images downloaded: ' + str(datetime.now()).split(' ')[0] + '</p>'
    html += footer
    html = html.replace('{title}', ARCHIVE_NAME + ' – Page ' + str(count) + '/' + str(num_pages))
    file = open(path + '/' + filename, 'w')
    file.write(html)
    file.close()
    start += group_size

#Main page
html = header
html += '<h1>' + ARCHIVE_NAME +'</h1>'
html += '<p>Created ' + str(datetime.now()).split(' ')[0] + '.</p>'
html += '<p>View alphabetic list:<br>'
for i in range(len(archive_links)):
    html += archive_links[i] + '<br>'
html += '<br>Asset issuances:   ' + n_issuances.rjust(stat_max_len)
html += '<br>Image URLs found:  ' + n_download_attempts.rjust(stat_max_len)
html += '<br>Downloaded images: ' + n_download_successes.rjust(stat_max_len)
html += '<br>Downsized images:  ' + n_dowsize_successes.rjust(stat_max_len)
html += '</p><p>The <a href="' + file_receipt + '">reciept</a> csv file contains checksums of all images.</p>'
html += '<p>Check out <a href="https://github.com/Jpja/XDP-Image-Archive">Github</a> for further details.</p>'
html += '<p>MIT licence. Images may be subject to copyright.</p>'
html += footer
html = html.replace('{title}', ARCHIVE_NAME)
file = open('index.html', 'w')
file.write(html)
file.close()


#Congraulations!
print('')
print('CONGRATULATIONS!')
print('Archive created successfully.')
print('Asset issuances:   ' + n_issuances.rjust(stat_max_len))
print('Image URLs found:  ' + n_download_attempts.rjust(stat_max_len))
print('Downloaded images: ' + n_download_successes.rjust(stat_max_len))
print('Downsized images:  ' + n_dowsize_successes.rjust(stat_max_len))
print('')
print('To timestamp the archive, broadcast a text of the following format:')
print('  bit.ly/xxxxxxx ' + sha_receipt[0:32])
print('where "bit.ly/xxxxxxx" points to the archive.')
print('and "' + sha_receipt[0:32] + '" is a truncated sha256 hash of the receipt file.')
print('')
input("*** PRESS ENTER TO QUIT ***")