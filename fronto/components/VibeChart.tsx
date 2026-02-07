import React from 'react';
import { AreaChart, Area, XAxis, Tooltip, ResponsiveContainer } from 'recharts';
import { VibeData } from '../types';

interface VibeChartProps {
  data: VibeData[];
}

const VibeChart: React.FC<VibeChartProps> = ({ data }) => {
  return (
    <div className="h-32 w-full mt-8 opacity-60 hover:opacity-100 transition-opacity duration-500">
      <div className="text-[10px] font-mono text-zinc-500 mb-2 uppercase border-b border-zinc-800 pb-1">
        Projected Intensity Levels (Weekly)
      </div>
      <ResponsiveContainer width="100%" height="100%">
        <AreaChart data={data}>
          <defs>
            <linearGradient id="colorIntensity" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#ccff00" stopOpacity={0.3}/>
              <stop offset="95%" stopColor="#ccff00" stopOpacity={0}/>
            </linearGradient>
          </defs>
          <XAxis 
            dataKey="day" 
            tick={{fill: '#52525b', fontSize: 10, fontFamily: 'monospace'}} 
            axisLine={false}
            tickLine={false}
          />
          <Tooltip 
            contentStyle={{ backgroundColor: '#09090b', border: '1px solid #ccff00', color: '#ccff00' }}
            itemStyle={{ color: '#ccff00', fontFamily: 'monospace', fontSize: '12px' }}
            cursor={{ stroke: '#ccff00', strokeWidth: 1, strokeDasharray: '4 4' }}
          />
          <Area 
            type="monotone" 
            dataKey="intensity" 
            stroke="#ccff00" 
            fillOpacity={1} 
            fill="url(#colorIntensity)" 
          />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
};

export default VibeChart;