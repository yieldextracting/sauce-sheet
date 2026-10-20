import Link from "next/link";
import { BRAND, DISCLAIMER } from "@/lib/brand";

export function Footer() {
  return (
    <footer className="border-t border-rule mt-8">
      <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8 text-sm text-muted space-y-3">
        <p className="max-w-3xl leading-relaxed">{DISCLAIMER}</p>
        <p className="max-w-3xl leading-relaxed">
          Every number on this site comes from the {BRAND.name} pipeline or from the author&apos;s dated card. Nothing is
          typed in by hand, and no line is re-priced after it is locked.
        </p>
        <p className="flex flex-wrap gap-x-5 gap-y-1">
          <Link href="/responsible-gambling" className="underline hover:text-ink">
            Responsible gambling
          </Link>
          <Link href="/nba/record" className="underline hover:text-ink">
            Model record
          </Link>
          <Link href="/nba/card" className="underline hover:text-ink">
            My Card record
          </Link>
        </p>
        <p className="eyebrow">{BRAND.name} · {BRAND.tagline}</p>
      </div>
    </footer>
  );
}
