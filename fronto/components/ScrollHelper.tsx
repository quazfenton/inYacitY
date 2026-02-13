import React, { useEffect } from 'react';

/**
 * ScrollHelper provides automatic edge-triggered scrolling
 * When user moves mouse to top/bottom 10% of screen, page slowly scrolls after a delay
 */
const ScrollHelper: React.FC = () => {
  useEffect(() => {
    let animationFrameId: number;
    let scrollVelocity = 0;
    let currentZone: 'none' | 'top' | 'bottom' = 'none';
    let activationTimeout: number | undefined;

    const ZONE_RATIO = 0.1; // top/bottom 10%
    const MAX_VELOCITY = 2; // slower scroll speed
    const ACTIVATION_DELAY = 250; // wait 250ms before scrolling

    const handleMouseMove = (e: MouseEvent) => {
      const screenHeight = window.innerHeight;
      const topThreshold = screenHeight * ZONE_RATIO;
      const bottomThreshold = screenHeight * (1 - ZONE_RATIO);

      let newZone: 'none' | 'top' | 'bottom' = 'none';
      if (e.clientY < topThreshold) {
        newZone = 'top';
      } else if (e.clientY > bottomThreshold) {
        newZone = 'bottom';
      }

      if (newZone !== currentZone) {
        currentZone = newZone;
        scrollVelocity = 0;

        if (activationTimeout) {
          window.clearTimeout(activationTimeout);
          activationTimeout = undefined;
        }

        if (currentZone !== 'none') {
          activationTimeout = window.setTimeout(() => {
            scrollVelocity = currentZone === 'top' ? -MAX_VELOCITY : MAX_VELOCITY;
          }, ACTIVATION_DELAY);
        }
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
      if (activationTimeout) {
        window.clearTimeout(activationTimeout);
      }
      cancelAnimationFrame(animationFrameId);
    };
  }, []);

  return null; // This component doesn't render anything
};

export default ScrollHelper;
