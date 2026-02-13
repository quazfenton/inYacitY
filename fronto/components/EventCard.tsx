import React from 'react';
import { Event } from '../types';
import { MapPin, Clock, Tag, ExternalLink } from 'lucide-react';
import EventActionBar from './EventActionBar';

interface EventCardProps {
  event: Event;
  onSelect?: (event: Event, initialTab: "details" | "rsvp" | "comments") => void;
}

const EventCard: React.FC<EventCardProps> = ({ event, onSelect }) => {

  const handleRSVP = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect?.(event, 'rsvp');
  };

  const handleShowComments = (e: React.MouseEvent) => {
    e.stopPropagation();
    onSelect?.(event, 'comments');
  };

  const handleCardClick = () => {
    onSelect?.(event, 'details');
  };

  return (
    <>
      <div 
        onClick={handleCardClick}
        className="group relative w-full bg-concrete/10 border border-zinc-800 hover:border-acid transition-all duration-500 overflow-hidden min-h-[400px] flex flex-col justify-between p-6 cursor-pointer"
      >
        {/* Background Image with Hover Effect */}
        <div className="absolute inset-0 z-0">
          <img 
            src={event.imageUrl} 
            alt={event.title} 
            className="w-full h-full object-cover opacity-20 group-hover:opacity-40 transition-opacity duration-700 scale-100 group-hover:scale-110 grayscale group-hover:grayscale-0"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-void via-void/80 to-transparent"></div>
        </div>

        <div className="relative z-10 flex justify-between items-start">
           <div className="bg-acid text-void font-bold font-mono text-xs px-2 py-1">
              {event.price.toUpperCase()}
           </div>
           {event.isAiGenerated && (
               <div className="border border-acid/50 text-acid/80 font-mono text-[10px] px-2 py-1 animate-pulse">
                  LIVE_INTEL_FETCH
               </div>
           )}
        </div>

        <div className="relative z-10 mt-auto space-y-4">
          <div className="space-y-1">
            <h3 className="text-3xl md:text-4xl font-black text-zinc-100 tracking-tighter uppercase leading-none group-hover:text-acid transition-colors duration-300">
              {event.title}
            </h3>
            <div className="flex items-center gap-2 text-zinc-400 font-mono text-xs">
              <Clock size={12} />
              <span>{event.date} // {event.time}</span>
            </div>
            <div className="flex items-center gap-2 text-zinc-400 font-mono text-xs">
               <MapPin size={12} />
               <span>{event.location}</span>
            </div>
          </div>

          <p className="text-zinc-300 text-sm font-light border-l-2 border-zinc-700 pl-3 group-hover:border-acid transition-colors duration-500">
            {event.description}
          </p>

          <div className="flex flex-wrap items-center justify-between gap-2 pt-2">
            <div className="flex flex-wrap gap-2">
              {event.tags.map((tag) => (
                <span key={tag} className="flex items-center text-[10px] uppercase tracking-wider text-zinc-500 font-mono border border-zinc-800 px-2 py-0.5 rounded-full">
                  #{tag}
                </span>
              ))}
            </div>
            {event.link && (
              <a 
                href={event.link}
                target="_blank"
                rel="noopener noreferrer"
                onClick={(e) => e.stopPropagation()}
                className="flex items-center gap-1 text-acid hover:text-white text-xs font-mono transition-colors"
              >
                <ExternalLink size={12} />
                VIEW
              </a>
            )}
          </div>

          {/* Action Bar */}
          <EventActionBar
            event={event}
            onRSVP={handleRSVP}
            onShowComments={handleShowComments}
            rsvpCount={0}
            commentCount={0}
            hasRSVP={false}
          />
        </div>
      </div>

    </>
  );
};

export default EventCard;