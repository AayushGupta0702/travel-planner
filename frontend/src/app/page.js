"use client";

import { useState, useEffect } from "react";
import dynamic from "next/dynamic";
import ChatPanel from "../components/ChatPanel";
import ItineraryTimeline from "../components/ItineraryTimeline";

// Dynamically import map component because Leaflet accesses window object (cannot be rendered on server)
const Map = dynamic(() => import("../components/Map"), {
  ssr: false,
  loading: () => (
    <div className="map-loading-placeholder">
      <div className="spinner"></div>
      <p>Loading Interactive Map...</p>
    </div>
  )
});

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export default function Home() {
  const [messages, setMessages] = useState([]);
  const [itineraries, setItineraries] = useState([]);
  const [currentItineraryId, setCurrentItineraryId] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [routes, setRoutes] = useState([]);
  const [hoveredActivityId, setHoveredActivityId] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  // 1. Fetch saved itineraries on startup
  useEffect(() => {
    loadSavedItineraries();
  }, []);

  const loadSavedItineraries = async () => {
    try {
      const res = await fetch(`${BACKEND_URL}/api/itineraries`);
      if (res.ok) {
        const data = await res.json();
        setItineraries(data);
      }
    } catch (err) {
      printError("Failed to load saved itineraries", err);
    }
  };

  // 2. Fetch specific itinerary details
  const handleLoadItinerary = async (id) => {
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/itineraries/${id}`);
      if (res.ok) {
        const data = await res.json();
        setCurrentItineraryId(data.id);
        setTimeline(data.timeline || []);
        setRoutes(data.routes || []);
        
        // Reconstruct message history based on loaded timeline if needed,
        // or just set a friendly system welcome.
        setMessages([
          {
            role: "model",
            content: `Successfully loaded trip: "${data.title}" to ${data.destination}! You can ask me to make modifications or add new activities.`
          }
        ]);
      }
    } catch (err) {
      printError("Failed to fetch itinerary details", err);
    } finally {
      setIsLoading(false);
    }
  };

  // 3. Clear/Reset for a New Trip
  const handleStartNewItinerary = () => {
    setCurrentItineraryId(null);
    setTimeline([]);
    setRoutes([]);
    setMessages([]);
    setHoveredActivityId(null);
  };

  // 3b. Delete an Itinerary
  const handleDeleteItinerary = async (id) => {
    if (!window.confirm("Are you sure you want to delete this trip?")) return;
    setIsLoading(true);
    try {
      const res = await fetch(`${BACKEND_URL}/api/itineraries/${id}`, {
        method: "DELETE"
      });
      if (res.ok) {
        if (currentItineraryId === id) {
          handleStartNewItinerary();
        }
        loadSavedItineraries();
      }
    } catch (err) {
      printError("Failed to delete itinerary", err);
    } finally {
      setIsLoading(false);
    }
  };

  // 4. Send Message to Agent API
  const handleSendMessage = async (text) => {
    // Optimistically add user message
    const userMsg = { role: "user", content: text };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const res = await fetch(`${BACKEND_URL}/api/chat`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: text,
          itinerary_id: currentItineraryId
        })
      });

      if (!res.ok) {
        const errorData = await res.json();
        throw new Error(errorData.detail || "Server error");
      }

      const data = await res.json();
      
      // Update states from agent response
      setMessages((prev) => [...prev, { role: "model", content: data.text }]);
      
      if (data.itinerary) {
        setCurrentItineraryId(data.itinerary_id);
        setTimeline(data.itinerary.timeline || []);
        setRoutes(data.itinerary.routes || []);
      }
      
      // Refresh list in sidebar
      loadSavedItineraries();
    } catch (err) {
      printError("Error sending message", err);
      setMessages((prev) => [
        ...prev,
        {
          role: "model",
          content: `⚠️ Error: ${err.message}. Please verify the backend FastAPI server is running and the Gemini API key is configured.`
        }
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="app-layout">
      {/* Col 1: Conversation Panel */}
      <section className="column chat-col">
        <ChatPanel
          messages={messages}
          onSendMessage={handleSendMessage}
          isLoading={isLoading}
          itineraries={itineraries}
          currentItineraryId={currentItineraryId}
          onLoadItinerary={handleLoadItinerary}
          onStartNewItinerary={handleStartNewItinerary}
          onDeleteItinerary={handleDeleteItinerary}
        />
      </section>

      {/* Col 2: Itinerary Timeline Panel */}
      <section className="column timeline-col">
        <ItineraryTimeline
          timeline={timeline}
          hoveredActivityId={hoveredActivityId}
          onHoverActivity={setHoveredActivityId}
        />
      </section>

      {/* Col 3: Interactive Map Panel */}
      <section className="column map-col">
        {timeline && timeline.length > 0 ? (
          <Map
            activities={timeline.flatMap((day) => day.activities || [])}
            routes={routes}
            hoveredActivityId={hoveredActivityId}
          />
        ) : (
          <div className="map-empty-placeholder">
            <div className="ambient-bg"></div>
            <div className="placeholder-content">
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" className="globe-icon">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20" />
                <path d="M2 12h20" />
              </svg>
              <h3>Interactive Trip Map</h3>
              <p>Your routes and sightseeing spots will render here in real time as you chat with your travel agent.</p>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}

function printError(msg, err) {
  console.error(msg, err);
}
