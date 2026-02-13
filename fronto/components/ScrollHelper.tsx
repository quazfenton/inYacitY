import React, { useEffect } from 'react';

/**
 * ScrollHelper provides automatic edge-triggered scrolling
 * When user moves mouse to top/bottom 10% of screen, page slowly scrolls after a delay
 */
const ScrollHelper: React.FC = () => {
  useEffect(() => {
    let animationFrameId: number;
    let scrollVelocity = 0;
    let scrollDelayTimeout: NodeJS.Timeout | null = null;
    let isInScrollZone = false;
    const SCROLL_ZONE_PERCENT = 0.10; // 10% of screen height
    const ACTIVATION_DELAY = 300; // 300ms delay before scrolling
    const MAX_VELOCITY = 3; // slower scroll speed

    const handleMouseMove = (e: MouseEvent) => {
      const screenHeight = window.innerHeight;
      const topZone = screenHeight * SCROLL_ZONE_PERCENT;
      const bottomZone = screenHeight * (1 - SCROLL_ZONE_PERCENT);

      // Clear any pending delay timeout
      if (scrollDelayTimeout) {
        clearTimeout(scrollDelayTimeout);
        scrollDelayTimeout = null;
      }

      // Detect if mouse is in top or bottom zone
      if (e.clientY < topZone) {
        // Near top: scroll up (only after delay)
        if (!isInScrollZone) {
          isInScrollZone = true;
          scrollDelayTimeout = setTimeout(() => {
            scrollVelocity = -MAX_VELOCITY;
          }, ACTIVATION_DELAY);
        }
      } else if (e.clientY > bottomZone) {
        // Near bottom: scroll down (only after delay)
        if (!isInScrollZone) {
          isInScrollZone = true;
          scrollDelayTimeout = setTimeout(() => {
            scrollVelocity = MAX_VELOCITY;
          }, ACTIVATION_DELAY);
        }
      } else {
        // Not near edge: no scroll
        isInScrollZone = false;
        scrollVelocity = 0;
      }
    };

    const scroll = () => {
      if (scrollVelocity !== 0 && isInScrollZone) {
        window.scrollBy(0, scrollVelocity);
      }
      animationFrameId = requestAnimationFrame(scroll);
    };

    document.addEventListener('mousemove', handleMouseMove);
    animationFrameId = requestAnimationFrame(scroll);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      if (scrollDelayTimeout) {
        clearTimeout(scrollDelayTimeout);
      }
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return null; // This component doesn't render anything
};

export default ScrollHelper;
