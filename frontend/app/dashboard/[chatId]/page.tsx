"use client";

import { use } from "react";
import { useState } from "react";
import { DashboardView } from "@/components/dashboard/dashboard-view";

interface DashboardPageProps {
  params: Promise<{ chatId: string }>;
}

export default function DashboardPage({ params }: DashboardPageProps) {
  const { chatId } = use(params);
  const [selectedUser, setSelectedUser] = useState("Overall");

  return (
    <div className="mx-auto max-w-6xl px-4 py-8">
      <DashboardView
        chatId={chatId}
        selectedUser={selectedUser}
        onUserChange={setSelectedUser}
      />
    </div>
  );
}
