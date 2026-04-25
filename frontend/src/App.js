import React, { useState, useRef, useEffect } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import axios from 'axios';
import './App.css';
import { useGeolocation } from './hooks/useGeolocation';

const API_BASE = process.env.REACT_APP_API_BASE || "/api";

function App() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([
    { text: "Hi! Ask me about places or directions. I'll find nearby spots and guide you there.", isUser: false }
  ]);
  const [places, setPlaces] = useState([]);
  const [directions, setDirections] = useState(null);
  const [showDirections, setShowDirections] = useState(false);
  const [mapCenter, setMapCenter] = useState(null);
  const [userLocation, setUserLocation] = useState(null);
  const [showConsent, setShowConsent] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const mapRef = useRef(null);
  const mapInstanceRef = useRef(null);
  const markersRef = useRef([]);
  const routeLayerRef = useRef(null);
  const messagesEndRef = useRef(null);

  const { coords, status, error, accuracy, retry } = useGeolocation();

  useEffect(() => {
    if (coords) {
      setUserLocation(coords);
      if (!mapCenter) {
        setMapCenter({ lat: coords.lat, lng: coords.lng });
      }
    }
  }, [coords, mapCenter]);

  useEffect(() => {
    if (status === "idle" && !coords) {
      setShowConsent(true);
    }
  }, [status, coords]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleAllowLocation = () => {
    setShowConsent(false);
    retry();
  };

  const mapInitializedRef = useRef(false);

  useEffect(() => {
    if (!mapInitializedRef.current && mapRef.current) {
      mapInitializedRef.current = true;
      mapInstanceRef.current = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: true
      }).setView([34.0775, -117.6897], 14);

      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap'
      }).addTo(mapInstanceRef.current);
    }
  }, []);

  useEffect(() => {
    if (mapInstanceRef.current && mapCenter) {
      const lat = mapCenter.lat;
      const lng = mapCenter.lng;
      if (lat !== undefined && lng !== undefined && Number.isFinite(lat) && Number.isFinite(lng)) {
        mapInstanceRef.current.setView([lat, lng], 14);
      }
    }
  }, [mapCenter]);

  useEffect(() => {
    if (!mapInstanceRef.current || !userLocation) return;

    const lat = userLocation.lat;
    const lng = userLocation.lng;
    if (lat === undefined || lng === undefined || !Number.isFinite(lat) || !Number.isFinite(lng)) return;

    markersRef.current.forEach(m => m.remove());
    markersRef.current = [];

    const userMarker = L.marker([lat, lng], {
      icon: L.divIcon({
        className: 'user-location-marker',
        html: '<div style="background:#3b82f6;width:20px;height:20px;border-radius:50%;border:3px solid white;box-shadow:0 0 8px rgba(0,0,0,0.3)"><div style="position:absolute;top:50%;left:50%;transform:translate(-50%,-50%);width:8px;height:8px;background:white;border-radius:50%"></div></div>',
        iconSize: [20, 20],
        iconAnchor: [10, 10]
      })
    }).addTo(mapInstanceRef.current).bindPopup("Your Location");
    markersRef.current.push(userMarker);
  }, [userLocation]);

  useEffect(() => {
    if (!mapInstanceRef.current || !places.length) return;

    places.forEach((place) => {
      const lat = place.location?.lat;
      const lng = place.location?.lng;
      if (lat !== undefined && lng !== undefined && Number.isFinite(lat) && Number.isFinite(lng)) {
        const marker = L.marker([lat, lng])
          .addTo(mapInstanceRef.current)
          .bindPopup(`<b>${place.name}</b><br>${place.vicinity || ''}`);
        markersRef.current.push(marker);
      }
    });
  }, [places]);

  useEffect(() => {
    if (!mapInstanceRef.current) return;

    if (routeLayerRef.current) {
      routeLayerRef.current.remove();
      routeLayerRef.current = null;
    }

    if (directions?.polyline) {
      const coords = decodePolyline(directions.polyline);
      if (coords.length) {
        routeLayerRef.current = L.polyline(coords, {
          color: '#3b82f6',
          weight: 6,
          opacity: 0.8
        }).addTo(mapInstanceRef.current);
        
        mapInstanceRef.current.fitBounds(routeLayerRef.current.getBounds(), { padding: [50, 50] });
      }
    }
  }, [directions]);

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    setIsLoading(true);
    const userMsg = input;
    const newMessages = [...messages, { text: userMsg, isUser: true }];
    setMessages(newMessages);
    setInput('');

    try {
      const payload = {
        text: userMsg,
        location: userLocation,
        session_id: "default"
      };
      console.log("Sending request:", payload);
      
      const { data } = await axios.post(`${API_BASE}/chat`, payload, { timeout: 15000 });
      console.log("API response:", data);

      setMessages(prev => [...prev, { text: data.response, isUser: false }]);

      if (data.places?.length > 0) {
        setPlaces(data.places);
        const dest = data.places[0];
        if (dest.location?.lat && dest.location?.lng) {
          setMapCenter({ lat: dest.location.lat, lng: dest.location.lng });
        }
      }

      if (data.directions?.length > 0) {
        setDirections(data.directions[0]);
        setShowDirections(true);
      } else {
        setDirections(null);
        setShowDirections(false);
      }
    } catch (err) {
      console.error("API Error:", err);
      setMessages(prev => [...prev, {
        text: "Sorry, couldn't reach the server. Please check your connection.",
        isUser: false
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const closeDirections = () => {
    setShowDirections(false);
    if (routeLayerRef.current) {
      routeLayerRef.current.remove();
      routeLayerRef.current = null;
    }
    setDirections(null);
  };

  const formatDistance = (meters) => {
    if (!meters) return '';
    if (meters < 1000) return `${Math.round(meters)} m`;
    return `${(meters / 1000).toFixed(1)} km`;
  };

  const formatDuration = (seconds) => {
    if (!seconds) return '';
    const mins = Math.round(seconds / 60);
    if (mins < 60) return `${mins} min`;
    return `${Math.floor(mins / 60)} hr ${mins % 60} min`;
  };

  function decodePolyline(str) {
    if (!str) return [];
    let index = 0, lat = 0, lng = 0, coordinates = [];
    while (index < str.length) {
      let b, shift = 0, result = 0;
      do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      let dlat = ((result & 1) ? ~(result >> 1) : (result >> 1));
      lat += dlat;
      shift = 0; result = 0;
      do { b = str.charCodeAt(index++) - 63; result |= (b & 0x1f) << shift; shift += 5; } while (b >= 0x20);
      let dlng = ((result & 1) ? ~(result >> 1) : (result >> 1));
      lng += dlng;
      coordinates.push([lat / 1e5, lng / 1e5]);
    }
    return coordinates;
  }

  const accuracyLabel = {
    gps: 'GPS',
    'gps-approx': 'GPS (approx)',
    ip: 'IP Location',
    loading: 'Finding...'
  };

  return (
    <>
      {showConsent && (
        <div className="consent-modal">
          <div className="consent-content">
            <h3>Enable Location</h3>
            <p>This helps me find places and directions near you.</p>
            {error && <p style={{color: '#dc2626', fontSize: '13px'}}>{error}</p>}
            <div style={{display: 'flex', gap: '10px', justifyContent: 'center'}}>
              <button onClick={handleAllowLocation}>Enable</button>
              <button onClick={() => setShowConsent(false)} style={{background: '#9ca3af'}}>Skip</button>
            </div>
          </div>
        </div>
      )}
      
      <div className="app-container">
        <div className="map-container" ref={mapRef} />

        <div className="chat-container">
          <div className="location-bar">
            <div className="location-indicator">
              <div className={`location-dot ${accuracy || 'loading'}`} />
              <span>
                {status === 'ok' 
                  ? `Using ${accuracyLabel[accuracy] || 'location'}`
                  : status === 'loading' 
                    ? 'Getting location...' 
                    : 'Location unavailable'}
              </span>
            </div>
            <button className="refresh-btn" onClick={retry}>Refresh</button>
          </div>

          {showDirections && directions && (
            <div className="route-card">
              <div className="route-header">
                <h4>Directions</h4>
                <div className="route-stats">
                  {directions.distance_text && <span>{formatDistance(directions.distance_text)}</span>}
                  {directions.duration_text && <span>{formatDuration(directions.duration_text)}</span>}
                </div>
                <button className="route-close" onClick={closeDirections}>&times;</button>
              </div>
              <ul className="steps-list">
                {directions.steps?.map((step, i) => (
                  <li key={i} className="step-item">
                    <div className="step-icon">
                      {i === directions.steps.length - 1 ? '✓' : i + 1}
                    </div>
                    <div>
                      <div className="step-text">{step.instruction || step}</div>
                      {step.distance_text && <div className="step-distance">{formatDistance(step.distance_text)}</div>}
                    </div>
                  </li>
                ))}
              </ul>
            </div>
          )}

          <div className="messages">
            {messages.map((msg, i) => (
              <div key={i} className={`message ${msg.isUser ? "user" : "ai"}`}>
                {msg.text}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>

          <div className="input-area">
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={(e) => e.key === 'Enter' && handleSend()}
              placeholder="Ask about places or directions..."
              disabled={isLoading}
            />
            <button onClick={handleSend} disabled={isLoading}>
              {isLoading ? '...' : 'Send'}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

export default App;
