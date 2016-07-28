#!/usr/bin/env python

import datetime
import logging
import pymongo
import requests
import configparser
import os

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
file_handler = logging.FileHandler(filename=config['logging']['scraper_log_file'], mode='a')
file_formatter = logging.Formatter('%(asctime)s %(levelname)s: %(message)s', datefmt="[%d/%m/%Y %H:%M:%S]")
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)


if __name__ == '__main__':

	# MongoDB connection
	conn = pymongo.MongoClient(config['mongodb'].get('host'),config['mongodb'].getint('port'))
	db = conn[config['mongodb'].get('db')]
	indeed = db[config['mongodb'].get('collection')]

	# Misc variables
	start = 0
	posts_inserted = 0
	posts_skipped = 0
	loop_through_api_calls = True
	logger.info("Beginning import.")
	# We don't know how many results we're going to have until we do the first query.
	# So we're going to loop until we've processed the total number of results
	while loop_through_api_calls:
		# Params for the API call.
		# The only one that changes per loop is 'start'.
		params = {
			'publisher':config['indeed'].get('publisher'),
			'v':2,
			'format':'json',
			'q':config['indeed'].get('query'),
			'l':config['indeed'].get('location'),
			'sort':'date',
			'radius':'50',
			'st':'',
			'jt':'fulltime',
			'limit':config['indeed'].getint('limit'),
			'start':start,
			'fromage':config['indeed'].getint('days_back'),
			}

		logger.debug("Loop start: {!s}".format(start))
		# When we store a entry in the DB, we also store when we first saw it.
		retrieval_time = datetime.datetime.utcnow()

		# Ping the API.
		r = requests.get(config['indeed'].get('base_url'),params=params)
		api_response = r.json()
		results = api_response.get('results')

		# Loop through the response.
		for result in results:
			# Extract the stuff we need.
			result_id = result.get('jobkey')
			post_time = datetime.datetime.strptime(result.get('date'), "%a, %d %b %Y %H:%M:%S GMT")
			result_data = {
				'id':result_id,
				'retrieval_time':retrieval_time,
				'post_time':post_time,
				'data':result,
				}
			# Check if we already have this post in the DB.
			already_in_db = list(indeed.find({'id':result_id}))
			if not already_in_db:
				# It's a new post so drop it in.
				logger.debug("Post {!s} not in db, inserting.".format(result_id))
				indeed.insert(result_data)
				posts_inserted += 1
			else:
				# We already ahve this so skip it.
				logger.debug("Post {!s} already in db, skipping.".format(result_id))
				posts_skipped += 1

		# Get the number of the last post on this loop and the total available posts.
		end = api_response.get('end')
		totalResults = api_response.get('totalResults')

		logger.debug("Loop end: {!s}".format(end))
		logger.debug("totalResults: {!s}".format(totalResults))

		# Log out some progress.
		current_progress = float(end) / float(totalResults)
		logger.info("Current progress: {:.0%} ({!s}/{!s})".format(current_progress,end,totalResults))
		logger.debug((posts_inserted,posts_skipped))

		# If the last post we saw is at the end of the total results available, we're done.
		if end >= totalResults:
			loop_through_api_calls = False

		# Set the new start to the current end to get the next set of posts on the next API call.
		start = end

	logger.info("{!s} new posts found. {!s} duplicate posts skipped.".format(posts_inserted,posts_skipped))
	logger.info("Import complete.")