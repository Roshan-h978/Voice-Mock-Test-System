// Small animation helpers for the landing page. Both respect "reduce motion" in the device settings.

import { useEffect, useState } from 'react';

function prefersReducedMotion() {
  return typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
}

/**
 * Counts from 0 to 1 over `duration` ms after `delay` ms (eased), for numbers that count up.
 * Returns 1 straight away when the person prefers less motion.
 */
export function useCountUp({ duration = 1200, delay = 0 } = {}) {
  const [progress, setProgress] = useState(() => (prefersReducedMotion() ? 1 : 0));

  useEffect(() => {
    if (prefersReducedMotion()) return undefined;
    let frame;
    let start;
    const tick = (now) => {
      start ??= now;
      const t = Math.min(1, (now - start) / duration);
      setProgress(1 - (1 - t) ** 3); // ease out
      if (t < 1) frame = requestAnimationFrame(tick);
    };
    const timer = setTimeout(() => {
      frame = requestAnimationFrame(tick);
    }, delay);
    return () => {
      clearTimeout(timer);
      cancelAnimationFrame(frame);
    };
  }, [duration, delay]);

  return progress;
}

/**
 * Adds "is-visible" to every `.vmt-reveal` element on the page once it scrolls into view,
 * so CSS can bring it in. Everything shows at once without IntersectionObserver or with reduced motion.
 */
export function useRevealOnScroll() {
  useEffect(() => {
    const items = Array.from(document.querySelectorAll('.vmt-reveal'));
    if (!('IntersectionObserver' in window) || prefersReducedMotion()) {
      items.forEach((item) => item.classList.add('is-visible'));
      return undefined;
    }
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) {
            entry.target.classList.add('is-visible');
            observer.unobserve(entry.target);
          }
        });
      },
      { rootMargin: '0px 0px -8% 0px', threshold: 0.12 },
    );
    items.forEach((item) => observer.observe(item));
    return () => observer.disconnect();
  }, []);
}
