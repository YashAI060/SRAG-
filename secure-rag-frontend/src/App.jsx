import React, { useState, useEffect } from 'react';
import { client } from './api/client';
import Auth from './components/Auth';
import Sidebar from './components/Sidebar';
import Chat from './components/Chat';
import TelemetryPanel from './components/TelemetryPanel';
import ErrorBoundary from './components/ErrorBoundary';
import './index.css';

function App() {
  const [isAuthenticated, setIsAuthenticated] = useState(!!client.token);
  const [activeTrace, setActiveTrace] = useState(null);
  const [activeCitations, setActiveCitations] = useState([]);
  const [activeConfidence, setActiveConfidence] = useState(null);

  useEffect(() => {
    // Check if token is still valid (could add a /me endpoint call here)
  }, []);

  const handleLogin = () => {
    setIsAuthenticated(true);
  };

  const handleLogout = () => {
    client.logout();
    setIsAuthenticated(false);
  };

  if (!isAuthenticated) {
    return (
      <ErrorBoundary>
        <Auth onLogin={handleLogin} />
      </ErrorBoundary>
    );
  }

  return (
    <ErrorBoundary>
      <div className="app-container">
        <Sidebar onLogout={handleLogout} />
        <div className="main-content">
          <Chat 
            onNewTrace={(trace, citations, confidence) => {
              setActiveTrace(trace);
              setActiveCitations(citations);
              setActiveConfidence(confidence);
            }} 
          />
        </div>
        {(activeTrace || (activeCitations && activeCitations.length > 0)) && (
          <TelemetryPanel 
            trace={activeTrace} 
            citations={activeCitations} 
            confidence={activeConfidence} 
          />
        )}
      </div>
    </ErrorBoundary>
  );
}

export default App;
