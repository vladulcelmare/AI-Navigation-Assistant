import React from 'react';
import { useVehicle } from "./VehicleContext.jsx";

function BatteryIcon({ level, color, size = 40 }){
    const fill = Math.max(0, Math.min(100, level));
    const fillWidth = (fill/100) * 74; // inner width
    return (
        <svg width={size} height={size*0.6} viewBox="0 0 100 60" aria-hidden>
            <rect x="2" y="12" width="82" height="36" rx="4" stroke={'#FFFFFF'} fill="none" strokeWidth="4"/>
            <rect x="84" y="22" width="10" height="16" rx="2" stroke={'#FFFFFF'} fill={'#FFFFFF'} />
            <rect x="6" y="16" width={fillWidth} height="28" rx="3" fill={color} />
        </svg>
    );
}

function FuelIcon({ level, color, size = 40 }){
    const fill = Math.max(0, Math.min(100, level));
    const fillHeight = (fill/100) * 36; // inner height
    const y = 48 - fillHeight;
    return (
        <svg width={size} height={size*0.7} viewBox="0 0 100 70" aria-hidden>
            <rect x="6" y="8" width="60" height="52" rx="4" stroke={'#FFFFFF'} fill="none" strokeWidth="4"/>
            <rect x="66" y="22" width="18" height="10" rx="2" stroke={'#FFFFFF'} fill={'#FFFFFF'}/>
            <rect x="10" y={y} width="52" height={fillHeight} rx="2" fill={color} />
        </svg>
    );
}

export function EnergyIndicator(){
    const { selectedVehicle } = useVehicle();
    const telemetry = selectedVehicle?.telemetry;
    const level = Number(telemetry?.current_fuel ?? 0);
    const engine = String(selectedVehicle?.engine_type ?? "").toLowerCase();
    const isElectric = engine.includes("electric");

    const pct = Math.max(0, Math.min(100, level));
    const color = pct >= 60 ? '#16a34a' : (pct >= 20 ? '#f59e0b' : '#ef4444');

    return (
        <div className="h-full bg-white/20 border border-white flex items-center gap-2 p-2 rounded-2xl" style={{minWidth:120}}>
            {!selectedVehicle ? (
                <div className="text-xs text-white/70">Select vehicle</div>
            ) : (
                <>
                    {isElectric ? (
                        <BatteryIcon level={pct} color={color} />
                    ) : (
                        <FuelIcon level={pct} color={color} />
                    )}
                    <div className="flex flex-col">
                        <div style={{fontSize:14, color:'#fff'}}>{Math.round(pct)}%</div>
                        <div style={{fontSize:11, color:'#ddd'}}>{isElectric ? 'Battery' : 'Fuel'}</div>
                    </div>
                </>
            )}
        </div>
    );
}
