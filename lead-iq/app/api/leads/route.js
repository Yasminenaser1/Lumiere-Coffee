import { NextResponse } from 'next/server';
import { readDb, writeDb } from '@/lib/db';

export async function GET() {
  try {
    const { leads } = readDb();
    return NextResponse.json([...leads].sort((a, b) => b.id - a.id));
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}

export async function POST(request) {
  try {
    const body = await request.json();
    const { company, contact_name, email, title, company_size, notes } = body;

    if (!company || !contact_name) {
      return NextResponse.json(
        { error: 'company and contact_name are required' },
        { status: 400 }
      );
    }

    const db = readDb();
    const lead = {
      id:           db.nextId,
      company,
      contact_name,
      email:        email        || '',
      title:        title        || '',
      company_size: company_size || '',
      score:        0,
      score_reason: '',
      status:       'New',
      notes:        notes        || '',
      created_at:   new Date().toISOString(),
    };
    db.leads.push(lead);
    db.nextId += 1;
    writeDb(db);

    return NextResponse.json(lead, { status: 201 });
  } catch (err) {
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
