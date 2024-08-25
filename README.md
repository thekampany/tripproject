# Tripproject
You and your friends go on a trip. This app allows you to share all the details of the trip with the people going on the trip with you. Add links to (or upload) relevant travel documents. 
It is the app in which you answer questions like: what time do we have to be at the airport, should I dress up for dinner or do we go to the beach and eat something there afterwards. 

Besides the main purpose, you can also entertain your fellow travellers by geting them involved in (road)tripbingo and let them win fancy badges. 

The Trippers can invite their friends and family to the tribe. People in the tribe can see an overview of the trip and who is winning the badges.

# Installation
`git clone https://github.com/thekampany/tripproject.git`  
edit  docker-compose.yml for portnumbers and dbuser and password  
`cp .env.sample .env`  
edit .env for unsplash api key and for emailsettings  
  
`docker compose build`  
`docker compose up -d`  
In the container `python manage.py migrate`  
Go to your browser and start with register.  

# Screenshots
Users see the programme of the trip, see a map of the trip, read the information for a specific day, add suggestions for the day themselves, add photos and text of what they saw, as a reference for later. Trippers can also participate in the tripbingo and see how many badges they have in comparison to the others.
For a tripadmin, the functions to organize the trip are brought together in one overview.

![Screenshot](/screenshots/IMG_3501.PNG )
![Screenshot](/screenshots/IMG_3502.PNG )
![Screenshot](/screenshots/IMG_3503.PNG )
![Screenshot](/screenshots/IMG_3504.PNG )
![Screenshot](/screenshots/IMG_3505.PNG )
![Screenshot](/screenshots/IMG_3506.PNG )
![Screenshot](/screenshots/IMG_3507.PNG )
![Screenshot](/screenshots/IMG_3508.PNG )
![Screenshot](/screenshots/IMG_3509.PNG )
![Screenshot](/screenshots/IMG_3510.PNG )
 
# Struggles - Unfinished Business
I want to integrate facilmap. It offers very nice planning options on the map. But how to integrate this with the parts of the trip that are kept in the database?
