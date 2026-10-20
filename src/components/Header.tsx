import Link from "next/link";
import { BRAND } from "@/lib/brand";
import { ThemeToggle } from "./ThemeToggle";

const NAV = [
  { href: "/nba", label: "Board" },
  { href: "/nba/record", label: "Record" },
  { href: "/nba/card", label: "My Card" },
];

export function Header() {
  return (
    <header className="border-b border-rule">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 h-14 flex items-center justify-between gap-4">
        <Link href="/" className="font-serif text-base sm:text-lg font-semibold tracking-tight whitespace-nowrap">
          {BRAND.name.toUpperCase()}
        </Link>
        <nav aria-label="Main" className="flex items-center gap-3 sm:gap-6 text-sm whitespace-nowrap">
          {NAV.map((n) => (
            <Link key={n.href} href={n.href} className="text-muted hover:text-ink">
              {n.label}
            </Link>
          ))}
          <ThemeToggle />
        </nav>
      </div>
    </header>
  );
}
