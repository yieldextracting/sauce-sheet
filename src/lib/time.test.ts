import { describe, expect, it } from "vitest";
import { addDays, etDate, formatDayLong, formatTip, formatUpdated } from "./time";

describe("ET game day", () => {
  it("keeps a late West Coast game on its tip date", () => {
    expect(etDate("2026-10-21T02:30:00Z")).toBe("2026-10-20"); // 10:30 PM EDT
    expect(etDate("2026-10-21T03:59:00Z")).toBe("2026-10-20");
    expect(etDate("2026-10-21T04:00:00Z")).toBe("2026-10-21"); // midnight EDT
  });

  it("uses the EST offset after the Nov 1 change", () => {
    expect(etDate("2026-12-02T04:59:00Z")).toBe("2026-12-01");
    expect(etDate("2026-12-02T05:00:00Z")).toBe("2026-12-02");
  });

  it("maps both 1:30 AMs on fall-back day to Nov 1", () => {
    expect(etDate("2026-11-01T05:30:00Z")).toBe("2026-11-01");
    expect(etDate("2026-11-01T06:30:00Z")).toBe("2026-11-01");
  });

  it("puts the Halloween late game on Oct 31 even though it ends after the change", () => {
    expect(etDate("2026-11-01T02:30:00Z")).toBe("2026-10-31");
  });

  it("handles spring forward", () => {
    expect(etDate("2027-03-14T06:59:00Z")).toBe("2027-03-14");
    expect(formatTip("2027-03-14T07:00:00Z")).toBe("3:00 AM ET");
  });
});

describe("formatting", () => {
  it("formats tips in ET across DST", () => {
    expect(formatTip("2026-10-20T23:30:00Z")).toBe("7:30 PM ET"); // EDT
    expect(formatTip("2026-11-03T00:30:00Z")).toBe("7:30 PM ET"); // EST
  });

  it("formats the updated stamp", () => {
    expect(formatUpdated("2026-10-21T00:39:00Z")).toBe("UPDATED TUE 8:39 PM ET");
  });

  it("formats ET calendar days without shifting them", () => {
    expect(formatDayLong("2026-10-20")).toBe("Tuesday, October 20");
    expect(addDays("2026-10-31", 1)).toBe("2026-11-01");
    expect(addDays("2027-03-13", 2)).toBe("2027-03-15");
  });
});
