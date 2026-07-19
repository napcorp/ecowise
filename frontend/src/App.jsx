import { useState, useEffect } from 'react'
import { Routes, Route, NavLink } from 'react-router-dom'
import ChatPanel from './components/ChatPanel'
import DeviceMonitor from './components/DeviceMonitor'
import SidePane from './components/SidePane'
import './App.css'

const INITIAL_MESSAGES = [
  {
    sender: 'bot',
    text: "Hello there, buddy! EcoWise here. I'm all booted up, synced with your home's telemetry, and ready to keep you company. Let's make some simple, green choices today!"
  }
]

function App() {
  const [devices, setDevices] = useState([])
  const [events, setEvents] = useState([])
  const [messages, setMessages] = useState(INITIAL_MESSAGES)
  const [telemetry, setTelemetry] = useState({
    time: 'Detecting...',
    location: 'Detecting...',
    weather: 'Detecting...'
  })
  const [isDrawerOpen, setIsDrawerOpen] = useState(false)
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false)

  // Fetch devices
  const fetchDevices = async () => {
    try {
      const res = await fetch('/api/devices')
      const data = await res.json()
      setDevices(data)
      
      const eventRes = await fetch('/api/events')
      const eventData = await eventRes.json()
      setEvents(eventData)
    } catch (err) {
      console.error("Error polling devices state: ", err)
    }
  }

  // Fetch telemetry once
  const loadTelemetry = async () => {
    try {
      const res = await fetch('/api/telemetry')
      const data = await res.json()
      setTelemetry(data)
    } catch (err) {
      console.error("Error loading telemetry: ", err)
    }
  }

  const handleReset = async () => {
    try {
      const res = await fetch('/api/chat/clear', { method: 'POST' })
      if (res.ok) {
        setMessages(INITIAL_MESSAGES)
      }
    } catch (err) {
      console.error("Error during memory reset: ", err)
    }
  }

  useEffect(() => {
    fetchDevices()
    const deviceInterval = setInterval(fetchDevices, 1500)
    
    setTimeout(loadTelemetry, 500)
    
    // Fallback timer just for UI feel if telemetry fails
    const timeInterval = setInterval(() => {
      setTelemetry(prev => {
        if(prev.time === 'Detecting...') return prev;
        const now = new Date()
        const days = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
        let hours = now.getHours()
        let minutes = now.getMinutes()
        const ampm = hours >= 12 ? 'PM' : 'AM'
        hours = hours % 12
        hours = hours ? hours : 12
        minutes = minutes < 10 ? '0'+minutes : minutes
        const timeStr = `${days[now.getDay()]}, ${months[now.getMonth()]} ${now.getDate()}, ${now.getFullYear()} at ${hours}:${minutes} ${ampm}`
        
        return { ...prev, time: timeStr }
      })
    }, 1000)

    return () => {
      clearInterval(deviceInterval)
      clearInterval(timeInterval)
    }
  }, [])

  const handleDeviceUpdate = async (deviceId, key, value) => {
    try {
      const res = await fetch(`/api/devices/${deviceId}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ key, value })
      })
      const data = await res.json()
      if (data.success) {
        fetchDevices()
      }
    } catch (err) {
      console.error("Error updating device state manually: ", err)
    }
  }

  return (
    <>
      <header>
        <div className="header-logo">
            <span className="logo-icon">🌿</span>
            <div>
                <h1>EcoWise</h1>
                <p className="motto">Nurturing habits, protecting our planet, together.</p>
                <p className="subheading">Empowering you to live sustainably with smart, simple steps.</p>
            </div>
        </div>
        
        {/* Navigation - Desktop */}
        <nav className="desktop-only" style={{ display: 'flex', gap: '1.5rem', marginLeft: '2rem', marginRight: 'auto', alignItems: 'center' }}>
            <NavLink to="/" style={({ isActive }) => ({ fontWeight: isActive ? '700' : '500', color: isActive ? 'var(--accent-green)' : 'var(--text-secondary)', textDecoration: 'none', fontSize: '1.1rem', transition: 'color 0.2s' })}>Chat</NavLink>
            <NavLink to="/simulations" style={({ isActive }) => ({ fontWeight: isActive ? '700' : '500', color: isActive ? 'var(--accent-green)' : 'var(--text-secondary)', textDecoration: 'none', fontSize: '1.1rem', transition: 'color 0.2s' })}>Simulations</NavLink>
        </nav>

        {/* Desktop Telemetry Bar */}
        <div className="telemetry-bar desktop-only">
            <div className="telemetry-item">
                📍 Location: <strong>{telemetry.location}</strong>
            </div>
            <div className="telemetry-item">
                ⛅ Weather: <strong>{telemetry.weather}</strong>
            </div>
            <div className="telemetry-item">
                🕒 Time: <strong>{telemetry.time}</strong>
            </div>
        </div>

        {/* Mobile Hamburger Button */}
        <button 
            className="hamburger-btn mobile-only"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
            title="Toggle Menu"
        >
            {isMobileMenuOpen ? '✕' : '☰'}
        </button>
      </header>

      {/* Mobile Telemetry Dropdown */}
      <div className={`mobile-menu ${isMobileMenuOpen ? 'open' : ''}`}>
          <NavLink to="/" className="btn btn-secondary mobile-sim-btn" onClick={() => setIsMobileMenuOpen(false)} style={({ isActive }) => ({ marginTop: '0.5rem', width: '100%', display: 'flex', justifyContent: 'center', gap: '0.5rem', color: isActive ? 'var(--accent-green)' : 'var(--text-primary)' })}>
              💬 Chat
          </NavLink>
          <NavLink to="/simulations" className="btn btn-secondary mobile-sim-btn" onClick={() => setIsMobileMenuOpen(false)} style={({ isActive }) => ({ marginTop: '0.5rem', width: '100%', display: 'flex', justifyContent: 'center', gap: '0.5rem', color: isActive ? 'var(--accent-green)' : 'var(--text-primary)' })}>
              ⚙️ Simulations
          </NavLink>
          <div className="telemetry-item" style={{ marginTop: '1rem' }}>
              📍 Location: <strong>{telemetry.location}</strong>
          </div>
          <div className="telemetry-item">
              ⛅ Weather: <strong>{telemetry.weather}</strong>
          </div>
          <div className="telemetry-item">
              🕒 Time: <strong>{telemetry.time}</strong>
          </div>
      </div>

      <Routes>
        <Route path="/" element={
          <div className="portal-grid" style={{ gridTemplateColumns: '1fr' }}>
            <ChatPanel 
              fetchDevices={fetchDevices} 
              messages={messages} 
              setMessages={setMessages}
            />
          </div>
        } />
        <Route path="/simulations" element={
          <>
            <div className="portal-grid" style={{ gridTemplateColumns: '1fr' }}>
              <DeviceMonitor devices={devices} events={events} />
            </div>
            <button className="simulator-fab" onClick={() => setIsDrawerOpen(!isDrawerOpen)}>
                ⚙️ Advanced Simulator
            </button>
            <SidePane 
              isOpen={isDrawerOpen} 
              onClose={() => setIsDrawerOpen(false)} 
              devices={devices}
              events={events}
              fetchEvents={fetchDevices}
              handleDeviceUpdate={handleDeviceUpdate}
              onReset={handleReset}
            />
          </>
        } />
      </Routes>
    </>
  )
}

export default App
