import datetime
import pytz
import json
import os
import pymongo
from bson import json_util
import configparser
import os
import logging

from flask import Flask, Response, render_template
app = Flask(__name__)

# Config setup
cwd = os.path.dirname(os.path.abspath(__file__))
config_filename = 'config.ini'
config_file_path = os.path.join(cwd, config_filename)
config = configparser.ConfigParser()
config.read(config_file_path)

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt="[%d/%m/%Y %H:%M:%S]"))
logger.addHandler(handler)
file_handler = logging.FileHandler(filename=config['logging']['api_log_file'], mode='a')
file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt="[%d/%m/%Y %H:%M:%S]")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

@app.route("/indeed", strict_slashes=False)
# @app.route("/indeed/")
@app.route("/indeed/<startdate>", strict_slashes=False)
# @app.route("/indeed/<startdate>/")
@app.route("/indeed/<startdate>/<enddate>", strict_slashes=False)
# @app.route("/indeed/<startdate>/<enddate>/")
def indeed(startdate=None,enddate=None):
    if not startdate:
        tz = pytz.timezone(config['api'].get('local_timezone'))
        today = datetime.datetime.now(tz).date()
        midnight = tz.localize(datetime.datetime.combine(today,datetime.time(0,0)), is_dst=None)
        midnight_as_utc = midnight.astimezone(pytz.utc)
        startdate = midnight_as_utc - datetime.timedelta(days=1)
    else:
        startdate = datetime.datetime.strptime(startdate,'%Y-%m-%d')
    if not enddate:
        enddate = datetime.datetime.utcnow()
    else:
        enddate = datetime.datetime.strptime(enddate,'%Y-%m-%d')
    conn = pymongo.MongoClient(config['mongodb'].get('host'),config['mongodb'].getint('port'))
    db = conn[config['mongodb'].get('db')]
    indeed = db[config['mongodb'].get('collection')]
    results = indeed.find({
                            'post_time':{
                                '$gte':startdate,
                                '$lt':enddate,
                                }
                            }).sort([
                                ('post_time',-1),
                                ])
    results = list(results)
    json_out = json.dumps(results,default=json_util.default)
    conn.close()
    return Response(json_out,mimetype='application/json')


@app.route("/")
def index():
    html_out = render_template("jobs.html")
    return html_out



if __name__ == "__main__":
    app.run(host='0.0.0.0',port=config['api'].getint('port'))



