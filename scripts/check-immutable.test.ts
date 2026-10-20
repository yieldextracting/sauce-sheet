import { describe, expect, it } from "vitest";
import { checkCardChange } from "./check-immutable";

const GAME = "20261021-BOS-DET";
const tip = new Date("2026-10-21T23:00:00Z");
const tipOf = (id: string) => (id === GAME ? tip : null);
const before = new Date("2026-10-21T20:00:00Z");
const after = new Date("2026-10-22T01:00:00Z");

const pick = (over: Record<string, unknown> = {}) => ({
  id: "1", game: GAME, market: "spread" as const, side: "BOS", line: -1.5, odds: -110, units: 1, confidence: 3,
  ...over,
});
const card = (picks: ReturnType<typeof pick>[], amendments: { at: string; pickId: string; note: string }[] = [], body = "") => ({
  date: "2026-10-21", picks, amendments, body,
});

describe("card lock", () => {
  it("allows edits before tip", () => {
    expect(checkCardChange(card([pick()]), card([pick({ line: -2 })]), tipOf, before, "f")).toEqual([]);
  });

  it("rejects edits after tip without an amendment", () => {
    expect(checkCardChange(card([pick()]), card([pick({ line: -2 })]), tipOf, after, "f")).toHaveLength(1);
  });

  it("rejects rationale edits after tip", () => {
    expect(checkCardChange(card([pick({ why: "a" })]), card([pick({ why: "b" })]), tipOf, after, "f")).toHaveLength(1);
  });

  it("accepts edits after tip with a new amendment note", () => {
    const amended = card([pick({ units: 0.5 })], [{ at: "2026-10-22T01:00:00Z", pickId: "1", note: "Logged 1u by mistake, bet was 0.5u" }]);
    expect(checkCardChange(card([pick()]), amended, tipOf, after, "f")).toEqual([]);
  });

  it("rejects adding a pick after tip, even with an amendment", () => {
    expect(checkCardChange(card([]), card([pick()], [{ at: "x", pickId: "1", note: "late" }]), tipOf, after, "f")).toHaveLength(1);
  });

  it("rejects removing a pick after tip", () => {
    expect(checkCardChange(card([pick()]), card([]), tipOf, after, "f")).toHaveLength(1);
  });

  it("rejects picks on unknown games", () => {
    expect(checkCardChange(null, card([pick({ game: "20261021-XXX-YYY" })]), tipOf, before, "f")).toHaveLength(1);
  });

  it("locks the written takes after the first tip", () => {
    const a = card([pick()], [], "old take");
    const b = card([pick()], [], "new take");
    expect(checkCardChange(a, b, tipOf, after, "f", tip)).toHaveLength(1);
    expect(checkCardChange(a, b, tipOf, before, "f", tip)).toEqual([]);
    const amended = card([pick()], [{ at: "x", pickId: "takes", note: "fixed a typo" }], "new take");
    expect(checkCardChange(a, amended, tipOf, after, "f", tip)).toEqual([]);
  });
});
