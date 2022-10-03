from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
from csv import writer
import time
import csv
import os
import random
import requests
from bs4 import BeautifulSoup
import threading
from multiprocessing import Process
from fake_useragent import UserAgent
import re
from selectolax.parser import HTMLParser
from webdriver_manager.chrome import ChromeDriverManager

useragent = UserAgent()



with open(f'product_data/finished_category_pages.txt', 'a', encoding='utf-8') as ff:
    ff.close()

def html_write(soup, file_name):
    with open(f'category_pages/{file_name}.txt', 'w', encoding='utf-8') as file:
        links = soup.find_all('a', class_='product-card__main j-card-link')
        for product in links:
            file.write(product.get('href') + '\n')
            print('Получена ссылка на товар: ', product.get('href'))
        file.close()
    print(f'category_pages/{file_name}.txt записан')


def category_links_get():
    with open('category_pages.txt', 'r', encoding='utf-8') as file:
        category_urls = file.read().strip().split('\n')
        return category_urls


def start(category_page, tries):
    options = Options()
    options.add_argument(f"user-agent={useragent.random}")
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1024,720")
    # options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(chrome_options=options)

    file_name = category_page
    if 'promotions' in category_page:
        file_name = category_page.split('promotions/')[1]
    if 'catalog' in category_page:
        file_name = category_page.split('catalog/')[1]
    if 'brands' in category_page:
        file_name = category_page.split('brands/')[1]
    file_name = file_name.replace('/', '+').replace('?', '+').replace('.', '+')
    try:
        driver.get(category_page)
        check_element = None
        try:
            check_element = WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product-card__main.j-card-link")))
            html = driver.page_source
            soup = BeautifulSoup(html, features='html.parser')
            html_write(soup, file_name)
            print("HTML получен")
            driver.close()
        except Exception as e:
            html = driver.page_source
            if 'class="empty-seller"' in str(html):
                raise NameError('Finish page')
            else:
                print('Карточки продуктов на странице не найдены')
                print(e)
                print('Элементы не появились, пробуем снова')
                tries += 1
                print('Попытка: ', tries, '/5')
                if tries <= 5:
                    start(category_page, tries)
                else:
                    success = True
                    return success
        if 'ERR_PROXY_CONNECTION_FAILED' in html:
            raise NameError('ERR_PROXY_CONNECTION_FAILED')
    except OSError as e:
        if 'ProxyError' or 'ConnectTimeout' or 'ERR_PROXY_CONNECTION_FAILED' in str(e):
            raise NameError('ERR_PROXY_CONNECTION_FAILED')
        if 'NameError' in str(type(e)):
            driver.close()
            raise NameError
        else:
            print(type(e).__name__, e.args)
            driver.close()
            raise NameError('ProxyError')

def get_data(link):
    options = Options()
    options.add_argument(f"user-agent={useragent.random}")
    prefs = {'profile.default_content_setting_values': {'images': 2}}
    options.add_experimental_option('prefs', prefs)
    options.add_argument("disable-infobars")
    options.add_argument("--window-size=1024,720")
    options.add_argument("--headless")
    options.add_argument("--disable-extensions")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(chrome_options=options)

    file_name = link.replace('https://www.wildberries.ru/', '').replace('/', '+').replace('?', '+').replace('.', '+')
    driver.get(link)
    WebDriverWait(driver, 15).until(EC.presence_of_element_located((By.CLASS_NAME, "product-page__details-section.details-section")))
    tree = HTMLParser(driver.page_source)
    sku = tree.css_first('#productNmId').text()
    title = tree.css_first('.product-page__header').css_first('h1').text()
    print(title)
    brand = tree.css_first('.product-page__header').text().strip().split("  ")[0]
    category = tree.css('.breadcrumbs__item')[1:-1]
    category_tags = ""
    for i in category:
        category_tags += i.text().strip() + "/"
    category = category_tags
    if len(category) < 5:
        category = 'Зоо (гигиена, груминг, косметика)'
    # print(category)
    with open(f'product_data/{file_name}.csv', 'w', encoding='utf-8', newline='') as file:
        data = {'sku':sku,'name': 'Имя товара', 'value': title}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        data = {'sku':sku,'name': 'Товарная группа', 'value': category}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        data = {'sku':sku,'name': 'Бренд', 'value': brand}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        data = {'sku':sku,'name': 'SKU(ID)', 'value': sku}
        csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        params_table = tree.css('.details__content.collapsable')[-1]
        params = params_table.css('tr')
        for row in params:
            name = row.css_first('th').text().strip()
            value = row.css_first('td').text().strip()
            data = {'name': name, 'value': value}
            print(data)
            csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        bonus_data = tree.css_first('.details-section__inner-wrap')
        info_tabs = bonus_data.css('.details-section__details.details')
        for tab in info_tabs:
            name = tab.css_first('h3').text().strip()
            value = tab.css_first('.details__content.collapsable').text().replace('Развернуть описание', '').replace('\n', '').strip()
            data = {'sku':sku,'name': name, 'value': value}
            print(data)
            csv.DictWriter(file, fieldnames=list(data)).writerow(data)
        file.close()
    driver.close()

def main(category_pages, t_num):
    for category_page in category_pages:
        proxy_tries = 0
        i = 2
        finish_page = False
        file_name = category_page
        while i <= 100 and finish_page == False:
            finish_page = False
            success = 'No'
            while success != 'Yes':
                success = 'No'
                with open('category_pages/111finished_pages.csv', 'r', encoding='utf-8') as finish_file:
                    finished_urls = finish_file.read()
                    finish_file.close()
                if not category_page in finished_urls:
                    print(t_num, ': Пробуем страницу ', category_page)
                    tries = 0
                    try:
                        start(category_page, tries)
                        with open('category_pages/111finished_pages.csv', 'a', encoding='utf-8') as finish_file:
                            finish_file.write(category_page + '\n')
                            finish_file.close()
                        category_page = re.sub(r'page=(\d+)', f'page={i}', category_page)
                        file_name = category_page
                        i+=1
                        proxy_tries = 0
                        success = 'Yes'
                    except Exception as e:
                        print('Тут ошибка', e)
                        if not 'Finish page' in str(e):
                            proxy_tries += 1
                            print('Попытка', proxy_tries, "/5")
                            if proxy_tries == 5:
                                proxy_tries = 0
                        else:
                            print('Достигли последней страницы!')
                            finish_page = True
                            success = 'Yes'
                else:
                    print('Уже собрана: ', category_page)
                    finish_page = True
                    success = 'Yes'

def product_parser(urls, t_num):
    for url in urls:
        with open(f'product_data/finished_product_urls.csv', 'r', encoding='utf-8') as ff:
            finished_pages = ff.read()
            ff.close()
        tries = 1
        if not url in finished_pages:
            success = 'No'
            while success != 'Yes':
                success = 'No'
                print(t_num, 'Пробуем ссылку: ', url)
                try:
                    get_data(url)
                    with open(f'product_data/finished_product_urls.csv', 'a', encoding='utf-8') as ff:
                        ff.write(url + '\n')
                        ff.close()
                    success = 'Yes'
                except Exception as e:
                    print('Ошибка: ', e)
                    if tries < 5:
                        print('Попытка: ', tries, '/5')
                        tries += 1
                    else:
                        print('Не получен: ', url)
                        success = 'Yes'
        else:
            print('Данные продукта уже были получены: ', url)

def product_data_parser():
    files = os.listdir('category_pages')
    open('category_pages/all_products_urls.csv', 'w').close()
    for file in files:
        open('category_pages/all_products_urls.csv', 'a', encoding='utf-8').write('\n' + open(f'category_pages/{file}', 'r').read().strip())
    all_urls = open('category_pages/all_products_urls.csv', 'r', encoding='utf-8').read().split('\n')

    slice = int(len(all_urls) / 5)
    urls_1 = all_urls[0:slice]
    urls_2 = all_urls[slice:slice * 2]
    urls_3 = all_urls[slice * 2:slice * 3]
    urls_4 = all_urls[slice * 3:slice * 4]
    urls_5 = all_urls[slice * 4:]
    #
    t1_new = threading.Thread(target=product_parser, args=(urls_1, '1'))
    t2_new = threading.Thread(target=product_parser, args=(urls_2, '2'))
    t3_new = threading.Thread(target=product_parser, args=(urls_3, '3'))
    t4_new = threading.Thread(target=product_parser, args=(urls_4, '4'))
    t5_new = threading.Thread(target=product_parser, args=(urls_5, '5'))

    t1_new.start()
    t2_new.start()
    t3_new.start()
    t4_new.start()
    t5_new.start()

    t1_new.join()
    t2_new.join()
    t3_new.join()
    t4_new.join()
    t5_new.join()


if __name__ == '__main__':

    category_urls = category_links_get()
    category_urls_arg = category_urls

    slice = int(len(category_urls) / 5)
    category_urls_1 = category_urls_arg[0:slice]
    category_urls_2 = category_urls_arg[slice:slice*2]
    category_urls_3 = category_urls_arg[slice*2:slice*3]
    category_urls_4 = category_urls_arg[slice*3:slice*4]
    category_urls_5 = category_urls_arg[slice*4:]

    t1 = threading.Thread(target=main, args=(category_urls_1, '1'))
    t2 = threading.Thread(target=main, args=(category_urls_2, '2'))
    t3 = threading.Thread(target=main, args=(category_urls_3, '3'))
    t4 = threading.Thread(target=main, args=(category_urls_4, '4'))
    t5 = threading.Thread(target=main, args=(category_urls_5, '5'))
    #
    t1.start()
    t2.start()
    t3.start()
    t4.start()
    t5.start()

    t1.join()
    t2.join()
    t3.join()
    t4.join()
    t5.join()

    product_data_parser()