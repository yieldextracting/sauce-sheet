import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BoardView } from "@/components/BoardView";
import { boardDays } from "@/lib/data";
import { formatDayLong } from "@/lib/time";

export const dynamicParams = false;

export function generateStaticParams() {
  return boardDays().map((date) => ({ date }));
}

export async function generateMetadata({ params }: PageProps<"/nba/[date]">): Promise<Metadata> {
  const { date } = await params;
  return { title: `NBA board, ${formatDayLong(date)}` };
}

export default async function BoardDayPage({ params }: PageProps<"/nba/[date]">) {
  const { date } = await params;
  if (!boardDays().includes(date)) notFound();
  return <BoardView day={date} />;
}
