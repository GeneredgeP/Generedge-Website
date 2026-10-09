/* ==========================================================================
   GenerEdge — site behaviour
   - mobile nav
   - scroll reveals + animated counters
   - cookie consent (gates Google Analytics — GA never loads without consent)
   - accessible form validation + submission
   ========================================================================== */
(function () {
  'use strict';

  var reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  /* ---------------------------------------------------------------- nav */
  var toggle = document.querySelector('.navtoggle');
  var links = document.getElementById('navlinks');
  if (toggle && links) {
    var mq = window.matchMedia('(max-width:900px)');
    var sync = function () {
      if (mq.matches) {
        links.hidden = toggle.getAttribute('aria-expanded') !== 'true';
      } else {
        links.hidden = false;
      }
    };
    toggle.addEventListener('click', function () {
      var open = toggle.getAttribute('aria-expanded') === 'true';
      toggle.setAttribute('aria-expanded', String(!open));
      sync();
    });
    // addListener is the pre-2019 Safari spelling; keep both so the menu still
    // reacts to rotation on older iOS.
    if (mq.addEventListener) mq.addEventListener('change', sync);
    else if (mq.addListener) mq.addListener(sync);
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape' && toggle.getAttribute('aria-expanded') === 'true') {
        toggle.setAttribute('aria-expanded', 'false');
        sync();
        toggle.focus();
      }
    });
    // Tapping a link closes the menu — otherwise same-page anchors leave the
    // panel covering the section the visitor just jumped to.
    links.addEventListener('click', function (e) {
      if (!mq.matches) return;
      if (!e.target.closest('a')) return;
      toggle.setAttribute('aria-expanded', 'false');
      sync();
    });
    sync();
  }

  /* ------------------------------------------------- reveals + counters */
  // The final value is already in the HTML, so the number is correct with
  // JavaScript disabled. We only animate up to it when JS is available.
  function count(el) {
    if (el.dataset.done) return;
    el.dataset.done = '1';
    var lit = el.dataset.literal;
    if (lit) { el.textContent = lit; return; }
    var target = parseFloat(el.dataset.count),
        pre = el.dataset.prefix || '',
        suf = el.dataset.suffix || '';
    if (reduce) { el.textContent = pre + target + suf; return; }
    el.textContent = pre + 0 + suf;
    var t0 = null, dur = 1200;
    function frame(t) {
      if (!t0) t0 = t;
      var p = Math.min((t - t0) / dur, 1), e = 1 - Math.pow(1 - p, 3);
      el.textContent = pre + Math.round(target * e) + suf;
      if (p < 1) requestAnimationFrame(frame);
    }
    requestAnimationFrame(frame);
  }

  var targets = document.querySelectorAll('.rv, .stats .wrap, .fees');
  if ('IntersectionObserver' in window) {
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('is-in');
        e.target.querySelectorAll('[data-count]').forEach(count);
        io.unobserve(e.target);
      });
    }, { threshold: 0.2 });
    targets.forEach(function (el) { io.observe(el); });
  } else {
    targets.forEach(function (el) {
      el.classList.add('is-in');
      el.querySelectorAll('[data-count]').forEach(count);
    });
  }

  /* ------------------------------------------------------ cookie consent */
  var CONSENT_KEY = 'ge_consent_v1';

  function readConsent() {
    try { return localStorage.getItem(CONSENT_KEY); } catch (e) { return null; }
  }
  function writeConsent(v) {
    try { localStorage.setItem(CONSENT_KEY, v); } catch (e) { /* private mode */ }
  }

  function loadAnalytics() {
    var id = window.GE_GA_ID;
    // Placeholder guard: nothing loads until a real GA4 ID is set in build.py.
    if (!id || id.indexOf('G-') !== 0 || id === 'G-XXXXXXXXXX') return;
    if (window.__geGaLoaded) return;
    window.__geGaLoaded = true;

    var s = document.createElement('script');
    s.async = true;
    s.src = 'https://www.googletagmanager.com/gtag/js?id=' + encodeURIComponent(id);
    document.head.appendChild(s);

    window.dataLayer = window.dataLayer || [];
    window.gtag = function () { window.dataLayer.push(arguments); };
    window.gtag('js', new Date());
    window.gtag('config', id, { anonymize_ip: true });
  }

  var banner = document.querySelector('.cc');
  var stored = readConsent();

  if (stored === 'granted') {
    loadAnalytics();
  } else if (stored !== 'denied' && banner) {
    banner.hidden = false;
  }

  if (banner) {
    banner.addEventListener('click', function (e) {
      var btn = e.target.closest('[data-consent]');
      if (!btn) return;
      var choice = btn.getAttribute('data-consent');
      writeConsent(choice);
      banner.hidden = true;
      if (choice === 'granted') loadAnalytics();
    });
  }

  // Lets a "Cookie settings" link anywhere on the site reopen the banner.
  document.addEventListener('click', function (e) {
    var re = e.target.closest('[data-consent-reopen]');
    if (!re) return;
    e.preventDefault();
    if (!banner) return;
    banner.hidden = false;
    // The banner is position:fixed and its buttons are the last thing in the
    // document, so without moving focus a keyboard or screen-reader user gets
    // no sign that anything happened.
    banner.setAttribute('tabindex', '-1');
    banner.focus();
  });

  /* --------------------------------------------------------------- forms */
  // Where lead submissions go. Configured in the FORM dict in scripts/build.py
  // and injected into every page's <head> as window.GE_FORM.
  var CFG = window.GE_FORM || {};
  var PROVIDER = CFG.provider || '';
  var ENDPOINT = CFG.endpoint || '';
  var TO_EMAIL = CFG.email || 'info@generedge.com';
  var TO_PHONE = CFG.phone || '(727) 370-0200';
  var SUBJECT = CFG.subject || 'New enquiry from generedge.com';

  function fieldError(field, msg) {
    var wrap = field.closest('.f') || field.closest('.consent');
    var slot = wrap && wrap.querySelector('.err');
    field.setAttribute('aria-invalid', msg ? 'true' : 'false');
    if (slot) slot.textContent = msg || '';
  }

  function validate(form) {
    var firstBad = null;
    form.querySelectorAll('input, select, textarea').forEach(function (field) {
      if (field.type === 'hidden' || field.closest('.hp')) return;
      var msg = '';
      var value = (field.value || '').trim();
      if (field.hasAttribute('required')) {
        if (field.type === 'checkbox') {
          if (!field.checked) msg = 'Please confirm to continue.';
        } else if (field.tagName === 'SELECT') {
          if (!value) msg = 'Please choose an option.';
        } else if (!value) {
          msg = 'This field is required.';
        }
      }
      if (!msg && field.type === 'email' && value &&
          !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(value)) {
        msg = 'Enter a valid email address.';
      }
      fieldError(field, msg);
      if (msg && !firstBad) firstBad = field;
    });
    return firstBad;
  }

  // Human-readable name for a field, so the notification email reads like the
  // form rather than like a database dump. Falls back to the input's name.
  function labelFor(field) {
    if (field.dataset && field.dataset.label) return field.dataset.label;
    var wrap = field.closest('.f, .consent');
    var span = wrap && wrap.querySelector('span');
    var text = span ? span.textContent.replace(/\*/g, '').trim() : '';
    return text || field.name;
  }

  function collect(form) {
    var out = {};
    function put(key, value) {
      if (!key) return;
      out[key] = out[key] === undefined ? value : out[key] + ', ' + value;
    }
    form.querySelectorAll('input, select, textarea').forEach(function (field) {
      if (!field.name || field.closest('.hp')) return;
      if (field.type === 'checkbox') {
        if (field.checked) put(labelFor(field), 'Yes');
        return;
      }
      if (field.type === 'radio') {
        if (field.checked) put(labelFor(field), field.value);
        return;
      }
      if (field.type === 'hidden') { put(field.name === 'form_name' ? 'Form' : field.name, field.value); return; }
      var value = (field.value || '').trim();
      if (value) put(labelFor(field), value);
    });
    return out;
  }

  function emailOf(form) {
    var el = form.querySelector('input[type="email"]');
    return el ? el.value.trim() : '';
  }

  // Windows' mailto handler and several mail clients truncate or refuse a URL
  // much past 2000 characters, and this is the last-resort path — a silent drop
  // here loses the lead twice over.
  var MAILTO_MAX = 1400;

  function mailtoLink(payload) {
    var lines = Object.keys(payload).map(function (k) { return k + ': ' + payload[k]; });
    var body = lines.join('\n');
    if (body.length > MAILTO_MAX) {
      body = body.slice(0, MAILTO_MAX) + '\n\n[truncated — please paste the rest below]';
    }
    return 'mailto:' + TO_EMAIL +
      '?subject=' + encodeURIComponent(payload.Form || SUBJECT) +
      '&body=' + encodeURIComponent(body);
  }

  // Some providers answer 200 with a failure body, so the body is authoritative
  // where there is one.
  function succeeded(res, body) {
    if (!res.ok) return false;
    if (PROVIDER === 'formsubmit' || PROVIDER === 'web3forms') {
      if (!body) return false;
      if (!(body.success === true || body.success === 'true')) return false;
      // FormSubmit answers the very first POST to a new address with a success
      // code and a message asking for the address to be confirmed. Nothing was
      // delivered, so treat it as a failure and give the visitor the mailto
      // fallback rather than a thank-you for a lead that went nowhere.
      if (/activat|confirm your email|verify your email/i.test(body.message || '')) return false;
      return true;
    }
    if (PROVIDER === 'formspree' && body && body.ok === false) return false;
    // The Apps Script answers {"ok":false} with a 200 if MailApp fails.
    if (PROVIDER === 'custom' && body && body.ok === false) return false;
    return true;
  }

  // A stalled mobile connection would otherwise leave the visitor watching a
  // disabled "Sending..." button until the browser's own network timeout.
  var SEND_TIMEOUT = 20000;

  function send(form, payload) {
    var body = {};
    Object.keys(payload).forEach(function (k) { body[k] = payload[k]; });

    // collect() emits human labels ("Email"), which no provider recognises as
    // the reply-to address — so set it explicitly, whichever provider is in use.
    // Without it, replying to a lead notification goes to the provider, not the
    // person who filled the form in.
    var replyTo = emailOf(form);
    var subject = (payload.Form ? payload.Form + ' — ' : '') + SUBJECT;

    if (PROVIDER === 'formsubmit') {
      body._subject = subject;
      body._template = 'table';
      body._captcha = 'false';
      if (replyTo) body._replyto = replyTo;
    } else if (PROVIDER === 'web3forms') {
      body.access_key = CFG.accessKey || '';
      body.subject = subject;
      body.from_name = 'generedge.com';
      if (replyTo) body.replyto = replyTo;
    } else if (PROVIDER === 'formspree') {
      body._subject = subject;
      if (replyTo) body._replyto = replyTo;
    }

    // The custom endpoint is a Google Apps Script web app, which cannot answer
    // a CORS preflight. 'application/json' (or any extra header such as
    // Accept) would trigger one, so send the same JSON as text/plain: that is
    // a "simple" request, fetch follows Apps Script's 302 to its content host
    // and reads the 200. The script parses the body as JSON regardless.
    var headers = PROVIDER === 'custom'
      ? { 'Content-Type': 'text/plain;charset=utf-8' }
      : { 'Content-Type': 'application/json', Accept: 'application/json' };

    var request = fetch(ENDPOINT, {
      method: 'POST',
      headers: headers,
      body: JSON.stringify(body)
    }).then(function (res) {
      return res.json().catch(function () { return null; }).then(function (json) {
        if (!succeeded(res, json)) throw new Error('rejected');
        return json;
      });
    });

    var timeout = new Promise(function (_resolve, reject) {
      setTimeout(function () { reject(new Error('timeout')); }, SEND_TIMEOUT);
    });

    return Promise.race([request, timeout]);
  }

  function setStatus(status, state, text, link) {
    if (!status) return;
    status.dataset.state = state;
    status.textContent = text;
    if (link) {
      status.appendChild(document.createTextNode(' '));
      var a = document.createElement('a');
      a.href = link;
      a.textContent = 'Send it by email instead';
      a.style.textDecoration = 'underline';
      status.appendChild(a);
      status.appendChild(document.createTextNode('.'));
    }
  }

  document.querySelectorAll('form[data-lead-form]').forEach(function (form) {
    // Take over validation only now that we are here to do it. The markup
    // keeps native validation so that a visitor without JavaScript still gets
    // required-field enforcement before the form posts.
    form.noValidate = true;

    var status = form.querySelector('.form__status');
    var submit = form.querySelector('[type="submit"]');
    var sending = false;

    form.addEventListener('submit', function (e) {
      e.preventDefault();
      if (sending) return;

      var bad = validate(form);
      if (bad) {
        setStatus(status, 'err', 'Please correct the highlighted fields.');
        bad.focus();
        return;
      }

      // Honeypot — a real visitor never sees this field, so anything in it is
      // a bot. Show the success state and drop the submission.
      var hp = form.querySelector('.hp input');
      if (hp && hp.value) {
        form.reset();
        setStatus(status, 'ok', 'Thank you. We received your request and will be in touch shortly.');
        return;
      }

      var payload = collect(form);
      payload.Page = window.location.pathname;
      payload.Submitted = new Date().toISOString();

      if (!ENDPOINT) {
        setStatus(status, 'err',
          'This form is not connected yet. Please call ' + TO_PHONE + ' or email ' + TO_EMAIL + '.',
          mailtoLink(payload));
        return;
      }

      sending = true;
      if (submit) {
        submit.setAttribute('aria-disabled', 'true');
        if (!submit.dataset.label) submit.dataset.label = submit.textContent;
        submit.textContent = 'Sending...';
      }
      if (status) { status.dataset.state = ''; status.textContent = ''; }

      // send() can throw before returning a promise — an engine with no fetch,
      // or a blocked global. Route that into the same failure branch instead of
      // leaving the button stuck on "Sending..." with no message.
      var pending;
      try {
        if (typeof window.fetch !== 'function') throw new Error('no-fetch');
        pending = send(form, payload);
      } catch (err) {
        pending = Promise.reject(err);
      }

      pending
        .then(function () {
          form.reset();
          form.querySelectorAll('[aria-invalid="true"]').forEach(function (f) { fieldError(f, ''); });
          setStatus(status, 'ok', 'Thank you. We received your request and will be in touch shortly.');
          if (window.gtag) window.gtag('event', 'generate_lead', { form_id: form.id || 'unknown' });
        })
        .catch(function () {
          setStatus(status, 'err',
            'We could not send that from here. Please call ' + TO_PHONE + ' or email ' + TO_EMAIL + '.',
            mailtoLink(payload));
          if (status) { status.setAttribute('tabindex', '-1'); status.focus(); }
        })
        .then(function () {
          sending = false;
          if (submit) {
            submit.removeAttribute('aria-disabled');
            submit.textContent = submit.dataset.label || 'Submit';
          }
        });
    });

    function clearOnEdit(e) {
      if (e.target.getAttribute && e.target.getAttribute('aria-invalid') === 'true') {
        fieldError(e.target, '');
      }
    }
    form.addEventListener('input', clearOnEdit);
    form.addEventListener('change', clearOnEdit);
  });
})();
