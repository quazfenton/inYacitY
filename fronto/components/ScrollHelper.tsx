import React, { useEffect } from 'react';

/**
 * ScrollHelper provides automatic edge-triggered scrolling
 * When user moves mouse to top/bottom of screen, page slowly scrolls
 */
const ScrollHelper: React.FC = () => {
  useEffect(() => {
    let animationFrameId: number;
    let scrollVelocity = 0;

    const handleMouseMove = (e: MouseEvent) => {
      const edgeZone = 100; // pixels from edge to trigger scroll
      const maxVelocity = 5; // max pixels to scroll per frame
      const screenHeight = window.innerHeight;

      // Detect if mouse is near top or bottom
      if (e.clientY < edgeZone) {
        // Near top: scroll up
        scrollVelocity = -maxVelocity * ((edgeZone - e.clientY) / edgeZone);
      } else if (e.clientY > screenHeight - edgeZone) {
        // Near bottom: scroll down
        scrollVelocity = maxVelocity * ((e.clientY - (screenHeight - edgeZone)) / edgeZone);
      } else {
        // Not near edge: no scroll
        scrollVelocity = 0;
      }
    };

    const scroll = () => {
      if (scrollVelocity !== 0) {
        window.scrollBy(0, scrollVelocity);
      }
      animationFrameId = requestAnimationFrame(scroll);
    };

    document.addEventListener('mousemove', handleMouseMove);
    animationFrameId = requestAnimationFrame(scroll);

    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return null; // This component doesn't render anything
};

export default ScrollHelper;
