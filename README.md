# Trippanion
The Selfhosted Trip-Planning-Companion application.   

You and your family / friends go on a trip. 
_While planning the trip_   
You have a central place to store all information coming out of the booking mails rather than having some of them in your own mailbox, and others in the mailbox of your spouse / co planner(s).  

_During the trip,_ 
this app allows you to share all the details of the trip with the people going on the trip with you and that just were not that involved in the planning. It is the app in which you answer questions like: what time do we have to be at the airport? Do we have an active day in nature, or do we have a cultural day with museumsvitis? etc.  

_After the trip_
the app provides you with the schedule and with all the content you added as a memory.  


_The application also has the following features:_  
:globe_with_meridians:  Show a map of the trip itinerary and show a map with the points of interest for one particular day.  
:moneybag:  Add expenses and keep a simple overview of who owes and who gets. Including currency conversion.    
:heavy_check_mark:  Keep a check/pack/wishlist.  
:camera:  Each traveller on the trip can add personal logentries and photos.  
:link:  Add documents for easy access like hotelreservations, flightconfirmations, but also copy of your passport or medical documents.  
:game_die:  You can also entertain your fellow travellers by geting them involved in (road)tripbingo and let them win fancy badges.  

_Integrations with other selfhosted apps:_  
Add a Dawarich api key and see your tracks - did you go where you planned you would go?  
Add an Immich api key and see where you took a photo  

_Control your data:_  
Your (trip)data is on your server and you decide who can view your tripdata. 
The application provides the option to export the details of trip to a zipped html file. So you can keep a memory of the trip also when you shutdown your instance.

# Installation

## By cloning the repository

`git clone https://github.com/thekampany/tripproject.git`  

Edit  docker-compose.yml for portnumbers and dbuser and password  
When you are editing portnumbers also check portnumber in nginx.conf  

`cp .env.sample .env`  

Edit .env  
Emailsettings in .env are needed for inviting others to the trip and resetting passwords.  
Unsplash api key in .env is used for displaying roadtrip backgrounds on the welcome and organize page. Can be left blank. Unsplash images are not used on the pages for a specific trip, here you can upload your own background image.   
The superuser in .env is an adminuser that you create to access the Django admin. This can also be the first user for logging in.  
Optionally enter a url of your docker staticmaps selfhostedinstance. This will enable the option to generate maps that will be part of downloadable offline html.  

After setting up the .env file, do:  

`docker compose build`  
`docker compose up -d`  

Go to your browser using the app_url as in your .env and start with register or use the superuser from your .env file to log in.


## Docker Compose

Create  .env file.  

```
APP_NAME = 'Trippanion' #shows only on welcome page  
APP_URL = 'http://mytrippanion.mydomain.com' #include port when needed  
DEBUG = False  
DJANGO_KEY = 'xxxxx'  # enter a long string 
APP_CURRENCY = 'EUR'  # when enabling expenses in what currency do you want to see them?  
TEMPERATURE_UNIT = 'C' # C or F for showing temperature in weather forecast  
TIME_ZONE = 'Europe/Amsterdam'  
DATABASE_URL = postgres://tripappuser:tripapppassword@db:5432/tripappdb  
CSRF_TRUSTED_ORIGINS = http://localhost:8043,http://example.com  
DEFAULT_FROM_EMAIL = 'holidaytrips@example.com' # emailsettings in order to invite others and do password resets  
EMAIL_HOST = 'smtp.server.tld'  
EMAIL_PORT = 587  
EMAIL_USE_TLS = True  
EMAIL_HOST_USER = 'username'   
EMAIL_HOST_PASSWORD = 'password'  
SUPERUSER_NAME=admin #needed if you want to use Django admin, for convenience keep it same as the user you are registering for yourself  
SUPERUSER_EMAIL=admin@example.com  
SUPERUSER_PASSWORD=adminpassword  
UNSPLASH_ACCESS_KEY = 'xxxxx' #optional - for showing background images on trip overview page  
EXCHANGERATE_API_KEY = 'xxxxxxxxx' #optional - for calculating tripexpenses to the app_currency: exchangerate-api.com  
STATICMAPS_URL = 'http://mystaticmaps.mydomain.com/api/staticmaps' #optional - for being able to generate offline maps using https://github.com/dietrichmax/docker-staticmaps  
STATICMAPS_API_KEY = 'xxxxxxxx' # use when your staticmaps server has allow_api_keyless_access set to false  
```


In the same folder as .env file save docker-compose.yml file with below content:   

```
services:
  web:
    image: thekampany/trippanion_web:latest
    volumes:
      - static_volume:/usr/src/app/staticfiles
      - media_volume:/usr/src/app/media
    expose:
      - 8000
    env_file:
      - .env
    depends_on:
      - db
    container_name: trippanion_web

  nginx:
    image: thekampany/trippanion_nginx:latest
    container_name: trippanion_nginx
    ports:
      - "8043:8043"
    volumes:
      - static_volume:/usr/src/app/staticfiles
      - media_volume:/usr/src/app/media
    depends_on:
      - web

  db:
    image: postgres:13
    container_name: trippanion_db
    volumes:
      - tripapp_postgres_data:/var/lib/postgresql/data
    environment:
      POSTGRES_DB: tripappdb
      POSTGRES_USER: tripappuser
      POSTGRES_PASSWORD: tripapppassword

volumes:
  static_volume:
  media_volume:
  tripapp_postgres_data:

```
After creating the .env and docker-compose.yml file do:  
`docker compose up -d`  



# Getting Started & Using the application

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

 
# Unfinished Business
Facilmap can be opened in a trip. It offers very nice planning options on the map. I am not yet satisfied with the way it is integrated in the app. Work in progress.  

# Credits
Flags from https://flagpedia.net  
Weather from https://api.open-meteo.com  
