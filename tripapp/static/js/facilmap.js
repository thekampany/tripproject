        import Client from 'https://esm.sh/facilmap-client'
        import 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'
        import 'https://unpkg.com/facilmap-leaflet@3/dist/facilmap-leaflet.full.js'

async function createPad() {
  try {
    // Roep de createPad methode aan
    const response = await client.createPad({
      id: 'theKampanyFr', writeId: 'theKampanyFrrw'  ,adminId: 'theKampanyFrad' ,
      name: 'MijnNieuwePad',
      searchEngines: false,
      description: 'Dit is een voorbeeld pad',
      clusterMarkers: true,
      legend1: 'Legenda boven',
      legend2: 'Legenda onder',
      createDefaultTypes: true
    });

    console.log('Pad gecreëerd:', response);
  } catch (error) {
    console.error('Er is een fout opgetreden bij het creëren van het pad:', error);
  }
}

        async function initializeMap() {
            //const map = L.map('map').setView([51.505, -0.09], 13);
            const map = L.map('map').locate({setView: true, maxZoom: 16});

            L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
              maxZoom: 19,
              attribution: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            }).addTo(map);

            //const client = new Client("https://facilmap.org/","FZmSbpw9jBPIcIFf");
            const client = new Client("https://facilmap.org/");

            client.on("connect", () => {
                console.log("connected");
                logClientMethods(client);
            });

            client.on("disconnect", () => {
                console.log("disconnected");
            });

            await client.setPadId("FZmSbpw9jBPIcIFf");
            //await client.createPad({id: "theKampanyFr", writeId: "theKampanyFrrw" ,adminId: "theKampanyFrad" , name : "test" ,searchEngines: false,description: "The description for search engines", clusterMarkers:false ,legend1:"Fr", legend2:"test2", createDefaultTypes:true})
            //createPad();
            console.log("show me markers ", client.markers);            
            console.log(client.padData, client.types, client.lines);

	    const layers = L.FacilMap.getLayers(map);
	    const byName = (layerMap) => Object.fromEntries(Object.entries(layerMap).map(([key, layer]) => [layer.options.fmName, layer]));
	    L.control.layers(byName(layers.baseLayers), byName(layers.overlays)).addTo(map);



            const bbox = new L.FacilMap.BboxHandler(map, client).enable();

            const markersLayer = new L.FacilMap.MarkersLayer(client).addTo(map)
                .on("click", (e) => {
                    markersLayer.setHighlightedMarkers(new Set([e.layer.marker.id]));
                    linesLayer.setHighlightedLines(new Set());
                    searchResultsLayer.setHighlightedResults(new Set());
                    overpassLayer.setHighlightedElements(new Set());
                });

            const linesLayer = new L.FacilMap.LinesLayer(client).addTo(map)
		.on("click", (e) => {
			L.DomEvent.stopPropagation(e);
			markersLayer.setHighlightedMarkers(new Set());
			linesLayer.setHighlightedLines(new Set([e.layer.line.id]));
			searchResultsLayer.setHighlightedResults(new Set());
			overpassLayer.setHighlightedElements(new Set());
		});

	    const routeLayer1 = new L.FacilMap.RouteLayer(client, undefined, { raised: true }).addTo(map);
	    const routeLayer2 = new L.FacilMap.RouteLayer(client, "route2", { raised: true }).addTo(map);
	    const routeDragHandler = new L.FacilMap.RouteDragHandler(map, client).enable();
	    setTimeout(() => {
				routeDragHandler.enableForLayer(routeLayer1);
				routeDragHandler.enableForLayer(routeLayer2);
		}, 0);


            const searchResultsLayer = new L.FacilMap.SearchResultsLayer().addTo(map)
		.on("click", (e) => {
			L.DomEvent.stopPropagation(e);
			markersLayer.setHighlightedMarkers(new Set());
			linesLayer.setHighlightedLines(new Set());
			searchResultsLayer.setHighlightedResults(new Set([ e.layer._fmSearchResult ]));
			overpassLayer.setHighlightedElements(new Set());
		});

	    map.on("click", () => {
		markersLayer.setHighlightedMarkers(new Set());
		linesLayer.setHighlightedLines(new Set());
		searchResultsLayer.setHighlightedResults(new Set());
		overpassLayer.setHighlightedElements(new Set());
	    });

            try {
              await client.findOnMap({
                query: "04-08-2024",
              });
              console.log("query:", client.lines,client.markers);
            } catch (error) {
              console.error("Error finding:", error);
            }


	    let overpassLoading = 0;
	    const overpassStatus = document.getElementById("overpass-status");
	    const overpassLayer = new L.FacilMap.OverpassLayer([], { markerShape: "rectangle-marker" }).addTo(map)
		.on("click", (e) => {
			console.log(e.layer._fmOverpassElement.tags);
			L.DomEvent.stopPropagation(e);
			markersLayer.setHighlightedMarkers(new Set());
			linesLayer.setHighlightedLines(new Set());
			searchResultsLayer.setHighlightedResults(new Set());
			overpassLayer.setHighlightedElements(new Set([e.layer._fmOverpassElement]));
		})
		.on("loadstart", () => {
			overpassLoading++;
			overpassStatus.innerText = "Loading POIs…";
			overpassStatus.style.opacity = 1;
		})
		.on("loadend", (e) => {
			if (--overpassLoading <= 0) {
				if (e.status == L.FacilMap.OverpassLoadStatus.COMPLETE)
					overpassStatus.style.opacity = 0;
				else if (e.status == L.FacilMap.OverpassLoadStatus.INCOMPLETE)
					overpassStatus.innerText = "Not all POIs are shown because there are too many results. Zoom in to show all results.";
				else if (e.status == L.FacilMap.OverpassLoadStatus.TIMEOUT)
					overpassStatus.innerText = "Zoom in to show POIs.";
				else if (e.status == L.FacilMap.OverpassLoadStatus.ERROR)
					overpassStatus.innerText = "Error loading POIs: " + e.error.message;
				}

				console.log("Overpass", e);
		})
		.on("clear", () => {
			overpassStatus.style.opacity = 0;
		});

	    const hashHandler = new L.FacilMap.HashHandler(map, client, { overpassLayer }).enable();

            //await client.updateBbox({ top: 53.5566, left: 8.7506, right: 19.8468, bottom: 50.1980, zoom: 8 });

            //await client.addMarker({id:123, name:"namepje", lat:"4.5", lon:"51.1" });
            //await client.find({query:"Leiden",loadUrls: false });
            //console.log(client)


        }

        function logClientMethods(obj) {
            let props = [];
            let proto = obj;
            do {
                props = props.concat(Object.getOwnPropertyNames(proto));
            } while (proto = Object.getPrototypeOf(proto));

            props = props.sort().filter((e, i, arr) => { 
                if (e != arr[i + 1] && typeof obj[e] == 'function') return true;
            });

            console.log("Available methods and properties:");
            console.log(props);
        }

        initializeMap();



