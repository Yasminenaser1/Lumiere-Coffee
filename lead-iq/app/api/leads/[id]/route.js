import { NextResponse } from 'next/server';
import { readDb, writeDb } from '@/lib/db';

export async function PATCH(request, { params }) {
  try {
    const body    = await request.json();
    const id      = parseInt(params.id);
    const allowed = ['status', 'score', 'score_reason', 'notes'];
    const db      = readDb();

    const idx = db.leads.findIndex(l => l.id === id);
    if (idx === -1) return NextResponse.json({ error: 'Not found' }, { status: 404 });

    for (const [k, v] of Object.entries(body)) {
      if (allowed.includes(k)) db.leads[idx][k] = v;
    }
    writeDb(db);
    return NextResponse.json(db.leads[idx]);
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function DELETE(request, { params }) {
  try {
    const id = parseInt(params.id);
    const db = readDb();
    db.leads  = db.leads.filter(l => l.id !== id);
    writeDb(db);
    return NextResponse.json({ deleted: id });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
