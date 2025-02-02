# Trippanion
The Selfhosted Trip-Planning-Companion application.   
You and your family / friends go on a trip. 
While planning the trip you have a central place to store all the booking mails rather than having some of them in your own mailbox, and others in the mailbox of your spouse / co planner(s).
During the trip, this app allows you to share all the details of the trip with the people going on the trip with you and that just were not that involved in the planning. It is the app in which you answer questions like: what time do we have to be at the airport, should I dress up for dinner or do we go to the beach and eat something there afterwards. 

The application also has the following features:
Show a map of the trip itinerary and show a map with the points of interest for one particular day.  
Add expenses and keep a simple overview of who owes and who gets. Also when making expenses in foreign currency.    
Keep a check/pack/wishlist.  
Each traveller on the trip can add personal logentries and photos.  

You can also entertain your fellow travellers by geting them involved in (road)tripbingo and let them win fancy badges. 

Add a Dawarich api key and see your tracks - did you go where you planned you would go?  
Add an Immich api key and see where you took a photo  

The Trippers can invite their friends and family to the tribe. People in the tribe can see an overview of the trip and who is winning the badges. 
Your (trip)data is on your server and you decide who can view your tripdata. 


# Installation
`git clone https://github.com/thekampany/tripproject.git`  
Edit  docker-compose.yml for portnumbers and dbuser and password  
`cp .env.sample .env`  
Edit .env  
Emailsettings in .env are needed for inviting others to the trip and resetting passwords.  
Unsplash api key in .env is used for displaying roadtrip backgrounds on the welcome and organize page. Can be left blank. Unsplash images are not used on the pages for a specific trip, here you can upload your own background image.   
  
`docker compose build`  
`docker compose up -d`  

Log in the web container to do some additional steps:  
~~`python manage.py migrate`~~ - should no longer be necessary     
`python manage.py createsuperuser` - in order to use the Django Admin    
~~`python manage.py qcluster`~~ - gives the functionality in the application to automatically assign badges on a certain date; should no longer be necessary  

Go to your browser using the url from your .env and start with register.  


# Getting Started

1. Create a Tribe by entering a name. A Tribe is you, the people on your trip and the people that you allow to see the tripdetails.
2. Invite the people to the tribe you just created.
3. Create a Trip. Define a period. For all days in the period a dayprogram will already be generated. You can add dayprograms later. You can choose an image. This image will then be used as the background for all the trip pages. On trip level you can also indicate to use Facilmap (https://facilmap.org). When you create a trip automatically a Facilmap will be created based on tribe and trip. When you use Facilmap then you can add makers and lines on the Facilmap. When you do not Facilmap, then you can add points and you can upload gpx files to show routes on the map. In general: if most of your trip is fixed already, then set the points and routes yourself while configuring the trip. When your trip is still largely unplanned, then facilmap is a helpful planning tool.
4. Edit the dayprograms for the trip. Can be a lot of work. Remember, everything can be added and edited during your trip.
5. Optionally add questions to a dayprogram, think of bingo items. 
6. Optionally upload badges.
7. Optionally a Tripper can add an api-key of a selfhosted Dawarich instance (https://dawarich.app/).
8. Optionally a Tripper can add an api-key of a selfhosted Immich instance (https://immich.app/).
9. When it works out, create another trip, or when it is with a different group, create another tribe.


# Screenshots
Users see the programme of the trip, see a map of the trip, read the information for a specific day, add suggestions for the day themselves, add photos and text of what they saw, as a reference for later. Trippers can also participate in the tripbingo and see how many badges they have in comparison to the others.
For a tripadmin, the functions to organize the trip are brought together in one overview.

![Screenshot](/screenshots/trippanion-screenshot-1-mytrips.png )
![Screenshot](/screenshots/trippanion-screenshot-2-tripdetail.png )
![Screenshot](/screenshots/trippanion-screenshot-3-tripday.png )
![Screenshot](/screenshots/trippanion-screenshot-4-tripdaymap.png )
![Screenshot](/screenshots/trippanion-screenshot-5-trippers.png )

 
# Struggles - Unfinished Business
Facilmap can be opened in a trip. It offers very nice planning options on the map. I am not yet satisfied with the way it is integrated in teh app. Work in progress.  

# Credits
Flags from https://flagpedia.net