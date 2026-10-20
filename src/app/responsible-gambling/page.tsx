import type { Metadata } from "next";
import { Note, PageTitle } from "@/components/ui";
import { BRAND } from "@/lib/brand";

export const metadata: Metadata = { title: "Responsible gambling" };

export default function ResponsibleGamblingPage() {
  return (
    <div className="max-w-2xl">
      <PageTitle eyebrow="Please read" title="Responsible gambling" />
      <div className="space-y-4 leading-relaxed">
        <p>
          {BRAND.name} publishes analysis and a public record. It is information and entertainment only. It is not
          betting advice, it does not take bets, and it does not link to, promote, or earn anything from any betting
          operator.
        </p>
        <p>
          Models are wrong often. Past results, including the ones on this site, do not predict future ones. Small
          samples are noise.
        </p>
        <h2 className="font-serif text-xl font-semibold pt-2">If gambling is a problem</h2>
        <p>
          If gambling is causing problems for you or someone you know, call the National Problem Gambling Helpline in
          Singapore. Please check the current number on the National Council on Problem Gambling website at{" "}
          <a href="https://www.ncpg.org.sg" className="underline text-accent" rel="noopener noreferrer">
            ncpg.org.sg
          </a>
          , which also lists self-exclusion and counselling options.
        </p>
        <p>Outside Singapore, use your local problem gambling helpline.</p>
        <Note>
          Warning signs include chasing losses, betting more than you planned, borrowing to bet, or hiding it from people
          close to you.
        </Note>
      </div>
    </div>
  );
}
