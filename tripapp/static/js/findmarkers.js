import Client from 'https://esm.sh/facilmap-client'


window.findOnMap = async function(tripname,tribe) {
     var trip = tripname.replace(/ /g, "");
     var tribe = tribe.replace(/ /g, "");
     const client = new Client("https://facilmap.org/HT"tribe+trip+"ad");

     client.on("connect", () => {
                console.log("connected");
                //logClientMethods(client);
     });

     client.on("disconnect", () => {
                console.log("disconnected");
     });

     try {
        await client.findOnPad({
            query: "HT"+tribe+trip,
        });
        console.log(client.padData, client.types, client.lines);
     } catch (error) {
        console.error("Error finding:", error);
     }



}




