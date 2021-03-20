# doing necessary imports

import logging
import time
from urllib.request import urlopen as uReq

import pymongo
import requests
from bs4 import BeautifulSoup as bs
from flask import Flask, request, render_template
from flask_cors import cross_origin
app = Flask(__name__)  # initialising the flask app with the name 'app'


@app.route('/', methods=['GET'])  # route to display the home page
@cross_origin()
def homePage():
    return render_template("index.html")


@app.route('/review', methods=['POST', 'GET'])  # route to show the review comments in a web UI
@cross_origin()
def index():
    if request.method == 'POST':
        # obtaining the search string entered in the form
        searchString = request.form['content'].replace(" ", "")
        # searchString = "pocomobile"
        try:
            logging.basicConfig(format='%(asctime)s,%(msecs)d %(name)s %(levelname)s %(message)s', datefmt='%H:%M:%S',
                                level=logging.INFO)
            logging.getLogger('urbanGUI')
            # mongodb: // localhost: 27017 
            dbConn = pymongo.MongoClient("mongodb+srv://username:password@srinivasaahlad.njxzl.mongodb.net/crawlerDB?retryWrites=true&w=majority")  # opening a connection to Mongo
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
                prodRes = requests.get(flipkart_url)
                prod_html = bs(prodRes.text, "html.parser")
                logging.info('Loaded Page')
                time.sleep(2)
                try:
                    product_link = f"https://www.flipkart.com{prod_html.select('._2rpwqI')[0].get('href')}"
                except:
                    product_link = f"https://www.flipkart.com{prod_html.select('._1fQZEK')[0].get('href')}"
                logging.info('Product link Fetched From Page')
                prodRes = requests.get(product_link)
                prod_html = bs(prodRes.text, "html.parser")
                logging.info('Getting Required info from Product Page')
                title = prod_html.select_one(".B_NuCI").text
                logging.info('Product title Fetched From Page')
                try:
                    pct_offer = prod_html.select_one("div._3Ay6Sb._31Dcoz > span").text
                except:
                    pct_offer = "No Offer"
                logging.info('Product pct_offer Fetched From Page')
                try:
                    price = prod_html.select_one('div._3I9_wc._2p6lqe').text
                    offer_price = prod_html.select_one("div._30jeq3._16Jk6d").text
                except:
                    price = prod_html.select_one('div._30jeq3._16Jk6d').text
                    offer_price = "No Offer"

                logging.info('Product price Fetched From Page')

                remaining_no_of_reviews = int(
                    prod_html.select_one("div._3UAT2v._16PBlm span").text.split()[1])
                logging.info('Getting Count of Reviews From Page')
                try:
                    available_offers = [ele.text for ele in prod_html.select("._3j4Zjq.row")]
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
                if remaining_no_of_reviews > 10:
                    remaining_no_of_reviews = 10
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
                return render_template('results.html', reviews=reviews)
        except Exception as e:
            print(e)
            return 'Product Not Found / Something is Wrong'
            # return render_template('results.html')
    else:
        return render_template('index.html')


if __name__ == "__main__":
    app.run(debug=True)
    # app.run(port=8000, debug=True)  # running the app on the local machine on port 8000
