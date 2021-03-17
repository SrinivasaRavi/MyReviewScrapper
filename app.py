# doing necessary imports

import logging
import time
from urllib.request import urlopen as uReq

import pymongo
import requests
from bs4 import BeautifulSoup as bs
from flask import Flask, request, render_template
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

app = Flask(__name__)  # initialising the flask app with the name 'app'


@app.route('/', methods=['POST', 'GET'])  # route with allowed methods as POST and GET
def index():
    if request.method == 'POST':
        # obtaining the search string entered in the form
        searchString = request.form['content'].replace(" ", "")
        # searchString = "pocomobile"
        try:
            logname = f"{searchString}logs.txt"
            logging.basicConfig(filename=logname,
                                filemode='a',
                                format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s',
                                datefmt='%H:%M:%S',
                                level=logging.INFO)
            logging.getLogger('urbanGUI')
            # mongodb: // localhost: 27017 /
            username = ""
            passwd = ""
            url = ""

            dbConn = pymongo.MongoClient(f"""mongodb + srv: // {username}: {passwd} @ {url} / myFirstDatabase?retryWrites = true & w = majority""")  # opening a connection to Mongo
            logging.info('Database Connection Success')
            db = dbConn['crawlerDB']  # connecting to the database called crawlerDB
            logging.info('connecting to the database called crawlerDB : Success')
            reviews = db[searchString].find({})
            if reviews.count() > 0:
                logging.info('Search For Database : Record Exists')
                return render_template('results.html', reviews=list(reviews))
            else:
                available_offers = []
                flipkart_url = "https://www.flipkart.com/search?q=" + searchString
                chrome_driver_path = r"./chromedriver.exe"
                driver = webdriver.Chrome(chrome_driver_path)
                prodRes = requests.get(flipkart_url)
                prod_html = bs(prodRes.text, "html.parser")
                logging.info('Web Driver started')
                time.sleep(2)
                driver.get(flipkart_url)
                try:
                    product_link = f"https://www.flipkart.com{prod_html.select('._2rpwqI')[0].get('href')}"
                except:
                    product_link = f"https://www.flipkart.com{prod_html.select('._1fQZEK')[0].get('href')}"
                logging.info('Product link Fetched From Page')
                driver.get(product_link)
                logging.info('Loaded Driver with Product Link')
                title = driver.find_element_by_css_selector("span.B_NuCI").text
                logging.info('Product title Fetched From Page')
                try:
                    pct_offer = driver.find_element_by_css_selector("div._3Ay6Sb._31Dcoz > span").text
                except:
                    pct_offer = "No Offer"
                logging.info('Product pct_offer Fetched From Page')
                try:
                    price = driver.find_element_by_css_selector('div._3I9_wc._2p6lqe').text
                    offer_price = driver.find_element_by_css_selector("div._30jeq3._16Jk6d").text
                except:
                    price = driver.find_element_by_css_selector('div._30jeq3._16Jk6d').text
                    offer_price = "No Offer"

                logging.info('Product price Fetched From Page')

                remaining_no_of_reviews = int(
                    driver.find_element_by_css_selector("div._3UAT2v._16PBlm span").text.split()[1])
                logging.info('Getting Count of Reviews From Page')
                try:
                    driver.find_element_by_xpath(
                        '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[3]/div[2]/div/button').click()

                    available_offers = \
                        [my_elem.text for my_elem in
                         WebDriverWait(driver, 5).until(EC.visibility_of_all_elements_located(
                             (By.XPATH, '//*[@id="container"]/div/div[3]/div[1]/div[2]/div[3]/div[2]/div/div')))][
                            0].split('\n')
                except:
                    available_offers.append("No Offers")
                logging.info('Getting Available Offers on Product From Page')
                product_details = {"_id": 1, "Product": searchString, "Price": price, "Offer Price": offer_price,
                                   "speifications": title,
                                   "Offer Percentage": pct_offer, "offers": available_offers}
                reviews = []
                table = db[searchString]
                table.insert_one(product_details)
                reviews.append(product_details)
                try:
                    prodRes = requests.get(product_link)
                    prod_html = bs(prodRes.text, "html.parser")
                    current_url = f'https://www.flipkart.com{prod_html.select("div.col.JOpGWq a")[-1].get("href")}'
                except Exception as e:
                    print(e)
                if remaining_no_of_reviews > 510:
                    remaining_no_of_reviews = 510
                page = 1
                logging.info(f"Number of Reviews to Product: {remaining_no_of_reviews}")
                while remaining_no_of_reviews > 0:
                    try:
                        uClient = uReq(current_url)
                        flipkartPage = uClient.read()
                        comments_html = bs(flipkartPage, "html.parser")
                        commentboxes = comments_html.find_all('div', {'class': "_27M-vq"})
                        for commentbox in commentboxes:
                            try:
                                name = commentbox.div.div.find_all('p', {'class': '_2sc7ZR _2V5EHH'})[0].text
                            except:
                                name = 'No Name'

                            try:
                                rating = commentbox.find('div', {"class": "_3LWZlK _1BLPMq"}).text

                            except:
                                rating = 'No Rating'

                            try:
                                commentHead = commentbox.find('p', {"class": "_2-N8zT"}).text
                            except:
                                commentHead = 'No Comment Heading'

                            try:
                                comtag = commentbox.div.div.find_all('div', {'class': ''})
                                custComment = comtag[0].div.text
                            except:
                                custComment = 'No Customer Comment'
                            try:
                                mydict = {"Customer Name": name,
                                          "Rating": rating,
                                          "CommentHead": commentHead, "CustomerComment": custComment}

                                table.insert_one(mydict)
                                reviews.append(mydict)
                                remaining_no_of_reviews -= 1
                            except:
                                print("Dictionary error")
                        logging.info(f"current page: {page}")
                        page += 1
                        current_url = f'https://www.flipkart.com{comments_html.select("a._1LKTO3")[-1].get("href")}'

                    except Exception as e:
                        print(e)
                driver.close()
                return render_template('results.html', reviews=reviews)
        except Exception as e:
            print(e)
            return 'Product Not Found / Something is Wrong'
            # return render_template('results.html')
    else:
        return render_template('index.html')


if __name__ == "__main__":
    app.run(port=8000, debug=True)  # running the app on the local machine on port 8000
