import { PrismaClient } from "@prisma/client"
import { PrismaPg } from "@prisma/adapter-pg"
import pg from "pg"

const globalForPrisma = globalThis as unknown as { prisma: PrismaClient }

const getPrismaClient = () => {
  const connectionString = process.env.DATABASE_URL || "postgresql://dummy:dummy@localhost:5432/dummy"
  const pool = new pg.Pool({ connectionString })
  const adapter = new PrismaPg(pool)
  return new PrismaClient({ adapter })
}

export const prisma = globalForPrisma.prisma || getPrismaClient()

if (process.env.NODE_ENV !== "production") globalForPrisma.prisma = prisma
