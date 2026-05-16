"use client";

import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

interface BarChartCardProps {
  data: { label: string; count: number }[];
  color?: string;
  layout?: "vertical" | "horizontal";
}

export function BarChartCard({
  data,
  color = "#128C7E",
  layout = "vertical",
}: BarChartCardProps) {
  const isHorizontal = layout === "horizontal";

  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart
        data={data}
        layout={isHorizontal ? "vertical" : "horizontal"}
        margin={{ top: 8, right: 8, left: isHorizontal ? 80 : 8, bottom: isHorizontal ? 8 : 48 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" />
        {isHorizontal ? (
          <>
            <XAxis type="number" tick={{ fontSize: 11 }} allowDecimals={false} />
            <YAxis type="category" dataKey="label" tick={{ fontSize: 11 }} width={72} />
          </>
        ) : (
          <>
            <XAxis
              dataKey="label"
              tick={{ fontSize: 11 }}
              angle={-25}
              textAnchor="end"
              height={50}
            />
            <YAxis tick={{ fontSize: 11 }} allowDecimals={false} />
          </>
        )}
        <Tooltip
          contentStyle={{
            background: "var(--card)",
            border: "1px solid var(--border)",
            borderRadius: "8px",
          }}
        />
        <Bar dataKey="count" name="Count" fill={color} radius={[4, 4, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
