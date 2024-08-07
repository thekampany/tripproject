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

 
# Struggles - Unfinished Business
I want to integrate facilmap. It offers very nice planning options on the map. But how to integrate this with the parts of the trip that are kept in the database?
