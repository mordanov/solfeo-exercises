import { openDB, type DBSchema } from "idb";
import type { ErrorCode } from "./share";

type FieldName = "audio" | "text" | "title" | "url" | "other";
export type SharedField =
  | { field: FieldName; kind: "text"; nonempty: boolean }
  | { field: FieldName; kind: "file"; type: string; size: number };

export interface ShareAttempt {
  receivedAt: number;
  outcome: ErrorCode | "RECEIVED";
  fields: SharedField[];
}

export interface StoredShare {
  file: Blob;
  name: string;
  type: string;
  size: number;
  receivedAt: number;
}

interface ShareDatabase extends DBSchema {
  shares: { key: string; value: StoredShare };
  attempts: { key: string; value: ShareAttempt };
}

function openStorage() {
  return openDB<ShareDatabase>("solfeo-pwa-prototype", 2, {
    upgrade(database, oldVersion) {
      if (oldVersion < 1) database.createObjectStore("shares");
      if (oldVersion < 2) database.createObjectStore("attempts");
    },
  });
}

export async function saveShare(
  file: File,
  attempt?: ShareAttempt,
): Promise<void> {
  const database = await openStorage();
  try {
    const transaction = database.transaction(
      ["shares", "attempts"],
      "readwrite",
    );
    const recorded = attempt
      ? transaction.objectStore("attempts").put(attempt, "latest")
      : Promise.resolve();
    const saved = transaction.objectStore("shares").put(
      {
        file: file.slice(0, file.size, file.type),
        name: file.name,
        type: file.type,
        size: file.size,
        receivedAt: Date.now(),
      },
      "latest",
    );
    await Promise.all([recorded, saved, transaction.done]);
  } finally {
    database.close();
  }
}

export async function saveAttempt(attempt: ShareAttempt): Promise<void> {
  const database = await openStorage();
  try {
    await database.put("attempts", attempt, "latest");
  } finally {
    database.close();
  }
}

export async function readAttempt(): Promise<ShareAttempt | null> {
  const database = await openStorage();
  try {
    return (await database.get("attempts", "latest")) ?? null;
  } finally {
    database.close();
  }
}

export async function clearAttempt(): Promise<void> {
  const database = await openStorage();
  try {
    await database.delete("attempts", "latest");
  } finally {
    database.close();
  }
}

export async function readShare(): Promise<StoredShare | null> {
  const database = await openStorage();
  try {
    return (await database.get("shares", "latest")) ?? null;
  } finally {
    database.close();
  }
}

export async function clearShare(): Promise<void> {
  const database = await openStorage();
  try {
    await database.delete("shares", "latest");
  } finally {
    database.close();
  }
}
