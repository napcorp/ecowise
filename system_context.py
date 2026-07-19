import psutil
import json

def get_battery_info():
    try:
        battery = psutil.sensors_battery()
        if battery:
            status = "Plugged In" if battery.power_plugged else "On Battery"
            return f"{battery.percent}% ({status})"
        return "Desktop PC (No Battery)"
    except Exception:
        return "Unknown"

def get_network_info():
    try:
        stats = psutil.net_if_stats()
        active_interfaces = []
        for name, stat in stats.items():
            if stat.isup and name not in ["Loopback Pseudo-Interface 1", "lo"]:
                if "Wi-Fi" in name or "Wireless" in name:
                    active_interfaces.append(f"{name} (Wireless)")
                elif "Ethernet" in name:
                    active_interfaces.append(f"{name} (Wired)")
                else:
                    active_interfaces.append(name)
        if active_interfaces:
            return ", ".join(active_interfaces)
        return "Offline / No Data"
    except Exception:
        return "Unknown"

def get_top_processes():
    try:
        # Get all processes, sort by memory usage, take top 5
        processes = []
        for p in psutil.process_iter(['name', 'memory_info']):
            try:
                if p.info['name'] and p.info['memory_info']:
                    mem_mb = p.info['memory_info'].rss / (1024 * 1024)
                    processes.append({'name': p.info['name'], 'mem': mem_mb})
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
                
        # Sort descending by memory
        processes.sort(key=lambda x: x['mem'], reverse=True)
        
        # Filter to avoid spamming the exact same process (like multiple chromes)
        unique_apps = []
        seen = set()
        for p in processes:
            name = p['name'].lower().replace('.exe', '')
            if name not in seen and name not in ['svchost', 'system', 'registry', 'memory compression', 'dwm', 'explorer', 'csrss']:
                unique_apps.append(p['name'])
                seen.add(name)
            if len(unique_apps) >= 5:
                break
                
        if unique_apps:
            return ", ".join(unique_apps)
        return "Minimal Activity"
    except Exception:
        return "Unknown"

def get_mock_personal_data():
    return {
        "calendar": [
            "Today 3:00 PM - Dentist Appointment",
            "Tomorrow 10:00 AM - Video call with grandkids"
        ],
        "emails": [
            "Electricity Bill due in 3 days ($45.20)",
            "Reminder: Neighborhood Watch Meeting tonight at 7 PM"
        ]
    }

def get_full_system_context():
    """Builds the comprehensive system context block to inject into the LLM prompt."""
    battery = get_battery_info()
    network = get_network_info()
    processes = get_top_processes()
    personal = get_mock_personal_data()
    
    context_str = "[LIVE SYSTEM & PERSONAL CONTEXT]\n"
    context_str += f"Battery: {battery}\n"
    context_str += f"Network: {network}\n"
    context_str += f"Active Apps: {processes}\n"
    
    context_str += "\nUpcoming Events (Calendar):\n"
    for event in personal["calendar"]:
        context_str += f"- {event}\n"
        
    context_str += "\nRecent Important Emails/Bills:\n"
    for email in personal["emails"]:
        context_str += f"- {email}\n"
        
    return context_str

if __name__ == "__main__":
    print(get_full_system_context())
