"use client";

import { useState, useRef, useEffect } from "react";

export default function ChatPanel({
  messages = [],
  onSendMessage = () => {},
  isLoading = false,
  itineraries = [],
  currentItineraryId = null,
  onLoadItinerary = () => {},
  onStartNewItinerary = () => {},
  onDeleteItinerary = () => {}
}) {
  const [inputText, setInputText] = useState("");
  const messagesEndRef = useRef(null);

  // Auto-scroll chat to the bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!inputText.trim() || isLoading) return;
    onSendMessage(inputText.trim());
    setInputText("");
  };

  return (
    <div className="chat-panel">
      {/* 1. Header & Saved List */}
      <div className="chat-header">
        <div className="chat-header-top">
          <h1>Travel Agent</h1>
          <button className="new-trip-btn" onClick={onStartNewItinerary}>
            + New Trip
          </button>
        </div>
        
        {itineraries.length > 0 && (
          <div className="itineraries-picker-section">
            <label htmlFor="itinerary-select">Load Saved Trip:</label>
            <div className="picker-wrapper">
              <select
                id="itinerary-select"
                value={currentItineraryId || ""}
                onChange={(e) => {
                  const val = e.target.value;
                  if (val) onLoadItinerary(parseInt(val, 10));
                }}
              >
                <option value="" disabled>-- Select a Saved Trip --</option>
                {itineraries.map((it) => (
                  <option key={it.id} value={it.id}>
                    {it.title} ({it.destination})
                  </option>
                ))}
              </select>
              {currentItineraryId && (
                <button
                  type="button"
                  className="delete-trip-btn"
                  onClick={() => onDeleteItinerary(currentItineraryId)}
                  title="Delete this trip"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" className="trash-icon">
                    <polyline points="3 6 5 6 21 6"></polyline>
                    <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path>
                    <line x1="10" y1="11" x2="10" y2="17"></line>
                    <line x1="14" y1="11" x2="14" y2="17"></line>
                  </svg>
                </button>
              )}
            </div>
          </div>
        )}
      </div>

      {/* 2. Messages List */}
      <div className="messages-list">
        {messages.length === 0 ? (
          <div className="chat-welcome">
            <h3>Start planning your trip!</h3>
            <p>Try prompting the agent like:</p>
            <div className="prompt-examples">
              <button onClick={() => setInputText("I want a 2-day outdoor trip to Seattle next weekend")}>
                "2-day outdoor Seattle trip"
              </button>
              <button onClick={() => setInputText("Plan a 3-day summer getaway to Miami")}>
                "3-day summer trip to Miami"
              </button>
            </div>
          </div>
        ) : (
          messages.map((msg, index) => (
            <div key={index} className={`message-bubble ${msg.role}`}>
              <div className="bubble-sender">{msg.role === "user" ? "You" : "Travel Agent"}</div>
              <div className="bubble-text">{msg.content}</div>
            </div>
          ))
        )}
        
        {isLoading && (
          <div className="message-bubble model loading">
            <div className="bubble-sender">Travel Agent</div>
            <div className="bubble-text">
              <div className="typing-loader">
                <span></span>
                <span></span>
                <span></span>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* 3. Input Footer */}
      <form className="chat-footer-form" onSubmit={handleSubmit}>
        <input
          type="text"
          value={inputText}
          onChange={(e) => setInputText(e.target.value)}
          placeholder="Ask to build or modify your trip..."
          disabled={isLoading}
        />
        <button type="submit" disabled={!inputText.trim() || isLoading}>
          Send
        </button>
      </form>
    </div>
  );
}
