import Client from 'https://esm.sh/facilmap-client'


//window.findmarkers = async function(tripname,tribe) {
async function findmarkers(tripname,tribe) {
     var trip = tripname.replace(/ /g, "");
     var tribe = tribe.replace(/ /g, "");
     const client = new Client("https://facilmap.org/HT"+tribe+tripname+"ad");

     client.on("connect", () => {
                console.log("connected");
                //logClientMethods(client);
     });

     client.on("disconnect", () => {
                console.log("disconnected");
     });

     try {
        await client.findOnMap({
            query: "04-08-2024",
        });
        console.log(client.padData, client.types, client.lines);
     } catch (error) {
        console.error("Error finding:", error);
     }



}




