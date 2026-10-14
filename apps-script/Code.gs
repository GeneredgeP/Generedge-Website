/**
 * GenerEdge — website lead forms
 *
 * Receives the lead forms on generedge.com (home, /business-loans/,
 * /contact-us/) and emails each lead to TO, with reply-to set to the person
 * who filled the form in. Every lead is also appended to a Google Sheet
 * ("GenerEdge — Website Leads"), created on the first run of setup().
 *
 * Lives at script.google.com under eduardo@generedge.com, project
 * "GenerEdge — Website Forms". This file is the source of truth: edit here,
 * paste into the editor, then Deploy → Manage deployments → (pencil) →
 * Version: New version → Deploy. That keeps the same /exec URL.
 *
 * Two request shapes arrive:
 *  - JavaScript on: fetch POST, Content-Type text/plain, body is JSON with
 *    human labels ("Form", "First name", "Email"...). text/plain keeps it a
 *    CORS "simple" request, so there is no preflight Apps Script can't answer.
 *  - JavaScript off: native form POST, urlencoded, raw field names
 *    (form_name, first_name, email...). The visitor's browser lands on the
 *    response, so that path gets a small HTML thank-you page, not JSON.
 */

const TO = 'eduardo@generedge.com';
const SITE = 'https://generedge.com';
const SHEET_NAME = 'GenerEdge — Website Leads';

// ---------------------------------------------------------------- spam
// Anything judged spam is NOT emailed but IS logged to the Sheet with the
// reason in the Status column, so a false positive is never a lost lead —
// filter the Sheet by Status to review them.
//
// The bots seen so far POST straight to this /exec URL (it is the form's
// action, so it is in the page source) without loading the page. site.js
// sends _t, the milliseconds the visitor spent on the page; a direct POST
// has none, and a bot that does run the page submits almost instantly.
const MIN_FILL_MS = 2000;

// The multilingual "I wanted to know your price" template.
const SPAM_PHRASES = [
  /zin[aā]t (savu|j[uū]su) cenu/i,
  /узнать (вашу|свою) цен/i,
  /\bwanted to know (your|the) price/i,
  /quer[ií]a saber (su|tu|el) precio/i,
  /wollte (ihren|deinen|den) preis wissen/i,
];

// Raw field names (no-JS path) → the labels the JS path already uses.
const LABELS = {
  form_name: 'Form',
  first_name: 'First name',
  last_name: 'Last name',
  email: 'Email',
  phone: 'Phone',
  business_name: 'Business name',
  years_in_business: 'Years in business',
  loan_type: 'Loan type',
  project_type: 'Project type',
  amount: 'Amount requested',
  message: 'Message',
  sms_consent: 'SMS consent',
};

function doPost(e) {
  const native = !!(e && e.postData && e.postData.type === 'application/x-www-form-urlencoded');
  let data = {};
  try {
    data = (e && e.postData && !native)
      ? JSON.parse(e.postData.contents)
      : ((e && e.parameter) || {});
  } catch (err) {
    data = (e && e.parameter) || {};
  }

  const lead = normalise_(data);

  const spam = verdict_(data, native, lead);
  if (spam) {
    log_(lead, spam);
    // Answer as if it worked: telling a bot why it failed teaches it.
    return reply_(native, { ok: true, held: native });
  }
  const replyTo = String(lead['Email'] || '').trim();
  const subject = (lead['Form'] || 'Website enquiry') + ' — generedge.com';
  const lines = Object.keys(lead).map(function (k) { return k + ': ' + lead[k]; });

  const opts = {
    to: TO,
    subject: subject,
    name: 'generedge.com',
    body: lines.join('\n'),
    htmlBody: table_(lead),
  };
  if (/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(replyTo)) opts.replyTo = replyTo;

  try {
    MailApp.sendEmail(opts);
  } catch (err) {
    console.error('sendEmail failed: ' + err);
    log_(lead, 'EMAIL FAILED: ' + err);
    return reply_(native, { ok: false, error: 'send failed' });
  }

  log_(lead, 'sent');
  return reply_(native, { ok: true });
}

/** '' for a real lead, otherwise the reason it was held. */
function verdict_(data, native, lead) {
  if (data._honey) return 'spam: honeypot filled';
  // Real visitors run site.js and arrive as JSON. A urlencoded POST is the
  // no-JavaScript path, which in practice is only ever bots; the rare real
  // person who lands here is logged and told to call or email.
  if (native) return 'held: posted without the page (no JavaScript)';
  const t = Number(data._t);
  if (!t) return 'spam: no page timer';
  if (t < MIN_FILL_MS) return 'spam: filled in ' + t + ' ms';
  return contentFlag_(lead);
}

function contentFlag_(lead) {
  const first = String(lead['First name'] || '');
  const last = String(lead['Last name'] || '');
  const msg = String(lead['Message'] || '');
  const all = Object.keys(lead).map(function (k) { return String(lead[k]); }).join('\n');

  if (/https?:|www\.|<a\s/i.test(first + ' ' + last)) return 'spam: link in name';
  const tag = camelTail_(first);
  if (tag && tag === camelTail_(last)) return 'spam: same tag on both names (' + tag + ')';
  if ((msg.match(/https?:\/\/|www\./gi) || []).length >= 2) return 'spam: several links in message';
  if (/[\u0400-\u04FF]/.test(all)) return 'spam: Cyrillic text';
  for (var i = 0; i < SPAM_PHRASES.length; i++) {
    if (SPAM_PHRASES[i].test(all)) return 'spam: known template';
  }
  return '';
}

// "LarryNeokyGM" -> "NeokyGM": the tag some bots glue onto a real first name,
// identical on first and last name ("LarryNeokyGM MichaelNeokyGM").
function camelTail_(name) {
  const m = /[a-z]([A-Z][A-Za-z]{3,})$/.exec(String(name).trim());
  return m ? m[1] : '';
}

// Health check: opening the /exec URL in a browser shows {"ok":true,...}.
function doGet() {
  return json_({ ok: true, service: 'generedge.com forms' });
}

/** Labels for raw names, drops internal "_" fields, stamps time if missing. */
function normalise_(data) {
  const out = {};
  Object.keys(data).forEach(function (k) {
    if (k.charAt(0) === '_') return;
    const v = data[k];
    if (v === '' || v === null || v === undefined) return;
    out[LABELS[k] || k] = String(v);
  });
  if (!out['Submitted']) {
    out['Submitted'] = Utilities.formatDate(new Date(), 'America/New_York', 'yyyy-MM-dd HH:mm z');
  }
  return out;
}

function table_(lead) {
  const esc = function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  };
  const rows = Object.keys(lead).map(function (k) {
    return '<tr><td style="padding:6px 12px;border:1px solid #ddd;font-weight:600;vertical-align:top">' +
      esc(k) + '</td><td style="padding:6px 12px;border:1px solid #ddd;white-space:pre-wrap">' +
      esc(lead[k]) + '</td></tr>';
  });
  return '<table style="border-collapse:collapse;font-family:Arial,sans-serif;font-size:14px">' +
    rows.join('') + '</table>';
}

/** Appends the lead to the sheet. Never lets a sheet problem lose the email. */
function log_(lead, status) {
  try {
    const id = PropertiesService.getScriptProperties().getProperty('SHEET_ID');
    if (!id) return;
    const sh = SpreadsheetApp.openById(id).getSheets()[0];
    let header = sh.getLastRow() ? sh.getRange(1, 1, 1, sh.getLastColumn()).getValues()[0] : [];
    if (!header.length) {
      header = ['Logged', 'Status'];
      sh.appendRow(header);
    }
    Object.keys(lead).forEach(function (k) {
      if (header.indexOf(k) === -1) {
        header.push(k);
        sh.getRange(1, header.length).setValue(k);
      }
    });
    const row = header.map(function (h) {
      if (h === 'Logged') return new Date();
      if (h === 'Status') return status;
      return lead[h] || '';
    });
    sh.appendRow(row);
  } catch (err) {
    console.error('sheet log failed: ' + err);
  }
}

function reply_(native, obj) {
  if (!native) return json_(obj);
  const msg = obj.held
    ? 'We could not send this form automatically. Please email ' + TO +
      ' or call (727) 370-0200 and we will help you right away.'
    : obj.ok
    ? 'Thank you — we received your details and will be in touch shortly.'
    : 'Sorry, something went wrong. Please email ' + TO + ' or call (727) 370-0200.';
  return HtmlService.createHtmlOutput(
    '<div style="font-family:Arial,sans-serif;max-width:520px;margin:60px auto;padding:0 16px">' +
    '<h1 style="font-size:22px">GenerEdge</h1><p>' + msg + '</p>' +
    '<p><a href="' + SITE + '" target="_top">Back to generedge.com</a></p></div>'
  ).setTitle('GenerEdge');
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

/**
 * Run once from the editor: authorises MailApp + Sheets, creates the leads
 * sheet (if not already set) and sends a test email through doPost.
 */
function setup() {
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('SHEET_ID')) {
    const ss = SpreadsheetApp.create(SHEET_NAME);
    ss.getSheets()[0].setName('Leads');
    props.setProperty('SHEET_ID', ss.getId());
    console.log('Created sheet: ' + ss.getUrl());
  } else {
    console.log('Sheet: https://docs.google.com/spreadsheets/d/' + props.getProperty('SHEET_ID'));
  }
  const res = doPost({
    postData: {
      type: 'text/plain',
      // _t stands in for the page timer site.js sends, or this would be held as spam.
      contents: JSON.stringify({ Form: 'Setup test', 'First name': 'Test', Email: TO, _t: '5000' }),
    },
  });
  console.log(res.getContent());
}
