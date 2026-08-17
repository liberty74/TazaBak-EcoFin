import React, { useState } from 'react';
import { MapContainer, TileLayer, Marker, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { Navigation, MapPin } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { fetchContainers } from '../api/containers';
import { queryKeys } from '../api/queryKeys';
import { Container } from '../api/types';

const ContainerPopup = ({ container }: { container: Container }) => {
  const handleRoute = () => {
    window.open(`https://yandex.ru/maps/?pt=${container.longitude},${container.latitude}&z=16&l=map`, '_blank');
  };

  return (
    <div className="p-1 min-w-[200px]">
      <div className="flex items-center gap-2 mb-2">
        <div className="w-8 h-8 bg-primary/10 text-primary rounded-lg flex items-center justify-center">
          <MapPin className="w-5 h-5" />
        </div>
        <div>
          <h3 className="font-bold text-sm">{container.name}</h3>
          <p className="text-[10px] text-graphite/60">{container.address}</p>
        </div>
      </div>
      
      <div className="mb-3">
        <div className="flex justify-between text-xs mb-1">
          <span className="text-graphite/60">Заполненность</span>
          <span className="font-bold">{container.fill_percent}%</span>
        </div>
        <div className="w-full bg-sand rounded-full h-2">
          <div 
            className="bg-primary h-2 rounded-full transition-all" 
            style={{ 
              width: `${container.fill_percent}%`,
              backgroundColor: container.fill_percent >= 80 ? '#D64545' : container.fill_percent >= 50 ? '#F59E42' : '#39A96B'
            }}
          />
        </div>
      </div>

      <button 
        onClick={handleRoute}
        className="w-full bg-primary/10 text-primary hover:bg-primary hover:text-white transition-colors py-2 rounded-lg text-xs font-bold flex items-center justify-center gap-2"
      >
        <Navigation className="w-3 h-3" />
        Маршрут
      </button>
    </div>
  );
};

export default function MapPage() {
  const kokshetauCenter = [53.2846, 69.3833] as [number, number];

  const { data: containers = [], isLoading } = useQuery({
    queryKey: queryKeys.containers(false), // Fetch all, active or inactive
    queryFn: () => fetchContainers(false),
  });

  const getMarkerIcon = (isActive: boolean, fillLevel: number) => {
    let color = '#39A96B'; // green
    if (!isActive) color = '#A0AEC0'; // gray for inactive
    else if (fillLevel >= 80) color = '#D64545'; // red
    else if (fillLevel >= 50) color = '#F59E42'; // orange
    
    return L.divIcon({
      className: 'custom-div-icon',
      html: `<div style="background-color: ${color}; width: 24px; height: 24px; border-radius: 50%; border: 3px solid white; box-shadow: 0 2px 5px rgba(0,0,0,0.3);"></div>`,
      iconSize: [24, 24],
      iconAnchor: [12, 12]
    });
  };

  const activeCount = containers.filter(c => c.is_active).length;

  return (
    <div className="flex flex-col h-[100dvh] bg-background relative z-0">
      {/* Map Header */}
      <div className="absolute top-4 left-4 right-4 z-[400] flex justify-between items-center pointer-events-none mt-16 md:mt-0">
        <div className="bg-white/90 backdrop-blur-md px-4 py-3 rounded-2xl shadow-lg pointer-events-auto border border-sand">
          <h1 className="font-bold text-lg text-primary">Карта Смарт-Баков</h1>
          <p className="text-xs text-graphite/60">
            {isLoading ? 'Загрузка...' : `Кокшетау • ${activeCount} онлайн`}
          </p>
        </div>
      </div>

      <MapContainer 
        center={kokshetauCenter} 
        zoom={14} 
        className="w-full h-full z-0"
        zoomControl={false}
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png"
        />
        
        {containers.map((container) => (
          <Marker 
            key={container.id} 
            position={[container.latitude, container.longitude]}
            icon={getMarkerIcon(container.is_active, container.fill_percent)}
          >
            <Popup className="rounded-xl overflow-hidden border-none shadow-xl">
              <ContainerPopup container={container} />
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
