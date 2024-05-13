const ICON_IDENTIFIER = "icon.";
var olMap;
var popupOverlay;

function getSingleMarker(markerColor, markerSize) {
    console.log(markerColor, markerSize);
    if (markerColor.substring(0, ICON_IDENTIFIER.length) === ICON_IDENTIFIER) {
        return new ol.style.Icon({
            anchor: [0.5, 1.0],
            anchorXUnits: 'fraction',
            anchorYUnits: 'fraction',
            src: markerColor.substring(ICON_IDENTIFIER.length),
            scale: markerSize
        });
    }
    else {
        return new ol.style.Circle({
            radius: markerSize,
            fill: new ol.style.Fill({
                color: markerColor
            })
        });
    }
}

function setMapMarkers(targetTag, zoomLevel, mainMarkers, extraMarkers = {}) {
    if (extraMarkers.color === undefined) {
        extraMarkers.color = "black";
    }
    if (extraMarkers.size === undefined) {
        extraMarkers.size = 1;
    }
    if (extraMarkers.coordinates === undefined) {
        extraMarkers.coordinates = [];
    }
    console.log(targetTag, zoomLevel, mainMarkers, extraMarkers);

    return new ol.Map({
        target: targetTag,
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM()
            }),
            new ol.layer.Vector({
                source: new ol.source.Vector({
                    features: mainMarkers.coordinates.map(({latitude, longitude}) =>
                        new ol.Feature({
                            geometry: new ol.geom.Point(ol.proj.fromLonLat([longitude, latitude]))
                        })
                    )
                }),
                style: new ol.style.Style({
                    image: getSingleMarker(mainMarkers.color, mainMarkers.size)
                })
            }),
            new ol.layer.Vector({
                source: new ol.source.Vector({
                    features: extraMarkers.coordinates.map(({latitude, longitude}) =>
                        new ol.Feature({
                            geometry: new ol.geom.Point(ol.proj.fromLonLat([longitude, latitude]))
                        })
                    )
                }),
                style: new ol.style.Style({
                    image: getSingleMarker(extraMarkers.color, extraMarkers.size)
                })
            })
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([mainMarkers.longitude, mainMarkers.latitude]),
            zoom: zoomLevel
        })
    });
}

function getVectorLayer(markerInfo) {
    return new ol.layer.Vector({
        source: new ol.source.Vector({
            features: [
                new ol.Feature({
                    name: markerInfo.name,
                    link: markerInfo.link,
                    address: markerInfo.address,
                    service_type: markerInfo.service_type,
                    total: markerInfo.total,
                    warningValue: markerInfo.warningValue,
                    errorValue: markerInfo.errorValue,
                    timestamp: markerInfo.timestamp,
                    geometry: new ol.geom.Point(ol.proj.fromLonLat([markerInfo.longitude, markerInfo.latitude]))
                })
            ]
        }),
        style: new ol.style.Style({
            image: getSingleMarker(markerInfo.color, markerInfo.size)
        })
    });
}

function setSeparateMapMarkers(targetTag, zoomLevel, latitude, longitude, markers, zoomAllowed) {
    console.log(targetTag, zoomLevel, markers);

    olMap = new ol.Map({
        target: targetTag,
        controls: [],
        interactions: ol.interaction.defaults({
            mouseWheelZoom: zoomAllowed,
            doubleClickZoom: zoomAllowed,
            dragAndDrop: zoomAllowed,
            keyboardPan: zoomAllowed,
            keyboardZoom: zoomAllowed
        }),
        layers: [
            new ol.layer.Tile({
                source: new ol.source.OSM()
            }),
        ],
        view: new ol.View({
            center: ol.proj.fromLonLat([longitude, latitude]),
            zoom: zoomLevel
        })
    });

    // var i, l, c = map.getControlsBy("zoomWheelEnabled", true);
    // for (i = 0, l = c.length; i < l; i++) {
        // c[i].disableZoomWheel();
    // }

    for (var index in markers) {
        olMap.addLayer(getVectorLayer(markers[index]));
    }
    return map;
}

function addPopupToMap(popupTag, popupContentTag, popupCloserTag, markerHtmlFunc) {
    var container = document.getElementById(popupTag);
    var content = document.getElementById(popupContentTag);
    var closer = document.getElementById(popupCloserTag);

    popupOverlay = new ol.Overlay({
        element: container,
        autoPan: true,
        autoPanAnimation: {
            duration: 250
        }
    });
    olMap.addOverlay(popupOverlay);

    closer.onclick = function() {
        popupOverlay.setPosition(undefined);
        closer.blur();
        return false;
    };

    olMap.on('singleclick', function (event) {
        if (olMap.hasFeatureAtPixel(event.pixel) === true) {
            var coordinate = event.coordinate;
            var feature = olMap.forEachFeatureAtPixel(event.pixel, function(feature) {
                return feature;
            });

            content.innerHTML = markerHtmlFunc(feature);
            popupOverlay.setPosition(coordinate);
        } else {
            popupOverlay.setPosition(undefined);
            closer.blur();
        }
    });

    return olMap;
}

function createClickAtCoordinates(latitude, longitude, popupContentTag, markerHtmlFunc) {
    var content = document.getElementById(popupContentTag);
    var coordinate = ol.proj.fromLonLat([longitude, latitude]);
    var pixel = olMap.getPixelFromCoordinate(coordinate);

    if (olMap.hasFeatureAtPixel(pixel) === true) {
        var feature = olMap.forEachFeatureAtPixel(pixel, function(feature) {
            return feature;
        });
        content.innerHTML = markerHtmlFunc(feature);
        popupOverlay.setPosition(coordinate);
    }
}

function getDashboardMarkerHtml(feature) {
    return '<table class="table">\n' +
           '  <thead>\n' +
           '    <tr>\n' +
           '      <th colspan="2" align="center"><h4 class="title"><a href="' + feature.get("link") + '">' +
                    feature.get("name") + '</a></h4></th>\n' +
           '    </tr>\n' +
           '  </thead>\n' +
           '  <tbody>\n' +
           '    <tr>\n' +
           '      <td colspan="2" align="center"><strong>' + feature.get("address") + '</strong></td>\n' +
           '    </tr>\n' +
           '    <tr>\n' +
           '      <td colspan="2" align="center"><strong>' + feature.get("total").toString() +
                    ' streetlight' + ((feature.get("service_type") == "tampere") ? ' groups' : 's') + '</strong></td>\n' +
           '    </tr>\n' +
           '    <tr>&#8205;</tr><tr>\n' +
           '      <td align="right">' + feature.get("warningValue").toString() + '</td>\n' +
           '      <td>with warnings</td>\n' +
           '    </tr>\n' +
           '    <tr>\n' +
           '      <td align="right">' + feature.get("errorValue").toString() + '</td>\n' +
           '      <td>with errors</td>\n' +
           '    </tr>\n' +
           '  </tbody>\n' +
           '</table>';
}

function getAreaMarkerHtml(feature) {
    return '<table class="table">\n' +
           '  <thead>\n' +
           '    <tr>\n' +
           '      <th align="center"><h3 class="title"><a href="' + feature.get("link") + '">' +
                    feature.get("name") + '</a></h3></th>\n' +
           '    </tr>\n' +
           '  </thead>\n' +
           '  <tbody>\n' +
           '    <tr>\n' +
           '      <td align="center"><strong>' + feature.get("address") + '</strong></td>\n' +
           '    </tr>\n' +
           '    <tr>\n' +
           '      <td align="center">latest update:</td>\n' +
           '    </tr>\n' +
           '    <tr>\n' +
           '      <td align="center">' + feature.get("timestamp") + '</td>\n' +
           '    </tr>\n' +
           '  </tbody>\n' +
           '</table>';
}
