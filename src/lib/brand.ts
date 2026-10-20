import brandJson from "../../config/brand.json";
import siteJson from "../../config/site.json";

/** Rename the site here (config/brand.json). Python reads the same file. */
export const BRAND = {
  name: brandJson.name,
  tagline: brandJson.tagline,
  url: brandJson.url,
} as const;

/** Compliance switch: when false, odds tables show consensus/best price without naming books. */
export const SHOW_BOOK_NAMES: boolean = siteJson.showBookNames;

export const SEASON: string = siteJson.season;

export const DISCLAIMER =
  "Information and entertainment only. Not betting advice. Past results don't predict future ones. If gambling is a problem for you or someone you know, call the National Problem Gambling Helpline (verify the current number at ncpg.org.sg).";
