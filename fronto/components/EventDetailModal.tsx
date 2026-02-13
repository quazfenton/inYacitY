import React, { useState, useEffect } from 'react';
import { Event } from '../types';
import { X, Calendar, MessageCircle, Send, User, Clock, MapPin, ExternalLink } from 'lucide-react';
import { useEventRSVP } from '../src/hooks/useEventRSVP';
import { useEventComments } from '../src/hooks/useEventComments';

interface EventDetailModalProps {
  event: Event;
  isOpen: boolean;
  initialTab?: 'details' | 'rsvp' | 'comments';
  onClose: () => void;
}

const EventDetailModal: React.FC<EventDetailModalProps> = ({ event, isOpen, initialTab = 'details', onClose }) => {
  const [activeTab, setActiveTab] = useState<'details' | 'rsvp' | 'comments'>(initialTab);
  const [rsvpName, setRsvpName] = useState('');
  const [rsvpEmail, setRsvpEmail] = useState('');
  const [calendarType, setCalendarType] = useState<'google' | 'apple' | null>(null);
  const [enableReminder, setEnableReminder] = useState(false);
  const [commentAuthor, setCommentAuthor] = useState('');
  const [commentText, setCommentText] = useState('');

  const {
    rsvpEvent,
    cancelRSVP,
    getRSVPStatus,
    rsvpData,
    isLoading: rsvpLoading,
    error: rsvpError
  } = useEventRSVP();

  const {
    comments,
    fetchComments,
    postComment,
    likeComment,
    isLoading: commentsLoading,
    error: commentsError,
    rateLimitStatus
  } = useEventComments();

  // Fetch comments when modal opens and tab is comments
  useEffect(() => {
    if (isOpen && activeTab === 'comments') {
      fetchComments(event.id, 50);
    }
  }, [isOpen, activeTab, event.id, fetchComments]);

  // Prevent body scroll when modal is open
  useEffect(() => {
    if (isOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.body.style.overflow = '';
    };
  }, [isOpen]);

  if (!isOpen) return null;

  const handleRSVP = async (e: React.FormEvent) => {
    e.preventDefault();
    await rsvpEvent(
      {
        event_id: event.id,
        title: event.title,
        date: event.date,
        time: event.time,
        location: event.location,
        description: event.description
      },
      {
        user_name: rsvpName,
        user_email: rsvpEmail,
        calendar_type: calendarType,
        reminder_enabled: enableReminder,
        reminder_minutes: 120
      }
    );
  };

  const handlePostComment = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!commentAuthor.trim() || !commentText.trim()) return;

    const result = await postComment(event.id, commentAuthor, commentText);
    if (result && !result.error) {
      setCommentText('');
      // Refresh comments after posting
      await fetchComments(event.id, 50);
    }
  };

  return (
    <div className="fixed inset-0 z-[999] bg-void/95 backdrop-blur-lg flex items-center justify-center p-4">
      <div className="w-full max-w-2xl max-h-[calc(100vh-8rem)] bg-black border border-zinc-800 overflow-hidden flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b border-zinc-800">
          <h2 className="text-2xl font-black tracking-tighter uppercase truncate pr-4">
            {event.title}
          </h2>
          <button
            onClick={onClose}
            className="text-zinc-500 hover:text-acid transition-colors"
          >
            <X size={24} />
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-zinc-800">
          <button
            onClick={() => setActiveTab('details')}
            className={`flex-1 py-3 text-xs font-mono transition-colors ${
              activeTab === 'details'
                ? 'bg-acid text-void'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            DETAILS
          </button>
          <button
            onClick={() => setActiveTab('rsvp')}
            className={`flex-1 py-3 text-xs font-mono transition-colors ${
              activeTab === 'rsvp'
                ? 'bg-acid text-void'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            RSVP
          </button>
          <button
            onClick={() => setActiveTab('comments')}
            className={`flex-1 py-3 text-xs font-mono transition-colors ${
              activeTab === 'comments'
                ? 'bg-acid text-void'
                : 'text-zinc-400 hover:text-white'
            }`}
          >
            COMMENTS ({comments.length})
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {/* Details Tab */}
          {activeTab === 'details' && (
            <div className="space-y-6">
              <div className="aspect-video bg-zinc-900 overflow-hidden relative group">
                <img
                  src={event.imageUrl || `https://picsum.photos/800/400?random=${event.id}`}
                  alt={event.title}
                  className="w-full h-full object-cover brightness-[0.4]"
                />
                {/* Dark gradient overlay */}
                <div className="absolute inset-0 bg-gradient-to-t from-black via-black/60 to-black/30"></div>
                
                {/* External link button */}
                {event.link && (
                  <a
                    href={event.link}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="absolute top-3 right-3 w-10 h-10 bg-black/60 hover:bg-acid border border-zinc-700 hover:border-acid flex items-center justify-center transition-all duration-300 group/link"
                    title="View on original site"
                  >
                    <ExternalLink size={16} className="text-zinc-400 group-hover/link:text-void transition-colors" />
                  </a>
                )}
              </div>

              <div className="space-y-3">
                <div className="flex items-center gap-2 text-zinc-400 font-mono text-sm">
                  <Clock size={16} className="text-acid" />
                  <span>{event.date} at {event.time}</span>
                </div>
                <div className="flex items-center gap-2 text-zinc-400 font-mono text-sm">
                  <MapPin size={16} className="text-acid" />
                  <a
                    href={`https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(event.location)}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-zinc-400 hover:underline"
                  >
                    {event.location}
                  </a>
                </div>
              </div>

              <p className="text-zinc-300 leading-relaxed">
                {event.description}
              </p>

              <div className="flex flex-wrap gap-2">
                {event.tags?.map((tag) => (
                  <span
                    key={tag}
                    className="text-[10px] uppercase tracking-wider text-zinc-500 font-mono border border-zinc-800 px-2 py-1"
                  >
                    #{tag}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* RSVP Tab */}
          {activeTab === 'rsvp' && (
            <div className="space-y-6">
              {rsvpData ? (
                <div className="text-center py-8 space-y-4">
                  <div className="text-acid text-lg font-mono">RSVP CONFIRMED!</div>
                  <p className="text-zinc-400 text-sm">
                    You're going to {event.title}
                  </p>
                  {rsvpData.calendar_url && (
                    <a
                      href={rsvpData.calendar_url}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-2 text-acid hover:text-white text-xs font-mono transition-colors"
                    >
                      <Calendar size={14} />
                      ADD TO CALENDAR
                    </a>
                  )}
                </div>
              ) : (
                <form onSubmit={handleRSVP} className="space-y-4">
                  <div>
                    <label className="block text-xs font-mono text-zinc-500 mb-2">
                      YOUR NAME *
                    </label>
                    <input
                      type="text"
                      value={rsvpName}
                      onChange={(e) => setRsvpName(e.target.value)}
                      required
                      className="w-full bg-zinc-900 border border-zinc-800 px-4 py-3 text-white font-mono text-sm focus:border-acid focus:outline-none transition-colors"
                      placeholder="Enter your name"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-zinc-500 mb-2">
                      EMAIL (optional)
                    </label>
                    <input
                      type="email"
                      value={rsvpEmail}
                      onChange={(e) => setRsvpEmail(e.target.value)}
                      className="w-full bg-zinc-900 border border-zinc-800 px-4 py-3 text-white font-mono text-sm focus:border-acid focus:outline-none transition-colors"
                      placeholder="Enter your email"
                    />
                  </div>

                  <div>
                    <label className="block text-xs font-mono text-zinc-500 mb-2">
                      ADD TO CALENDAR
                    </label>
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setCalendarType(calendarType === 'google' ? null : 'google')}
                        className={`flex-1 py-2 text-xs font-mono border transition-colors ${
                          calendarType === 'google'
                            ? 'border-acid text-acid'
                            : 'border-zinc-800 text-zinc-400 hover:border-zinc-600'
                        }`}
                      >
                        GOOGLE
                      </button>
                      <button
                        type="button"
                        onClick={() => setCalendarType(calendarType === 'apple' ? null : 'apple')}
                        className={`flex-1 py-2 text-xs font-mono border transition-colors ${
                          calendarType === 'apple'
                            ? 'border-acid text-acid'
                            : 'border-zinc-800 text-zinc-400 hover:border-zinc-600'
                        }`}
                      >
                        APPLE
                      </button>
                    </div>
                  </div>

                  <label className="flex items-center gap-2 text-xs font-mono text-zinc-400 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={enableReminder}
                      onChange={(e) => setEnableReminder(e.target.checked)}
                      className="accent-acid"
                    />
                    Enable 2-hour reminder
                  </label>

                  {rsvpError && (
                    <div className="text-red-500 text-xs font-mono">{rsvpError}</div>
                  )}

                  <button
                    type="submit"
                    disabled={rsvpLoading || !rsvpName.trim()}
                    className="w-full py-4 bg-acid text-void font-mono text-sm font-bold hover:bg-acid/90 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {rsvpLoading ? 'CONFIRMING...' : 'CONFIRM RSVP'}
                  </button>
                </form>
              )}
            </div>
          )}

          {/* Comments Tab */}
          {activeTab === 'comments' && (
            <div className="space-y-6">
              {/* Rate Limit Warning */}
              {rateLimitStatus?.is_limited && (
                <div className="bg-red-900/20 border border-red-900/50 p-3 text-red-400 text-xs font-mono">
                  Rate limit reached. Please wait {Math.ceil(rateLimitStatus.remaining_minutes)} minutes.
                </div>
              )}

              {/* Comment Form */}
              <form onSubmit={handlePostComment} className="space-y-3">
                <input
                  type="text"
                  value={commentAuthor}
                  onChange={(e) => setCommentAuthor(e.target.value)}
                  placeholder="Your name"
                  className="w-full bg-zinc-900 border border-zinc-800 px-3 py-2 text-white font-mono text-sm focus:border-acid focus:outline-none transition-colors"
                />
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={commentText}
                    onChange={(e) => setCommentText(e.target.value)}
                    placeholder="Add a comment..."
                    disabled={rateLimitStatus?.is_limited}
                    className="flex-1 bg-zinc-900 border border-zinc-800 px-3 py-2 text-white font-mono text-sm focus:border-acid focus:outline-none transition-colors disabled:opacity-50"
                  />
                  <button
                    type="submit"
                    disabled={!commentAuthor.trim() || !commentText.trim() || commentsLoading || rateLimitStatus?.is_limited}
                    className="px-4 py-2 bg-zinc-800 text-white font-mono text-xs hover:bg-acid hover:text-void transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    <Send size={14} />
                  </button>
                </div>
              </form>

              {/* Comments List */}
              <div className="space-y-4">
                {commentsLoading ? (
                  <div className="text-center py-8 text-zinc-500 font-mono text-xs">
                    LOADING COMMENTS...
                  </div>
                ) : comments.length === 0 ? (
                  <div className="text-center py-8 text-zinc-600 font-mono text-xs">
                    NO COMMENTS YET. BE THE FIRST!
                  </div>
                ) : (
                  comments.map((comment) => (
                    <div
                      key={comment.comment_id}
                      className="bg-zinc-900/50 border border-zinc-800 p-4 space-y-2"
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-2 text-zinc-400">
                          <User size={14} />
                          <span className="text-xs font-mono">{comment.author_name}</span>
                        </div>
                        <span className="text-[10px] font-mono text-zinc-600">
                          {new Date(comment.created_at).toLocaleDateString()}
                        </span>
                      </div>
                      <p className="text-zinc-300 text-sm">{comment.text}</p>
                      <button
                        onClick={() => likeComment(comment.comment_id)}
                        className="flex items-center gap-1 text-[10px] font-mono text-zinc-500 hover:text-acid transition-colors"
                      >
                        <MessageCircle size={12} />
                        {comment.likes} LIKES
                      </button>
                    </div>
                  ))
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default EventDetailModal;
