import Link from "next/link";
import {
  BarChart3,
  Clock,
  MessageSquare,
  Shield,
  Smile,
  Users,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";

const features = [
  {
    icon: MessageSquare,
    title: "Message statistics",
    description: "Total messages, words, media, and links at a glance.",
  },
  {
    icon: Clock,
    title: "Timelines",
    description: "Monthly and daily activity trends over your chat history.",
  },
  {
    icon: Users,
    title: "Group insights",
    description: "See who is most active and how participation is distributed.",
  },
  {
    icon: BarChart3,
    title: "Activity heatmaps",
    description: "Discover peak days, months, and hours of conversation.",
  },
  {
    icon: Smile,
    title: "Emoji analysis",
    description: "Top emojis with counts and distribution charts.",
  },
  {
    icon: Shield,
    title: "Privacy first",
    description:
      "Your export is processed in memory on the server and expires after one hour.",
  },
];

export default function HomePage() {
  return (
    <div>
      <section className="relative overflow-hidden border-b border-[var(--border)] bg-gradient-to-b from-[var(--primary)]/10 to-transparent">
        <div className="mx-auto max-w-6xl px-4 py-20 text-center md:py-28">
          <p className="mb-4 inline-block rounded-full bg-[var(--primary)]/15 px-4 py-1 text-sm font-medium text-[var(--primary)]">
            Production-grade chat analytics
          </p>
          <h1 className="mx-auto max-w-3xl text-4xl font-bold tracking-tight md:text-5xl">
            Turn your WhatsApp export into beautiful insights
          </h1>
          <p className="mx-auto mt-6 max-w-2xl text-lg text-[var(--muted-foreground)]">
            Upload a .txt export from WhatsApp and explore timelines, activity
            maps, word clouds, emoji breakdowns, and more — all in a modern
            interactive dashboard.
          </p>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-4">
            <Link href="/analyze">
              <Button size="lg">Get started — upload chat</Button>
            </Link>
            <a
              href="https://faq.whatsapp.com/1180414079177245/?helpref=uf_share"
              target="_blank"
              rel="noopener noreferrer"
            >
              <Button variant="outline" size="lg">
                How to export from WhatsApp
              </Button>
            </a>
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-6xl px-4 py-16">
        <h2 className="mb-8 text-center text-2xl font-bold">What you get</h2>
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {features.map(({ icon: Icon, title, description }) => (
            <Card key={title}>
              <CardContent className="p-6">
                <div className="mb-4 flex h-10 w-10 items-center justify-center rounded-lg bg-[var(--primary)]/10">
                  <Icon className="h-5 w-5 text-[var(--primary)]" />
                </div>
                <h3 className="font-semibold">{title}</h3>
                <p className="mt-2 text-sm text-[var(--muted-foreground)]">
                  {description}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      </section>
    </div>
  );
}
