import Link from "next/link";
import { PageTitle } from "@/components/ui";

export default function NotFound() {
  return (
    <PageTitle eyebrow="404" title="Nothing here">
      That page doesn&apos;t exist. <Link href="/nba" className="underline text-accent">Back to the board</Link>.
    </PageTitle>
  );
}
