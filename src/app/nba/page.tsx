import type { Metadata } from "next";
import { BoardView } from "@/components/BoardView";
import { PageTitle } from "@/components/ui";
import { defaultBoardDay } from "@/lib/data";

export const metadata: Metadata = { title: "NBA board" };

export default function BoardPage() {
  const day = defaultBoardDay();
  if (!day)
    return (
      <PageTitle eyebrow="NBA board" title="No slate yet">
        The pipeline has not produced projections yet.
      </PageTitle>
    );
  return <BoardView day={day} />;
}
