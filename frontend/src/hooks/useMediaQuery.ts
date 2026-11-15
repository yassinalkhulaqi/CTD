/**
 * Subscribe to a CSS media query from a component.
 */

import { useEffect, useState } from "react";

/**
 * Track whether a media query currently matches.
 *
 * @param query - The media query to observe.
 * @returns `true` while the query matches.
 */
export function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(() =>
    typeof window === "undefined" ? false : window.matchMedia(query).matches,
  );

  useEffect(() => {
    const media = window.matchMedia(query);
    setMatches(media.matches);
    function onChange(event: MediaQueryListEvent) {
      setMatches(event.matches);
    }
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, [query]);

  return matches;
}
