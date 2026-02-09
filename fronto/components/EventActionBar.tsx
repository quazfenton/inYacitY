import React from 'react';
import { Event } from '../types';
import { Calendar, MessageCircle, Users } from 'lucide-react';

interface EventActionBarProps {
  event: Event;
  onRSVP: (event: Event) => void;
  onShowComments: (event: Event) => void;
  rsvpCount?: number;
  commentCount?: number;
  hasRSVP?: boolean;
}

const EventActionBar: React.FC<EventActionBarProps> = ({
  event,
  onRSVP,
  onShowComments,
  rsvpCount = 0,
  commentCount = 0,
  hasRSVP = false
}) => {
  return (
    <div className="flex items-center gap-3 mt-4 pt-4 border-t border-zinc-800/50">
      {/* RSVP Button */}
      <button
        onClick={() => onRSVP(event)}
        className={`flex items-center gap-2 px-3 py-2 text-xs font-mono transition-all duration-300 ${
          hasRSVP
            ? 'bg-acid text-void'
            : 'border border-zinc-700 text-zinc-400 hover:border-acid hover:text-acid'
        }`}
      >
        <Calendar size={14} />
        <span>{hasRSVP ? 'RSVP\'D' : 'RSVP'}</span>
        {rsvpCount > 0 && (
          <span className="ml-1 text-[10px] opacity-70">({rsvpCount})</span>
        )}
      </button>

      {/* Comments Button */}
      <button
        onClick={() => onShowComments(event)}
        className="flex items-center gap-2 px-3 py-2 text-xs font-mono border border-zinc-700 text-zinc-400 hover:border-acid hover:text-acid transition-all duration-300"
      >
        <MessageCircle size={14} />
        <span>COMMENTS</span>
        {commentCount > 0 && (
          <span className="ml-1 text-[10px] opacity-70">({commentCount})</span>
        )}
      </button>

      {/* Attendees Indicator */}
      {rsvpCount > 0 && (
        <div className="flex items-center gap-1 text-zinc-500 text-[10px] font-mono ml-auto">
          <Users size={12} />
          <span>{rsvpCount} GOING</span>
        </div>
      )}
    </div>
  );
};

export default EventActionBar;
