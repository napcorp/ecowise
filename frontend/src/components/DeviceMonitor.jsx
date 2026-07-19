export default function DeviceMonitor({ devices, events = [] }) {
  const avatars = {
    thermostat: '🌡️',
    coffee_plug: '☕',
    bedroom_lamp: '💡',
    garden_irrigation: '💦'
  }

  return (
    <div className="panel">
        <div className="panel-header">
            <div className="panel-title">🌿 Device Status Monitor</div>
        </div>
        <div className="devices-body">
          {devices.map(device => {
            const isActive = device.status === 'ON'
            let detailsText = ''
            if (device.id === 'thermostat') {
                detailsText = `Set to ${device.value}°F | Mode: ${device.mode} ${device.eco_mode ? '(Eco Leaf 🍃)' : ''}`
            } else if (device.id === 'coffee_plug') {
                detailsText = isActive ? `Active (${device.device_connected}) | Drawing ${device.power_watts}W` : `Idle (${device.device_connected})`
            } else if (device.id === 'bedroom_lamp') {
                detailsText = isActive ? `Glow Brightness: ${device.value}%` : `Powered Off`
            } else if (device.id === 'garden_irrigation') {
                detailsText = isActive ? `Sprinklers Active` : `System Idle`
            }

            return (
              <div key={device.id} className={`status-card ${isActive ? 'active' : ''}`}>
                  <div className="device-info">
                      <div className="device-avatar">{avatars[device.id] || '⚙️'}</div>
                      <div className="device-details">
                          <h3>{device.name}</h3>
                          <p>{detailsText}</p>
                      </div>
                  </div>
                  <span className={`badge-status ${isActive ? 'on' : 'off'}`}>
                      {isActive ? '● ON' : '○ OFF'}
                  </span>
              </div>
            )
          })}
        </div>

        {events.length > 0 && (
          <>
            <div className="panel-header" style={{ marginTop: '1rem', borderTop: '1px solid rgba(15, 23, 42, 0.05)' }}>
                <div className="panel-title">📅 Upcoming Events</div>
            </div>
            <div className="devices-body" style={{ gridTemplateRows: 'auto' }}>
              {events.map(event => (
                <div key={event.id} className="status-card">
                    <div className="device-info">
                        <div className="device-avatar" style={{ fontSize: '1.2rem' }}>🗓️</div>
                        <div className="device-details">
                            <h3 style={{ fontSize: '1.05rem' }}>{event.title}</h3>
                            <p>{event.time}</p>
                        </div>
                    </div>
                </div>
              ))}
            </div>
          </>
        )}
    </div>
  )
}
