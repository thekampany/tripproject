// ========================================
// UNIFIED ICON SYSTEM - Color Coded
// ========================================

const COLORS = {
    route_start: '#28a745',
    route_end: '#dc3545',
    accommodation: '#6f42c1',
    food: '#fd7e14',
    activity: '#007bff',
    location: '#6c757d',
    poi: '#ffc107',
    default: '#ffffff'
};

function uniformIcon(color, emoji, size = 30) {
    return L.divIcon({
        html: `<div style="background:${color};width:${size}px;height:${size}px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:${size*0.6}px;border:2px solid white;box-shadow:0 2px 4px rgba(0,0,0,0.3)">${emoji}</div>`,
        className: '',
        iconSize: [size, size],
        iconAnchor: [size/2, size/2],
        popupAnchor: [0, -size/2]
    });
}
