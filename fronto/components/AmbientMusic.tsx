import React, { useEffect, useRef, useState } from 'react';
import { Volume2, VolumeX } from 'lucide-react';

const AmbientMusic: React.FC = () => {
  const audioRef = useRef<HTMLAudioElement>(null);
  const [isMuted, setIsMuted] = useState(false);

  useEffect(() => {
    // Auto-start playing ambient music with low volume
    if (audioRef.current) {
      audioRef.current.volume = 0.15; // 15% volume
      audioRef.current.play().catch(() => {
        // Playback prevented by browser, will retry on user interaction
      });
    }

    // Resume on user interaction if blocked by browser
    const handleUserInteraction = () => {
      if (audioRef.current && audioRef.current.paused) {
        audioRef.current.play().catch(() => {});
      }
    };

    document.addEventListener('click', handleUserInteraction);
    document.addEventListener('touchstart', handleUserInteraction);

    return () => {
      document.removeEventListener('click', handleUserInteraction);
      document.removeEventListener('touchstart', handleUserInteraction);
    };
  }, []);

  const toggleMute = () => {
    if (audioRef.current) {
      if (isMuted) {
        audioRef.current.play().catch(() => {});
        setIsMuted(false);
      } else {
        audioRef.current.pause();
        setIsMuted(true);
      }
    }
  };

  return (
    <>
      {/* Hidden audio element */}
      <audio
        ref={audioRef}
        loop
        src="https://cdn.pixabay.com/download/audio/2023/08/09/audio_9c5e0f1abc.mp3?filename=ambient-night-lofi-117355.mp3"
      />

      {/* Mute toggle button */}
      <button
        onClick={toggleMute}
        className="fixed bottom-6 right-6 z-40 p-3 border border-zinc-700 hover:border-acid hover:bg-acid hover:text-void transition-all duration-300 rounded-full flex items-center justify-center"
        title={isMuted ? 'Unmute music' : 'Mute music'}
        aria-label="Toggle ambient music"
      >
        {isMuted ? (
          <VolumeX size={18} />
        ) : (
          <Volume2 size={18} />
        )}
      </button>
    </>
  );
};

export default AmbientMusic;
