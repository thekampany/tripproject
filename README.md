# Trippanion
The Selfhosted Trip-Planning-Companion application.   
You and your friends go on a trip. This app allows you to share all the details of the trip with the people going on the trip with you. Add links to (or upload) relevant travel documents. 
It is the app in which you answer questions like: what time do we have to be at the airport, should I dress up for dinner or do we go to the beach and eat something there afterwards. 

Besides the main purpose, you can also entertain your fellow travellers by geting them involved in (road)tripbingo and let them win fancy badges. 

The Trippers can invite their friends and family to the tribe. People in the tribe can see an overview of the trip and who is winning the badges.

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
`python manage.py qcluster` - gives the functionality in the application to automatically assign badges on a certain date   

Go to your browser and start with register.  


# Getting Started

1. Create a Tribe by entering a name. A Tribe is you, the people on your trip and de people that you allow to see the tripdetails.
2. Invite the people to the tribe you just created.
3. Create a Trip. Define a period. For all days in the period a dayprogram will already be generated. You can add dayprograms later. You can choose an image. This image will then be used as the background for all the trip pages. On trip level you can also indicate to use Facilmap (https://facilmap.org). When you create a trip automatically a Facilmap will be created based on tribe and trip. When you use Facilmap then you can add makers and lines on the Facilmap. When you do not Facilmap, then you can add points and you can upload gpx files to show routes on the map. In general: if most of your trip is fixed already, then set the points and routes yourself while configuring the trip. When your trip is still largely unplanned, then facilmap is a helpful planning tool.
4. Edit the dayprograms for the trip. Can be a lot of work. Remember, everything can be added and edited during your trip.
5. Optionally add questions to a dayprogram, think of bingo items. 
6. Optionally upload badges.
7. When it works out, create another trip, or when it is with a different group, create another tribe.


# Screenshots
Users see the programme of the trip, see a map of the trip, read the information for a specific day, add suggestions for the day themselves, add photos and text of what they saw, as a reference for later. Trippers can also participate in the tripbingo and see how many badges they have in comparison to the others.
For a tripadmin, the functions to organize the trip are brought together in one overview.

![Screenshot](/screenshots/IMG_3622.PNG )
![Screenshot](/screenshots/IMG_3625.PNG )
![Screenshot](/screenshots/IMG_3503.PNG )
![Screenshot](/screenshots/IMG_3505.PNG )
![Screenshot](/screenshots/IMG_3504.PNG )
![Screenshot](/screenshots/IMG_3506.PNG )
![Screenshot](/screenshots/IMG_3507.PNG )
![Screenshot](/screenshots/IMG_3508.PNG )
![Screenshot](/screenshots/IMG_3509.PNG )
![Screenshot](/screenshots/IMG_3510.PNG )

 
# Struggles - Unfinished Business
I want to integrate facilmap. It offers very nice planning options on the map. But how to integrate this with the parts of the trip that are kept in the database?
