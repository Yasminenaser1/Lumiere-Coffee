import { NextResponse } from 'next/server';
import { readDb, writeDb } from '@/lib/db';
import Groq from 'groq-sdk';

export async function POST(request) {
  try {
    const { leadId } = await request.json();
    const db   = readDb();
    const idx  = db.leads.findIndex(l => l.id === leadId);

    if (idx === -1) {
      return NextResponse.json({ error: 'Lead not found' }, { status: 404 });
    }
    const lead = db.leads[idx];

    const groqKey = (process.env.GROQ_API_KEY || '').trim();
    console.log('KEY CHECK:', groqKey ? `found (${groqKey.slice(0,8)}...)` : 'MISSING');

    // No API key — return a demo score
    if (!groqKey || groqKey === 'paste_your_key_here') {
      const score  = Math.floor(Math.random() * 4) + 5;
      const reason = 'Demo mode — add your GROQ_API_KEY to .env.local for real AI scoring';
      db.leads[idx] = { ...lead, score, score_reason: reason };
      writeDb(db);
      return NextResponse.json({ score, reason, lead: db.leads[idx] });
    }

    const client = new Groq({ apiKey: groqKey });

    const prompt = `You are a B2B sales qualification expert for coffee shop equipment, supplies, and services.

Score this lead from 1-10 on likelihood to become a paying customer:

Company: ${lead.company}
Contact: ${lead.contact_name}${lead.title ? ` (${lead.title})` : ''}
Size: ${lead.company_size || 'Unknown'}
Notes: ${lead.notes || 'None'}

Scoring guide:
- 9-10: Decision maker at a growing coffee chain or large single location with clear budget
- 7-8: Owner or ops manager at a mid-size shop, genuine interest
- 5-6: Staff member or small independent, possible but slow conversion
- 1-4: Wrong fit, no authority, or very low spend potential

Reply in this exact JSON only — no extra text:
{"score": 7, "reason": "One concise sentence explaining the score."}`;

    const completion = await client.chat.completions.create({
      model: 'llama-3.3-70b-versatile',
      messages: [{ role: 'user', content: prompt }],
      max_tokens: 120,
      temperature: 0.3,
    });

    const raw = completion.choices[0].message.content.trim();
    const match = raw.match(/\{[\s\S]*?\}/);
    if (!match) throw new Error('Bad JSON from Groq: ' + raw);

    const { score, reason } = JSON.parse(match[0]);

    db.leads[idx] = { ...lead, score, score_reason: reason };
    writeDb(db);

    return NextResponse.json({ score, reason, lead: db.leads[idx] });
  } catch (err) {
    console.error('Score error:', err);
    return NextResponse.json({ error: err.message }, { status: 500 });
  }
}
