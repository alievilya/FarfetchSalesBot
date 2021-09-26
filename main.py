# !pip install beautifulsoup4
import os
import re
import urllib.request
import json
import arrow
import telebot
import tqdm
from bs4 import BeautifulSoup

import yaml

def load_cfg(path="config.yml"):
    with open(path, "r") as ymlfile:
        cfg = yaml.load(ymlfile)
    for section in cfg:
        print(section, ' is read in config')
    return cfg

def getdata_brand(url, save_path, previous_links):
    data = dict()
    item_class = "css-1sdwiau-ProductCard e19e7out0"
    p_class_price = "css-8ay7mq-Body-Price e15nyh750"
    p_old_price = "css-16ej13o-Footnote-PriceOriginal e9urw9y0"
    p_new_price = "css-1ve5oeq-Body-PriceFinal esd507w0"
    brand_p_class_name = "css-1swgdp2-Body-BodyBold-ProductCardBrandName e1s7cbpu0"
    item_p_class_name = "css-m4scyi-Body-ProductCardDescription enl7ai30"
    item_link = "css-1kfbwnd-BlockAction-ProductCardLink e4l1wga0"
    item_header_link = "css-a3xtya-ProductCardHeader e1cwh4yu0"
    img_class = "e953t7u0 css-1g1ti7a-BaseImg-ProductCardImagePrimary e2u0eu40"
    if os.path.isfile(save_path):
        os.remove(save_path)

    for page_n in tqdm.tqdm(range(400)):
        cur_url = url.format(page_n)
        try:
            page_files = urllib.request.urlopen(cur_url)
        except:
            print('page_not_found')
            continue
        file_data = ""
        for line in page_files:
            decoded_line = line.decode("utf-8")
            file_data += decoded_line
        soup = BeautifulSoup(file_data, 'html.parser')
        # n_pages_str = soup.find_all('div', class_=n_pages_link)
        for div_item in soup.find_all('div', class_=item_class):
            try:
                href_a = div_item.find('a', class_=item_link)
                link = href_a.get('href')
                try:
                    old_price_str = div_item.find('p', class_=p_class_price).getText()
                    new_price_str = old_price_str
                except:
                    try:
                        old_price_str = div_item.find('p', class_=p_old_price).getText()
                        new_price_str = div_item.find('p', class_=p_new_price).getText()
                    except:
                        old_price_str = ''
                        new_price_str = ''
                brand_name = div_item.find('p', class_=brand_p_class_name).getText()
                item_name = div_item.find('p', class_=item_p_class_name).getText()

                old_price = int(''.join(re.findall(r'\d+', old_price_str)))
                new_price = int(''.join(re.findall(r'\d+', new_price_str)))
                sale = round((1 - new_price / old_price) * 100)

                link_cont = div_item.find('div', class_=item_header_link)
                image_link = link_cont.find('link')
                if not image_link:
                    try:
                        image_link = div_item.find('img', class_=img_class).get('src')
                    except:
                        image_link = ''
                else:
                    image_link = image_link.get('href')
                if not data.get(link):
                    data[link] = dict()
                if link == data[link].get('link'):
                    continue
                data[link]['old_price'] = old_price
                data[link]['new_price'] = new_price
                data[link]['sale'] = sale
                data[link]['link'] = link
                data[link]['brand'] = brand_name
                data[link]['item_name'] = item_name
                data[link]['image_link'] = image_link

                if sale >= 70 and link not in previous_links:
                    send_new_posts(data[link])

            except:
                print('some exception')
                continue
    return data


def check_create_dir(directory):
    if not os.path.isdir(directory):
        os.mkdir(directory)


def write_today_brands(brands_arr, previous_links):
    for brand in brands_arr:
        brand_name = brand.split('/')[6]
        now_day = str(arrow.now().day)
        check_create_dir(now_day)
        save_path = '{}/{}.json'.format(now_day, brand_name)
        data_brand = getdata_brand(brand, save_path, previous_links=previous_links)

        with open(save_path, 'w', encoding='utf-8-sig') as fp:
            json.dump(data_brand, fp, ensure_ascii=False, indent=4)


def load_day(brands_arr, counter):
    brands_data = {}
    for brand in brands_arr:
        brand_name = brand.split('/')[6]

        load_path = '{}/{}.json'.format(counter, brand_name)
        with open(load_path, 'r', encoding='utf-8-sig') as reader:
            brands_data[brand_name] = json.load(reader)
    return brands_data



sent_videos = set()

cfg = load_cfg(path='config.yml')
token = cfg['token']
channel = cfg['channel']
bot = telebot.TeleBot(token)

def send_new_posts(diction):
    link = "farfetch.com" + diction['link']
    text_caption = "{} {} \n{} -> {}\n{}".format(diction['brand'], diction['item_name'],
                                                 diction['old_price'], diction['new_price'], link
                                                 )
    img_link = diction['image_link']
    if img_link is None:
        bot.send_message(chat_id=channel, text="{}".format(text_caption))
    else:
        f = open('out.jpg', 'wb')
        f.write(urllib.request.urlopen(img_link).read())
        f.close()
        img = open('out.jpg', 'rb')
        bot.send_photo(chat_id=channel, photo=img, caption=text_caption, timeout=10)
    return


if __name__ == "__main__":
    sales_page = "https://www.farfetch.com/ru/shopping/men/sale/all/items.aspx?page={}&rootCategory=Men"
    stone = "https://www.farfetch.com/ru/shopping/men/stone-island/items.aspx?page={}&rootCategory=Men"
    sale_value = 80
    brands_arr = [sales_page]
    for i in range(10):

        brands_yesterday = load_day(brands_arr, counter=0)

        write_today_brands(brands_arr, previous_links=brands_yesterday)
        brands_today = load_day(brands_arr, counter=i + 1)
        new_arr = {}
        for brand in ['sale']:
            b_t = set(brands_today[brand].keys())
            b_y = set(brands_yesterday[brand].keys())
            new = b_t - b_y
            new_arr[brand] = new

        link = new_arr['sale']

        text_array = []
        for l in link:
            y = brands_today['sale'][l]
            if y.get('sale') >= sale_value:
                print(y)
                send_new_posts(y)
