"use client";

export default function ItineraryTimeline({ timeline = [], hoveredActivityId = null, onHoverActivity = () => {} }) {
  if (!timeline || timeline.length === 0) {
    return (
      <div className="timeline-empty">
        <p>No itinerary loaded. Ask the agent to plan a trip to see it visualized here!</p>
      </div>
    );
  }

  // Pre-calculate flat indices for all activities to align with map markers
  let flatIndexCounter = 0;
  const enrichedTimeline = timeline.map((day) => {
    const enrichedActivities = (day.activities || []).map((act) => {
      const flatIndex = flatIndexCounter++;
      return { ...act, flatIndex };
    });
    return { ...day, activities: enrichedActivities };
  });

  return (
    <div className="timeline-container">
      <div className="timeline-header">
        <h2>Your Custom Itinerary</h2>
      </div>
      <div className="timeline-days-list">
        {enrichedTimeline.map((day, dIdx) => (
          <div key={dIdx} className="timeline-day-section">
            <div className="day-header-badge">
              Day {day.day_number || dIdx + 1} &bull; {day.date}
            </div>
            
            <div className="day-activities-container">
              {day.activities.map((act) => {
                const isHovered = hoveredActivityId === act.flatIndex;
                return (
                  <div
                    key={act.flatIndex}
                    className={`activity-card ${isHovered ? "active" : ""}`}
                    onMouseEnter={() => onHoverActivity(act.flatIndex)}
                    onMouseLeave={() => onHoverActivity(null)}
                  >
                    <div className="activity-left-bar">
                      <div className="activity-connector-dot" />
                      <div className="activity-number-icon">{act.flatIndex + 1}</div>
                    </div>
                    
                    <div className="activity-content">
                      <div className="activity-meta">
                        <span className="activity-time">{act.time}</span>
                        {act.weather_condition && (
                          <span className="activity-weather-badge">
                            {act.weather_condition}
                          </span>
                        )}
                      </div>
                      
                      <h3 className="activity-name">{act.name}</h3>
                      <p className="activity-description">{act.description}</p>
                    </div>
                  </div>
                );
              })}
              {(!day.activities || day.activities.length === 0) && (
                <p className="no-activities">No activities planned for this day.</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
