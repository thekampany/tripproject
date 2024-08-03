import Client from 'https://esm.sh/facilmap-client'

window.initializeMap = async function(tripname,tribe) {
     var trip = tripname.replace(/ /g, "");
     var tribe = tribe.replace(/ /g, "");
     const client = new Client("https://facilmap.org/");

     client.on("connect", () => {
                console.log("connected");
                //logClientMethods(client);
     });

     client.on("disconnect", () => {
                console.log("disconnected");
     });

     try {
        await client.createPad({
            id: "HT"+tribe+trip,
            writeId: "HT"+tribe+trip+"rw",
            adminId: "HT"+tribe+trip+"ad",
            name: trip,
            searchEngines: false,
            description: "Holiday Trip "+tribe+" "+trip,
            clusterMarkers:false ,
            legend1:trip,
            createDefaultTypes:true
        });
        console.log(client.padData, client.types, client.lines);
     } catch (error) {
        console.error("Error creating pad:", error);
     }



}




