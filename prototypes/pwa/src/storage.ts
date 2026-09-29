import { openDB, type DBSchema } from "idb";

export interface StoredShare {
  file: Blob;
  name: string;
  type: string;
  size: number;
  receivedAt: number;
}

interface ShareDatabase extends DBSchema {
  shares: { key: string; value: StoredShare };
}

function openStorage() {
  return openDB<ShareDatabase>("solfeo-pwa-prototype", 1, {
    upgrade(database) {
      database.createObjectStore("shares");
    },
  });
}

export async function saveShare(file: File): Promise<void> {
  const database = await openStorage();
  try {
    const transaction = database.transaction("shares", "readwrite");
    await transaction.store.put(
      {
        file: file.slice(0, file.size, file.type),
        name: file.name,
        type: file.type,
        size: file.size,
        receivedAt: Date.now(),
      },
      "latest",
    );
    await transaction.done;
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
