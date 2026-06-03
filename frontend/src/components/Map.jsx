"use client";

import { useEffect, useRef } from "react";
import L from "leaflet";
import "leaflet/dist/leaflet.css";

export default function Map({ activities = [], routes = [], hoveredActivityId = null }) {
  const mapContainerRef = useRef(null);
  const mapRef = useRef(null);
  const markersRef = useRef({});
  const polylineRef = useRef(null);

  // 1. Initialize Map
  useEffect(() => {
    if (!mapContainerRef.current || mapRef.current) return;

    // Start centered in Seattle, default zoom 10
    const map = L.map(mapContainerRef.current, {
      zoomControl: false // Disable to add custom styled zoom controls later or keep top right
    }).setView([47.6062, -122.3321], 11);

    L.tileLayer("https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png", {
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>',
      subdomains: "abcd",
      maxZoom: 20
    }).addTo(map);

    L.control.zoom({ position: "bottomright" }).addTo(map);

    mapRef.current = map;

    return () => {
      if (mapRef.current) {
        mapRef.current.remove();
        mapRef.current = null;
      }
    };
  }, []);

  // 2. Render Markers and Routes when activities change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    // Clear previous markers
    Object.values(markersRef.current).forEach((marker) => map.removeLayer(marker));
    markersRef.current = {};

    // Clear previous polyline
    if (polylineRef.current) {
      map.removeLayer(polylineRef.current);
      polylineRef.current = null;
    }

    if (!activities || activities.length === 0) return;

    const bounds = [];
    let activityCounter = 1;

    // Place Markers
    activities.forEach((act, index) => {
      const { name, latitude, longitude, description, time } = act;
      if (latitude == null || longitude == null) return;

      const lat = floatOrZero(latitude);
      const lng = floatOrZero(longitude);
      bounds.push([lat, lng]);

      // Custom premium HTML marker icon
      const icon = L.divIcon({
        html: `
          <div class="map-marker-pin" id="marker-pin-${index}">
            <span class="marker-number">${activityCounter++}</span>
          </div>
        `,
        className: "custom-map-marker",
        iconSize: [32, 32],
        iconAnchor: [16, 32],
        popupAnchor: [0, -32]
      });

      const popupContent = `
        <div class="map-popup-card">
          <div class="popup-time">${time || ""}</div>
          <h4 class="popup-title">${name}</h4>
          <p class="popup-description">${description || ""}</p>
        </div>
      `;

      const marker = L.marker([lat, lng], { icon })
        .addTo(map)
        .bindPopup(popupContent, { closeButton: false });

      // Save reference to marker
      markersRef.current[index] = marker;
    });

    // Draw route polylines
    const allCoords = [];
    if (routes && routes.length > 0) {
      routes.forEach((dayRoute) => {
        const geom = dayRoute?.route?.geometry;
        if (geom && geom.coordinates) {
          // GeoJSON coordinates are [lng, lat] - we need [lat, lng] for Leaflet
          const leafletCoords = geom.coordinates.map(([lng, lat]) => [lat, lng]);
          allCoords.push(...leafletCoords);
        }
      });
    }

    if (allCoords.length > 0) {
      const polyline = L.polyline(allCoords, {
        color: "#6366f1",
        weight: 4,
        opacity: 0.8,
        dashArray: "6, 8" // beautiful dashed line animation look
      }).addTo(map);
      polylineRef.current = polyline;
    }

    // Zoom/Pan Map to fit itinerary bounds
    if (bounds.length > 0) {
      map.fitBounds(bounds, { padding: [50, 50], maxZoom: 14, animate: true, duration: 1.5 });
    }
  }, [activities, routes]);

  // 3. Highlight hovered activity
  useEffect(() => {
    if (hoveredActivityId === null || !markersRef.current) return;
    
    const marker = markersRef.current[hoveredActivityId];
    if (marker) {
      marker.openPopup();
      // Center map slightly offset to leave space for popup
      const map = mapRef.current;
      if (map) {
        map.panTo(marker.getLatLng(), { animate: true, duration: 0.5 });
      }
    }
  }, [hoveredActivityId]);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div ref={mapContainerRef} style={{ width: "100%", height: "100%" }} />
    </div>
  );
}

function floatOrZero(val) {
  const f = parseFloat(val);
  return isNaN(f) ? 0.0 : f;
}
