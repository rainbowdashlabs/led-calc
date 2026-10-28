// Where the window stands against the Tailwind breakpoints the templates are written in,
// and what kind of pointer the device has.
import { breakpointsTailwind, useBreakpoints, useMediaQuery } from '@vueuse/core'

export function useBreakpoint() {
  const breakpoints = useBreakpoints(breakpointsTailwind)
  return {
    /** Sidebar and content side by side (lg and up); below, the mobile tab bar is used. */
    isDesktop: breakpoints.greaterOrEqual('lg'),
    /** Below sm: short labels. */
    isNarrow: breakpoints.smaller('sm'),
    /** Touch screens: bigger targets, tap instead of hover. */
    isCoarsePointer: useMediaQuery('(pointer: coarse)'),
  }
}
