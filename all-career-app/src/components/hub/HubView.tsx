import React, { useEffect, useRef } from 'react';
import { GlobalLogoPill } from '../common/GlobalLogoPill';
import { HubHero } from './HubHero';
import { HubCategoryGrid } from './HubCategoryGrid';

interface HubViewProps {
  onNavigate: (view: 'career_explorer' | 'big_company_jobs' | 'all_jobs' | 'practice') => void;
}

export const HubView: React.FC<HubViewProps> = ({ onNavigate }) => {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    // Add scroll-motion class on mount if window width >= 640
    if (window.innerWidth >= 640) {
      document.documentElement.classList.add('scroll-motion');
    }

    const gsap = (window as any).gsap;
    const ScrollTrigger = (window as any).ScrollTrigger;

    if (!gsap || !ScrollTrigger) return;
    gsap.registerPlugin(ScrollTrigger);

    const stage = document.querySelector('.career-stage');
    const hero = document.querySelector('.hero-panel');
    const grid = document.querySelector('.grid-panel') as HTMLElement;
    const cards = Array.from(document.querySelectorAll('.grid-panel .menu-card')) as HTMLElement[];

    let handleHeroClick: (() => void) | null = null;
    let heroEl: HTMLElement | null = null;

    if (!stage || !hero || !grid || !cards.length) {
      return () => {
        document.documentElement.classList.remove('scroll-motion');
      };
    }

    if (window.innerWidth < 640) {
      document.documentElement.classList.remove('scroll-motion');
      gsap.set(cards, { opacity: 0, y: 28, scale: 0.96 });
      ScrollTrigger.batch(cards, {
        start: 'top 88%',
        once: true,
        onEnter: (batch: any) =>
          gsap.to(batch, {
            opacity: 1,
            y: 0,
            scale: 1,
            duration: 0.45,
            stagger: 0.1,
            ease: 'power2.out',
            overwrite: true
          })
      });
      return () => {
        document.documentElement.classList.remove('scroll-motion');
        ScrollTrigger.getAll().forEach((st: any) => st.kill());
      };
    }

    // Desktop staggered layout
    const cardStates = cards.map((card, index) => ({
      card,
      rotation: index % 2 === 0 ? -4 : 4
    }));

    gsap.set(cardStates.map(item => item.card), { opacity: 0, y: 40, scale: 0.85 });
    cardStates.forEach(item => gsap.set(item.card, { rotation: item.rotation }));

    const syncLayerInteractivity = () => {
      const gridOpacity = Number.parseFloat(getComputedStyle(grid).opacity) || 0;
      const gridIsInteractive = gridOpacity >= 0.5;
      grid.style.pointerEvents = gridIsInteractive ? 'auto' : 'none';
      (hero as HTMLElement).style.pointerEvents = gridIsInteractive ? 'none' : 'auto';
    };

    syncLayerInteractivity();

    const TARGET_SCROLL = 270; // Reduced from 900 by 70% (requires only 30% scroll effort)

    const timeline = gsap.timeline({
      scrollTrigger: {
        trigger: stage,
        start: 'top top',
        end: `+=${TARGET_SCROLL}`,
        pin: true,
        scrub: true,
        anticipatePin: 1,
        invalidateOnRefresh: true,
        onUpdate: syncLayerInteractivity
      }
    });

    timeline.to(hero, { opacity: 0, scale: 0.85, y: -40, duration: 0.45, ease: 'none' }, 0);
    timeline.to(grid, { opacity: 1, duration: 0.7, ease: 'none' }, 0.2);
    timeline.fromTo(
      '.glass-orb',
      { scale: 0.8, x: 60, opacity: 0.2 },
      { scale: 1.15, x: -30, opacity: 1, duration: 0.8, ease: 'none' },
      0.1
    );
    cardStates.forEach((item, index) =>
      timeline.to(
        item.card,
        { opacity: 1, scale: 1, y: 0, rotation: 0, duration: 0.4, ease: 'none' },
        0.2 + index * 0.1
      )
    );
    timeline.set(grid, { pointerEvents: 'auto' }, 0.85);
    timeline.call(syncLayerInteractivity, [], 0.85);

    // Hero click to scrub smoothly down
    handleHeroClick = () => {
      const obj = { y: window.scrollY };
      gsap.to(obj, {
        y: TARGET_SCROLL,
        duration: 1.35,
        ease: 'power3.inOut',
        onUpdate: () => window.scrollTo(0, obj.y)
      });
    };

    (hero as HTMLElement).addEventListener('click', handleHeroClick);

    // 4-Second Auto-Scroll:
    // First time opening or on refresh, smoothly scrolls down after 4 seconds.
    // If the user scrolls manually or scrolls back to top, it will NOT auto-scroll again.
    let userInteracted = false;
    let hasAutoScrolled = false;

    const onUserInteraction = () => {
      userInteracted = true;
    };

    window.addEventListener('wheel', onUserInteraction, { passive: true, once: true });
    window.addEventListener('touchmove', onUserInteraction, { passive: true, once: true });
    window.addEventListener('keydown', onUserInteraction, { passive: true, once: true });

    const autoScrollTimer = setTimeout(() => {
      if (!userInteracted && !hasAutoScrolled && window.scrollY < 20) {
        hasAutoScrolled = true;
        const obj = { y: window.scrollY };
        gsap.to(obj, {
          y: TARGET_SCROLL,
          duration: 1.35,
          ease: 'power3.inOut',
          onUpdate: () => window.scrollTo(0, obj.y)
        });
      }
    }, 4000);

    return () => {
      clearTimeout(autoScrollTimer);
      window.removeEventListener('wheel', onUserInteraction);
      window.removeEventListener('touchmove', onUserInteraction);
      window.removeEventListener('keydown', onUserInteraction);
      document.documentElement.classList.remove('scroll-motion');
      (hero as HTMLElement).removeEventListener('click', handleHeroClick);
      ScrollTrigger.getAll().forEach((st: any) => st.kill());
    };
  }, []);

  const scrollToCategories = () => {
    const TARGET_SCROLL = 270;
    const gsap = (window as any).gsap;
    if (gsap) {
      const obj = { y: window.scrollY };
      gsap.to(obj, {
        y: TARGET_SCROLL,
        duration: 1.35,
        ease: 'power3.inOut',
        onUpdate: () => window.scrollTo(0, obj.y)
      });
    } else {
      window.scrollTo({ top: TARGET_SCROLL, behavior: 'smooth' });
    }
  };

  return (
    <div className="hub-container" ref={containerRef}>
      {/* Hidden SVG Gradient Definitions for authentic category icon fills */}
      <svg width="0" height="0" style={{ position: 'absolute' }}>
        <defs>
          <linearGradient id="grad-blue" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#3b82f6', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#a855f7', stopOpacity: 1 }} />
          </linearGradient>
          <linearGradient id="grad-green" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#10b981', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#06b6d4', stopOpacity: 1 }} />
          </linearGradient>
          <linearGradient id="grad-orange" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#f59e0b', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#f43f5e', stopOpacity: 1 }} />
          </linearGradient>
          <linearGradient id="grad-cyan" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style={{ stopColor: '#06b6d4', stopOpacity: 1 }} />
            <stop offset="100%" style={{ stopColor: '#8b5cf6', stopOpacity: 1 }} />
          </linearGradient>
        </defs>
      </svg>

      {/* Top-left Global Logo Pill */}
      <GlobalLogoPill onGoHome={() => window.scrollTo({ top: 0, behavior: 'smooth' })} />

      <main className="career-stage">
        {/* Screenshot 1: Hero Section */}
        <HubHero onScrollDown={scrollToCategories} />

        {/* Screenshot 2: Category Grid with Green Glass Orb */}
        <HubCategoryGrid onNavigate={onNavigate} />
      </main>
    </div>
  );
};
