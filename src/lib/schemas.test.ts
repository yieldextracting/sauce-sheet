import { describe, expect, it } from "vitest";
import { American, CardFrontmatter, GameId, UtcIso } from "./schemas";

describe("schemas", () => {
  it("rejects non-UTC timestamps", () => {
    expect(UtcIso.safeParse("2026-10-20T19:00:00Z").success).toBe(true);
    expect(UtcIso.safeParse("2026-10-20T15:00:00-04:00").success).toBe(false);
    expect(UtcIso.safeParse("2026-10-20T19:00:00").success).toBe(false);
  });

  it("validates game ids and American odds", () => {
    expect(GameId.safeParse("20261020-BOS-DET").success).toBe(true);
    expect(GameId.safeParse("2026-10-20-BOS-DET").success).toBe(false);
    expect(American.safeParse(-110).success).toBe(true);
    expect(American.safeParse(-50).success).toBe(false);
  });

  it("validates card frontmatter", () => {
    const ok = CardFrontmatter.safeParse({
      date: "2026-10-21",
      picks: [{ id: 1, game: "20261021-BOS-DET", market: "spread", side: "BOS", line: -1.5, odds: -110, units: 1, confidence: 3 }],
    });
    expect(ok.success).toBe(true);
    if (ok.success) expect(ok.data.picks[0].id).toBe("1");

    const yamlDate = CardFrontmatter.safeParse({ date: new Date("2026-10-21T00:00:00Z"), picks: [] });
    expect(yamlDate.success && yamlDate.data.date).toBe("2026-10-21");

    const noLine = CardFrontmatter.safeParse({
      date: "2026-10-21",
      picks: [{ id: 1, game: "20261021-BOS-DET", market: "total", side: "over", odds: -110, units: 1, confidence: 3 }],
    });
    expect(noLine.success).toBe(false);

    const badSide = CardFrontmatter.safeParse({
      date: "2026-10-21",
      picks: [{ id: 1, game: "20261021-BOS-DET", market: "total", side: "BOS", line: 220, odds: -110, units: 1, confidence: 3 }],
    });
    expect(badSide.success).toBe(false);
  });
});
