"use client";

import { create } from "zustand";

interface WorkspaceState {
  chatId: string;
  selectedUser: string;
  setChatId: (id: string) => void;
  setSelectedUser: (user: string) => void;
  reset: () => void;
}

export const useWorkspaceStore = create<WorkspaceState>((set) => ({
  chatId: "",
  selectedUser: "Overall",
  setChatId: (id) => set({ chatId: id }),
  setSelectedUser: (user) => set({ selectedUser: user }),
  reset: () => set({ chatId: "", selectedUser: "Overall" }),
}));
