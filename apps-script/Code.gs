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

  if (data._honey) return reply_(native, { ok: true });   // bot: say ok, drop it

  const lead = normalise_(data);
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
  const msg = obj.ok
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
      contents: JSON.stringify({ Form: 'Setup test', 'First name': 'Test', Email: TO }),
    },
  });
  console.log(res.getContent());
}
