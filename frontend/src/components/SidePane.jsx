import { useState, useEffect } from 'react'
import './SidePane.css' // We will put the drawer specific CSS here to keep index cleaner

export default function SidePane({ isOpen, onClose, devices, events = [], fetchEvents, handleDeviceUpdate, onReset }) {
  if (!devices || devices.length === 0) return null

  const getDevice = (id) => devices.find(d => d.id === id) || {}

  const thermostat = getDevice('thermostat')
  const coffeePlug = getDevice('coffee_plug')
  const bedroomLamp = getDevice('bedroom_lamp')
  const gardenIrrigation = getDevice('garden_irrigation')

  const [newEventTitle, setNewEventTitle] = useState('')
  const [newEventTime, setNewEventTime] = useState('')

  const handleAddEvent = async () => {
    if (!newEventTitle || !newEventTime) return
    try {
      await fetch('/api/events', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ title: newEventTitle, time: newEventTime })
      })
      setNewEventTitle('')
      setNewEventTime('')
      if (fetchEvents) fetchEvents()
    } catch (err) {
      console.error(err)
    }
  }

  const handleDeleteEvent = async (id) => {
    try {
      await fetch(`/api/events/${id}`, { method: 'DELETE' })
      if (fetchEvents) fetchEvents()
    } catch (err) {
      console.error(err)
    }
  }

  const toggleSwitch = (deviceId, key, checked, isBoolean = false) => {
    let val = checked
    if (!isBoolean) val = val ? 'ON' : 'OFF'
    handleDeviceUpdate(deviceId, key, val)
  }

  const handleResetWithConfirm = () => {
    if (window.confirm("Are you sure you want to reset ALL memory, context, and device states? This cannot be undone.")) {
      onReset()
    }
  }

  return (
    <div className={`sim-drawer ${isOpen ? 'open' : ''}`}>
        <div className="sim-header">
            <h2>⚙️ Advanced Simulator Controls</h2>
            <button className="sim-close" onClick={onClose}>×</button>
        </div>
        <div className="sim-body">
            
            {/* Thermostat Controls */}
            <div className="control-group">
                <div className="control-header">
                    <span className="control-title">Living Room Thermostat</span>
                    <label className="switch">
                        <input 
                          type="checkbox" 
                          checked={thermostat.status === 'ON'}
                          onChange={(e) => toggleSwitch('thermostat', 'status', e.target.checked)} 
                        />
                        <span className="slider"></span>
                    </label>
                </div>
                <div className="range-container">
                    <div className="range-label-row">
                        <span>Target Temp</span>
                        <span>{thermostat.value}°F</span>
                    </div>
                    <input 
                      type="range" 
                      className="sim-range" 
                      min="50" max="90" 
                      value={thermostat.value || 72}
                      onChange={(e) => handleDeviceUpdate('thermostat', 'value', parseInt(e.target.value))} 
                    />
                </div>
                <div style={{ marginTop: '1rem' }}>
                    <div className="range-label-row" style={{ marginBottom: '0.4rem' }}>
                        <span>System Mode</span>
                    </div>
                    <div className="selector-tabs">
                        {['Cooling', 'Heating', 'OFF'].map(mode => (
                          <button 
                            key={mode}
                            className={`tab-btn ${thermostat.mode === mode ? 'active' : ''}`}
                            onClick={() => handleDeviceUpdate('thermostat', 'mode', mode)}
                          >
                            {mode}
                          </button>
                        ))}
                    </div>
                </div>
                <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>Eco Mode</span>
                    <label className="switch">
                        <input 
                          type="checkbox" 
                          checked={!!thermostat.eco_mode}
                          onChange={(e) => toggleSwitch('thermostat', 'eco_mode', e.target.checked, true)} 
                        />
                        <span className="slider"></span>
                    </label>
                </div>
            </div>

            {/* Smart Plug Controls */}
            <div className="control-group">
                <div className="control-header">
                    <span className="control-title">Kitchen Smart Plug (Coffee Maker)</span>
                    <label className="switch">
                        <input 
                          type="checkbox" 
                          checked={coffeePlug.status === 'ON'}
                          onChange={(e) => toggleSwitch('coffee_plug', 'status', e.target.checked)} 
                        />
                        <span className="slider"></span>
                    </label>
                </div>
                <div className="range-label-row">
                    <span>Power Usage</span>
                    <span>{coffeePlug.power_watts || 0} Watts</span>
                </div>
            </div>

            {/* Bedroom Lamp Controls */}
            <div className="control-group">
                <div className="control-header">
                    <span className="control-title">Bedroom Lamp</span>
                    <label className="switch">
                        <input 
                          type="checkbox" 
                          checked={bedroomLamp.status === 'ON'}
                          onChange={(e) => toggleSwitch('bedroom_lamp', 'status', e.target.checked)} 
                        />
                        <span className="slider"></span>
                    </label>
                </div>
                <div className="range-container">
                    <div className="range-label-row">
                        <span>Brightness</span>
                        <span>{bedroomLamp.value || 80}%</span>
                    </div>
                    <input 
                      type="range" 
                      className="sim-range" 
                      min="10" max="100" 
                      value={bedroomLamp.value || 80}
                      onChange={(e) => handleDeviceUpdate('bedroom_lamp', 'value', parseInt(e.target.value))} 
                    />
                </div>
            </div>

            {/* Garden Irrigation Controls */}
            <div className="control-group">
                <div className="control-header">
                    <span className="control-title">Garden Irrigation</span>
                    <label className="switch">
                        <input 
                          type="checkbox" 
                          checked={gardenIrrigation.status === 'ON'}
                          onChange={(e) => toggleSwitch('garden_irrigation', 'status', e.target.checked)} 
                        />
                        <span className="slider"></span>
                    </label>
                </div>
            </div>

            {/* Calendar Events Simulator */}
            <div className="control-group">
                <div className="control-header" style={{ marginBottom: '1rem' }}>
                    <span className="control-title">Calendar & Reminders</span>
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginBottom: '1rem' }}>
                    {events.length === 0 ? (
                        <span style={{ fontSize: '0.9rem', color: 'var(--text-secondary)' }}>No events scheduled.</span>
                    ) : (
                        events.map(ev => (
                            <div key={ev.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: 'rgba(15, 23, 42, 0.05)', padding: '0.5rem 1rem', borderRadius: '8px' }}>
                                <div style={{ display: 'flex', flexDirection: 'column' }}>
                                    <div style={{ fontSize: '0.95rem', fontWeight: 'bold' }}>{ev.title}</div>
                                    <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{ev.time}</div>
                                </div>
                                <button onClick={() => handleDeleteEvent(ev.id)} style={{ background: 'transparent', border: 'none', color: '#ef4444', cursor: 'pointer', fontSize: '1.2rem' }}>×</button>
                            </div>
                        ))
                    )}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                    <input 
                        type="text" 
                        placeholder="Event Title" 
                        className="chat-input-large" 
                        style={{ padding: '0.6rem', fontSize: '0.9rem', width: '100%' }}
                        value={newEventTitle}
                        onChange={e => setNewEventTitle(e.target.value)}
                    />
                    <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <input 
                            type="text" 
                            placeholder="Time (e.g. 5:00 PM)" 
                            className="chat-input-large" 
                            style={{ flex: 1, padding: '0.6rem', fontSize: '0.9rem', minWidth: '0' }}
                            value={newEventTime}
                            onChange={e => setNewEventTime(e.target.value)}
                        />
                        <button className="btn btn-secondary" onClick={handleAddEvent} style={{ padding: '0.6rem 1rem' }}>Add</button>
                    </div>
                </div>
            </div>

            {/* System Actions */}
            <div className="control-group reset-group">
                <button className="btn btn-reset" onClick={handleResetWithConfirm}>
                    ⚠️ Reset Memory & Context
                </button>
            </div>

        </div>
    </div>
  )
}
