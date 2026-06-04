"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  getActivityHeatmap,
  getBusyUsers,
  getCommonWords,
  getDailyTimeline,
  getEmoji,
  getMonthActivity,
  getMonthlyTimeline,
  getUsers,
  getWeekActivity,
  getWordCloudUrl,
  saveWorkspace,
} from "@/lib/api";
import { monthLabel } from "@/lib/utils";
import { StatCards } from "@/components/dashboard/stat-cards";
import { ChartShell } from "@/components/charts/chart-shell";
import { TimelineChart } from "@/components/charts/timeline-chart";
import { BarChartCard } from "@/components/charts/bar-chart-card";
import { HeatmapGrid } from "@/components/charts/heatmap-grid";
import { EmojiPieChart } from "@/components/charts/emoji-pie-chart";
import { Select } from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Bot, Save, Loader2 } from "lucide-react";
import { useAuth } from "@/lib/auth-context";

interface DashboardViewProps {
  chatId: string;
  selectedUser: string;
  onUserChange: (user: string) => void;
}

export function DashboardView({
  chatId,
  selectedUser,
  onUserChange,
}: DashboardViewProps) {
  const { user } = useAuth();
  const [isSaveModalOpen, setIsSaveModalOpen] = useState(false);
  const [workspaceName, setWorkspaceName] = useState("WhatsApp Chat Analysis");
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saveSuccess, setSaveSuccess] = useState(false);

  const { data: users = [] } = useQuery({
    queryKey: ["users", chatId],
    queryFn: () => getUsers(chatId),
  });

  const monthly = useQuery({
    queryKey: ["monthly", chatId, selectedUser],
    queryFn: () => getMonthlyTimeline(chatId, selectedUser),
  });

  const daily = useQuery({
    queryKey: ["daily", chatId, selectedUser],
    queryFn: () => getDailyTimeline(chatId, selectedUser),
  });

  const weekActivity = useQuery({
    queryKey: ["week", chatId, selectedUser],
    queryFn: () => getWeekActivity(chatId, selectedUser),
  });

  const monthActivity = useQuery({
    queryKey: ["month-activity", chatId, selectedUser],
    queryFn: () => getMonthActivity(chatId, selectedUser),
  });

  const heatmap = useQuery({
    queryKey: ["heatmap", chatId, selectedUser],
    queryFn: () => getActivityHeatmap(chatId, selectedUser),
  });

  const busyUsers = useQuery({
    queryKey: ["busy-users", chatId],
    queryFn: () => getBusyUsers(chatId),
    enabled: selectedUser === "Overall",
  });

  const commonWords = useQuery({
    queryKey: ["words", chatId, selectedUser],
    queryFn: () => getCommonWords(chatId, selectedUser),
  });

  const emoji = useQuery({
    queryKey: ["emoji", chatId, selectedUser],
    queryFn: () => getEmoji(chatId, selectedUser),
  });

  const wordCloudUrl = getWordCloudUrl(chatId, selectedUser);

  const monthlyData =
    monthly.data?.map((d) => ({ label: d.time, value: d.message })) ?? [];
  const dailyData =
    daily.data?.map((d) => ({
      label: d.only_date.slice(0, 10),
      value: d.message,
    })) ?? [];
  const weekData =
    weekActivity.data?.map((d) => ({ label: d.label, count: d.count })) ?? [];
  const monthData =
    monthActivity.data?.map((d) => ({
      label: monthLabel(d.label),
      count: d.count,
    })) ?? [];
  const wordsData =
    commonWords.data?.map((d) => ({ label: d.word, count: d.count })) ?? [];

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Chat Analytics</h1>
          <p className="text-sm text-[var(--muted-foreground)]">
            Insights for {selectedUser === "Overall" ? "everyone" : selectedUser}
          </p>
        </div>
        <div className="flex w-full flex-col sm:w-auto sm:flex-row sm:items-end gap-4">
          <div className="w-full sm:w-64">
            <label htmlFor="user-select" className="mb-1 block text-xs font-medium">
              Show analysis for
            </label>
            <Select
              id="user-select"
              value={selectedUser}
              onChange={(e) => onUserChange(e.target.value)}
            >
              {users.map((u) => (
                <option key={u} value={u}>
                  {u}
                </option>
              ))}
            </Select>
          </div>
          <div className="flex w-full flex-col sm:w-auto sm:flex-row gap-2">
            {user ? (
              <Button
                onClick={() => setIsSaveModalOpen(true)}
                variant="outline"
                className="flex items-center gap-2 border-[var(--primary)] text-[var(--primary)] hover:bg-[var(--primary)]/10 w-full sm:w-auto"
              >
                <Save className="h-4 w-4" />
                Save Workspace
              </Button>
            ) : (
              <Button
                onClick={() => {
                  window.location.href = `/login?callbackUrl=/dashboard/${chatId}`;
                }}
                variant="outline"
                className="flex items-center gap-2 border-[var(--border)] text-[var(--muted-foreground)] hover:bg-[var(--muted)] w-full sm:w-auto"
              >
                <Save className="h-4 w-4" />
                Save Workspace (Login)
              </Button>
            )}
          </div>
        </div>
      </div>

      {isSaveModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200">
          <div className="relative w-full max-w-md overflow-hidden rounded-xl border border-[var(--border)] bg-[var(--card)] p-6 shadow-2xl animate-in zoom-in-95 duration-200">
            <h3 className="text-lg font-bold text-[var(--foreground)]">Save Workspace</h3>
            <p className="mt-2 text-sm text-[var(--muted-foreground)]">
              This will save your chat data, statistics, and vector embeddings so you can return to them instantly later without re-uploading.
            </p>
            
            <div className="mt-4">
              <label htmlFor="workspace-name-input" className="block text-xs font-semibold text-[var(--muted-foreground)] uppercase tracking-wider mb-2">
                Workspace Name
              </label>
              <input
                id="workspace-name-input"
                type="text"
                value={workspaceName}
                onChange={(e) => setWorkspaceName(e.target.value)}
                className="w-full rounded-lg border border-[var(--border)] bg-transparent px-3 py-2 text-sm text-[var(--foreground)] outline-none focus:border-[var(--primary)] transition-colors"
                placeholder="e.g. Chat with Rahul"
                disabled={isSaving || saveSuccess}
              />
            </div>
            
            {saveError && (
              <p className="mt-3 text-sm text-red-500 font-medium">
                {saveError}
              </p>
            )}
            
            {saveSuccess && (
              <p className="mt-3 text-sm text-[var(--primary)] font-medium">
                ✓ Workspace saved successfully! Redirecting...
              </p>
            )}
            
            <div className="mt-6 flex justify-end gap-3">
              <Button
                variant="outline"
                onClick={() => {
                  setIsSaveModalOpen(false);
                  setSaveError(null);
                }}
                disabled={isSaving || saveSuccess}
              >
                Cancel
              </Button>
              <Button
                onClick={async () => {
                  if (!workspaceName.trim()) {
                    setSaveError("Workspace name cannot be empty.");
                    return;
                  }
                  setIsSaving(true);
                  setSaveError(null);
                  try {
                    await saveWorkspace(chatId, workspaceName);
                    setSaveSuccess(true);
                    setTimeout(() => {
                      setIsSaveModalOpen(false);
                      setSaveSuccess(false);
                      window.location.href = "/analyze";
                    }, 1500);
                  } catch (err: any) {
                    setSaveError(err.message || "Failed to save workspace.");
                  } finally {
                    setIsSaving(false);
                  }
                }}
                disabled={isSaving || saveSuccess}
                className="flex items-center gap-2"
              >
                {isSaving ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Saving…
                  </>
                ) : (
                  <>
                    <Save className="h-4 w-4" />
                    Save
                  </>
                )}
              </Button>
            </div>
          </div>
        </div>
      )}

      <section>
        <h2 className="mb-4 text-lg font-semibold">Top Statistics</h2>
        <StatCards chatId={chatId} user={selectedUser} />
      </section>

      <ChartShell
        title="Monthly Timeline"
        description="Message volume over months"
        isLoading={monthly.isLoading}
        isEmpty={!monthly.isLoading && monthlyData.length === 0}
      >
        <TimelineChart data={monthlyData} color="#25D366" xLabel="Month" />
      </ChartShell>

      <ChartShell
        title="Daily Timeline"
        description="Message volume per day"
        isLoading={daily.isLoading}
        isEmpty={!daily.isLoading && dailyData.length === 0}
      >
        <TimelineChart data={dailyData} color="#128C7E" xLabel="Date" />
      </ChartShell>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartShell
          title="Most Busy Day"
          isLoading={weekActivity.isLoading}
          isEmpty={!weekActivity.isLoading && weekData.length === 0}
        >
          <BarChartCard data={weekData} color="#6C5CE7" />
        </ChartShell>
        <ChartShell
          title="Most Busy Month"
          isLoading={monthActivity.isLoading}
          isEmpty={!monthActivity.isLoading && monthData.length === 0}
        >
          <BarChartCard data={monthData} color="#FF6B6B" />
        </ChartShell>
      </div>

      <ChartShell
        title="Weekly Activity Map"
        description="Messages by day and hour period"
        isLoading={heatmap.isLoading}
        isEmpty={
          !heatmap.isLoading &&
          (!heatmap.data || heatmap.data.days.length === 0)
        }
        className="col-span-full"
        contentClassName="h-auto"
      >
        {heatmap.data && <HeatmapGrid data={heatmap.data} />}
      </ChartShell>

      {selectedUser === "Overall" && (
        <div className="grid gap-6 lg:grid-cols-2">
          <ChartShell
            title="Most Busy Users"
            isLoading={busyUsers.isLoading}
            isEmpty={
              !busyUsers.isLoading &&
              (!busyUsers.data || busyUsers.data.top_users.length === 0)
            }
          >
            <BarChartCard
              data={
                busyUsers.data?.top_users.map((u) => ({
                  label: u.user,
                  count: u.count,
                })) ?? []
              }
              color="#25D366"
              layout="horizontal"
            />
          </ChartShell>
          <Card>
            <CardHeader>
              <CardTitle>User Share (%)</CardTitle>
            </CardHeader>
            <CardContent>
              {busyUsers.isLoading ? (
                <div className="space-y-2">
                  {[1, 2, 3, 4, 5].map((i) => (
                    <div key={i} className="h-8 animate-pulse rounded bg-[var(--muted)]" />
                  ))}
                </div>
              ) : (
                <div className="max-h-[320px] overflow-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-[var(--border)] text-left">
                        <th className="pb-2 font-medium">User</th>
                        <th className="pb-2 font-medium">%</th>
                      </tr>
                    </thead>
                    <tbody>
                      {busyUsers.data?.percentages.map((row) => (
                        <tr
                          key={row.name}
                          className="border-b border-[var(--border)]/50"
                        >
                          <td className="py-2">{row.name}</td>
                          <td className="py-2 tabular-nums">{row.percent}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <Card className="overflow-hidden">
        <CardHeader>
          <CardTitle>Word Cloud</CardTitle>
        </CardHeader>
        <CardContent className="relative flex min-h-[300px] items-center justify-center overflow-hidden bg-gradient-to-br from-[#075E54]/12 via-[var(--muted)]/50 to-[#25D366]/12 px-4 py-8 sm:px-8">
          <div
            className="pointer-events-none absolute -right-16 -top-16 h-48 w-48 rounded-full bg-[#25D366]/10 blur-3xl"
            aria-hidden
          />
          <div
            className="pointer-events-none absolute -bottom-12 -left-12 h-40 w-40 rounded-full bg-[#128C7E]/15 blur-3xl"
            aria-hidden
          />
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={wordCloudUrl}
            alt="Word cloud of most-used words in this chat"
            className="relative z-10 max-h-[min(560px,70vh)] w-full max-w-4xl object-contain drop-shadow-[0_8px_32px_rgba(37,211,102,0.15)]"
          />
        </CardContent>
      </Card>

      <ChartShell
        title="Most Common Words"
        isLoading={commonWords.isLoading}
        isEmpty={!commonWords.isLoading && wordsData.length === 0}
      >
        <BarChartCard data={wordsData} color="#128C7E" layout="horizontal" />
      </ChartShell>

      <div className="grid gap-6 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>Emoji Analysis</CardTitle>
          </CardHeader>
          <CardContent>
            {emoji.isLoading ? (
              <div className="space-y-2">
                {[1, 2, 3].map((i) => (
                    <div key={i} className="h-6 animate-pulse rounded bg-[var(--muted)]" />
                ))}
              </div>
            ) : emoji.data && emoji.data.length > 0 ? (
              <div className="max-h-[320px] overflow-y-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--border)] text-left">
                      <th className="pb-2">Emoji</th>
                      <th className="pb-2">Count</th>
                    </tr>
                  </thead>
                  <tbody>
                    {emoji.data.map((row) => (
                      <tr
                        key={row.emoji}
                        className="border-b border-[var(--border)]/50"
                      >
                        <td className="py-2 text-xl">{row.emoji}</td>
                        <td className="py-2 tabular-nums">{row.count}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-[var(--muted-foreground)]">No emojis found</p>
            )}
          </CardContent>
        </Card>
        <ChartShell
          title="Emoji Distribution"
          isLoading={emoji.isLoading}
          isEmpty={!emoji.isLoading && (!emoji.data || emoji.data.length === 0)}
        >
          {emoji.data && <EmojiPieChart data={emoji.data} />}
        </ChartShell>
      </div>
    </div>
  );
}
