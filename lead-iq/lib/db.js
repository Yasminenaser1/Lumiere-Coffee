import fs   from 'fs';
import path from 'path';

const DB_PATH = path.join(process.cwd(), 'leads.json');

export function readDb() {
  try {
    if (fs.existsSync(DB_PATH)) {
      return JSON.parse(fs.readFileSync(DB_PATH, 'utf-8'));
    }
  } catch {}
  return { leads: [], nextId: 1 };
}

export function writeDb(data) {
  fs.writeFileSync(DB_PATH, JSON.stringify(data, null, 2));
}
