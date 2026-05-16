"use client";

import {
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts";

const COLORS = [
  "#25D366",
  "#128C7E",
  "#075E54",
  "#34B7F1",
  "#ECE5DD",
  "#FF6B6B",
  "#FFD93D",
  "#6C5CE7",
];

interface EmojiPieChartProps {
  data: { emoji: string; count: number }[];
}

export function EmojiPieChart({ data }: EmojiPieChartProps) {
  const top = data.slice(0, 12);

  return (
    <ResponsiveContainer width="100%" height="100%">
      <PieChart>
        <Pie
          data={top}
          dataKey="count"
          nameKey="emoji"
          cx="50%"
          cy="50%"
          outerRadius={100}
          label={(props) => {
            const payload = props as { emoji?: string; percent?: number };
            const emojiChar = payload.emoji ?? "";
            const pct = ((payload.percent ?? 0) * 100).toFixed(0);
            return `${emojiChar} ${pct}%`;
          }}
        >
          {top.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          formatter={(value, _name, props) => [
            value,
            (props.payload as { emoji: string }).emoji,
          ]}
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}
