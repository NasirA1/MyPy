#! /usr/bin/env python

import os, datetime, time
import codecs
import unicodecsv as csv
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from datetime import datetime
from sys import argv
print("\n" * 100)

# Configure browser session
wd_options = Options()
wd_options.add_argument("--disable-notifications")
wd_options.add_argument("--disable-infobars")
wd_options.add_argument("--mute-audio")
browser = webdriver.Chrome(chrome_options=wd_options)

DATA_FOLDER = './data/'


# --------------- Ask user to log in -----------------
def fb_login():
	print("Opening browser...")
	browser.get("https://www.facebook.com/")
	a = input("Please log into facebook and press enter after the page loads...")

# --------------- Scroll to bottom of page -----------------
def scroll_to_bottom():
	print("Scrolling to bottom...")
	while True:
			try:
				browser.find_element_by_class_name('_4khu') # class after friend's list
				print("Reached end!")
				break
			except:
				browser.execute_script("window.scrollTo(0, document.body.scrollHeight);")
				time.sleep(0.25)
				pass

# --------------- Get list of all friends on page ---------------
def scan_friends():
	print('Scanning page for friends...')
	friends = []
	friend_cards = browser.find_elements_by_xpath('//div[@id="pagelet_timeline_medley_friends"]//div[@class="fsl fwb fcb"]/a')

	for friend in friend_cards:
		if friend.get_attribute('data-hovercard') is None:
			print(" %s (INACTIVE)" % friend.text)
			friend_id = friend.get_attribute('ajaxify').split('id=')[1]
			friend_active = 0
		else:
			print(" %s" % friend.text)
			friend_id = friend.get_attribute('data-hovercard').split('id=')[1].split('&')[0]
			friend_active = 1

		friends.append({
			'name': friend.text.encode('utf-8', 'ignore').decode('utf-8'), #to prevent CSV writing issues
			'id': friend_id,
			'active': friend_active
			})

	print('Found %r friends on page!' % len(friends))
	return friends

# ----------------- Load list from CSV -----------------
def load_csv(filename):
	inact = 0
	myfriends = []
	with open(DATA_FOLDER + filename, 'rb') as input_csv:
		reader = csv.DictReader(input_csv)
		for idx,row in enumerate(reader):
			if row['active'] is '1':
				myfriends.append({
					"name":row['B_name'],
					"uid":row['B_id']
					})
			else:
				print("Skipping %s (inactive)" % row['B_name'])
				inact = inact + 1
	print("%d friends in imported list" % (idx+1))
	print("%d ready for scanning (%d inactive)" % (idx-inact+1, inact))

	return myfriends

# --------------- Scrape 1st degree connections ---------------
def scrape_1st_degrees():
	#Prep CSV Output File
	csvOut = '1st-degree_%s.csv' % now.strftime("%Y-%m-%d_%H%M")
	writer = csv.writer(open(DATA_FOLDER + csvOut, 'wb'))
	writer.writerow(['A_id','A_name','B_id','B_name','active'])

	#Get your unique Facebook ID
	profile_icon = browser.find_element_by_css_selector("[data-click='profile_icon'] > a > span > img")
	myid = profile_icon.get_attribute("id")[19:]

	#Scan your Friends page (1st-degree connections)
	print("Opening Friends page...")
	browser.get("https://www.facebook.com/" + myid + "/friends")
	scroll_to_bottom()
	myfriends = scan_friends()

	#Write connections to CSV File
	for friend in myfriends:
			writer.writerow([myid,"Me",friend['id'],friend['name'],friend['active']])

	print("Successfully saved to %s" % csvOut)
	return csvOut


# --------------- Scrape 2nd degree connections. ---------------
#This can take several days if you have a lot of friends!!
def scrape_2nd_degrees():
	#Prep CSV Output File
	csvOut = '2nd-degree_%s.csv' % now.strftime("%Y-%m-%d_%H%M")
	writer = csv.writer(open(DATA_FOLDER + csvOut, 'wb'))
	writer.writerow(['A_id', 'B_id', 'A_name','B_name','active'])

	#Load friends from CSV Input File
	script, filename = argv
	print("Loading list from %s..." % filename)
	myfriends = load_csv(filename)

	for idx,friend in enumerate(myfriends):
		#Load URL of friend's friend page
		scrape_url = "https://www.facebook.com/"+ friend['uid'] + "/friends?source_ref=pb_friends_tl"
		browser.get(scrape_url)

		#Scan your friends' Friends page (2nd-degree connections)
		print("%d) %s" % (idx+1, scrape_url))
		scroll_to_bottom()
		their_friends = scan_friends()

		#Write connections to CSV File
		print('Writing connections to CSV...')
		for person in their_friends:
			writer.writerow([friend['uid'],person['id'],friend['name'],person['name'],person['active']])
	return csvOut


# --- generate summary file
def generate_summary_from_csv(filepath):
	print('Writing summary to text file...')
	records = None
	
	# load connections from csv file
	with open(DATA_FOLDER + filepath, 'rb') as csvfile:
		records = [line for line in list(csv.reader(csvfile)) if line]

	#sort by name
	friend_names = [rec[3] for rec in records]
	friend_names.sort()

	#write names back to text file
	with codecs.open(DATA_FOLDER + filepath + '.names.txt', 'w', 'utf-8') as txtfile:
		for friend_name in friend_names:
			print (friend_name)
			txtfile.write(friend_name + '\n')


def mkdir(dirpath):
	try:
		os.makedirs(dirpath)
	except FileExistsError:
		# directory already exists
		pass	


# --------------- Start Scraping ---------------
mkdir(DATA_FOLDER)
now = datetime.now()
fb_login()
if len(argv) is 1:
	csvfile = scrape_1st_degrees()
	generate_summary_from_csv(csvfile)
elif len(argv) is 2:
	scrape_2nd_degrees()
else:
	print("Invalid # of arguments specified. Use none to scrape your 1st degree connections, or specify the name of the CSV file as the first argument.")