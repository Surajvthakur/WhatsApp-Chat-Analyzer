const API_BASE =
  process.env.NEXT_PUBLIC_API_URL?.replace(/\/$/, "") || "http://localhost:8000";

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (res.ok) {
    if (res.status === 204) return undefined as T;
    const contentType = res.headers.get("content-type") || "";
    if (contentType.includes("application/json")) {
      return res.json() as Promise<T>;
    }
    return res as unknown as T;
  }

  let detail = res.statusText;
  try {
    const body = await res.json();
    detail = body.detail || (typeof body === "string" ? body : detail);
    if (Array.isArray(detail)) {
      detail = detail.map((d) => d.msg || JSON.stringify(d)).join(", ");
    }
  } catch {
    /* ignore */
  }
  throw new ApiError(String(detail), res.status);
}

export interface DateRange {
  start: string | null;
  end: string | null;
}

export interface ChatUploadResponse {
  chat_id: string;
  users: string[];
  message_count: number;
  date_range: DateRange;
}

export interface StatsResponse {
  messages: number;
  words: number;
  media: number;
  links: number;
}

export interface TimelinePoint {
  time: string;
  message: number;
}

export interface DailyTimelinePoint {
  only_date: string;
  message: number;
}

export interface LabeledCount {
  label: string;
  count: number;
}

export interface HeatmapResponse {
  days: string[];
  periods: string[];
  values: number[][];
}

export interface BusyUserItem {
  user: string;
  count: number;
}

export interface BusyUserPercent {
  name: string;
  percent: number;
}

export interface BusyUsersResponse {
  top_users: BusyUserItem[];
  percentages: BusyUserPercent[];
}

export interface WordCount {
  word: string;
  count: number;
}

export interface EmojiCount {
  emoji: string;
  count: number;
}

export async function uploadChat(file: File): Promise<ChatUploadResponse> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/api/v1/chats`, {
    method: "POST",
    body: form,
  });
  return handleResponse<ChatUploadResponse>(res);
}

async function getJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: "no-store" });
  return handleResponse<T>(res);
}

export function getUsers(chatId: string) {
  return getJson<string[]>(`/api/v1/chats/${chatId}/users`);
}

export function getStats(chatId: string, user: string) {
  return getJson<StatsResponse>(
    `/api/v1/chats/${chatId}/stats?user=${encodeURIComponent(user)}`,
  );
}

export function getMonthlyTimeline(chatId: string, user: string) {
  return getJson<TimelinePoint[]>(
    `/api/v1/chats/${chatId}/timeline/monthly?user=${encodeURIComponent(user)}`,
  );
}

export function getDailyTimeline(chatId: string, user: string) {
  return getJson<DailyTimelinePoint[]>(
    `/api/v1/chats/${chatId}/timeline/daily?user=${encodeURIComponent(user)}`,
  );
}

export function getWeekActivity(chatId: string, user: string) {
  return getJson<LabeledCount[]>(
    `/api/v1/chats/${chatId}/activity/week?user=${encodeURIComponent(user)}`,
  );
}

export function getMonthActivity(chatId: string, user: string) {
  return getJson<LabeledCount[]>(
    `/api/v1/chats/${chatId}/activity/month?user=${encodeURIComponent(user)}`,
  );
}

export function getActivityHeatmap(chatId: string, user: string) {
  return getJson<HeatmapResponse>(
    `/api/v1/chats/${chatId}/activity/heatmap?user=${encodeURIComponent(user)}`,
  );
}

export function getBusyUsers(chatId: string) {
  return getJson<BusyUsersResponse>(
    `/api/v1/chats/${chatId}/users/busy?user=Overall`,
  );
}

export function getCommonWords(chatId: string, user: string) {
  return getJson<WordCount[]>(
    `/api/v1/chats/${chatId}/words/common?user=${encodeURIComponent(user)}`,
  );
}

export function getEmoji(chatId: string, user: string) {
  return getJson<EmojiCount[]>(
    `/api/v1/chats/${chatId}/emoji?user=${encodeURIComponent(user)}`,
  );
}

/** Bump when word-cloud rendering changes so browsers refetch the PNG. */
const WORDCLOUD_CACHE_VERSION = "3";

export function getWordCloudUrl(chatId: string, user: string): string {
  const params = new URLSearchParams({
    user,
    v: WORDCLOUD_CACHE_VERSION,
  });
  return `${API_BASE}/api/v1/chats/${chatId}/words/cloud?${params.toString()}`;
}

export interface Workspace {
  id: string;
  workspaceName: string;
  createdAt: string;
  summary: string | null;
}

export interface WorkspaceListResponse {
  workspaces: Workspace[];
}

export interface WorkspaceSaveResponse {
  status: string;
  workspace: Workspace;
}

export interface WorkspaceLoadResponse {
  status: string;
  chatId: string;
  users: string[];
  messageCount: number;
  dateRange: DateRange;
}

export async function saveWorkspace(chatId: string, workspaceName: string): Promise<WorkspaceSaveResponse> {
  const res = await fetch("/api/workspaces", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ chatId, workspaceName }),
  });
  return handleResponse<WorkspaceSaveResponse>(res);
}

export async function getWorkspaces(): Promise<Workspace[]> {
  const res = await fetch("/api/workspaces");
  const data = await handleResponse<WorkspaceListResponse>(res);
  return data.workspaces;
}

export async function deleteWorkspace(id: string): Promise<void> {
  const res = await fetch(`/api/workspaces/${id}`, {
    method: "DELETE",
  });
  return handleResponse<void>(res);
}

export async function loadWorkspace(id: string): Promise<WorkspaceLoadResponse> {
  const res = await fetch(`/api/workspaces/${id}/load`, {
    method: "POST",
  });
  return handleResponse<WorkspaceLoadResponse>(res);
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ChatHistoryResponse {
  status: string;
  messages: ChatMessage[];
}

export async function getChatHistory(workspaceId: string): Promise<ChatMessage[]> {
  const res = await fetch(`/api/workspaces/${workspaceId}/chat`);
  const data = await handleResponse<ChatHistoryResponse>(res);
  return data.messages;
}

export async function addChatMessage(
  workspaceId: string,
  role: "user" | "assistant",
  content: string
): Promise<void> {
  const res = await fetch(`/api/workspaces/${workspaceId}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ role, content }),
  });
  return handleResponse<void>(res);
}

