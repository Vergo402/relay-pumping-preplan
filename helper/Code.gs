// Report helper for the Relay Pumping Pre-plan page.
// The page sends a report. This script makes a GitHub issue from it.
// The GitHub key is not in this file. It is the script property GITHUB_TOKEN.
var REPO = 'Vergo402/relay-pumping-preplan';
var MAX_TEXT = 1000; // characters in one report
var DAY_MAX = 20;    // reports in one day, New York time

function reply(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

// Makes one line of plain text. The zero-width space stops a GitHub @mention.
function clean(v, max) {
  return String(v || '').replace(/[\u0000-\u0008\u000b-\u001f]/g, ' ').replace(/@/g, '@​').trim().slice(0, max);
}

function doPost(e) {
  try {
    var d = JSON.parse(e.postData.contents);
    if (d.website) return reply({ ok: true, number: 0 }); // the trap field: a person never fills it
    var raw = String(d.text || '').trim();
    if (!raw || raw.length > MAX_TEXT) return reply({ ok: false, why: 'text' });
    var idea = d.kind === 'idea';
    var text = clean(raw, MAX_TEXT), name = clean(d.name, 80).replace(/\s+/g, ' ');

    var props = PropertiesService.getScriptProperties();
    var lock = LockService.getScriptLock();
    lock.waitLock(10000);
    var day = Utilities.formatDate(new Date(), 'America/New_York', 'yyyy-MM-dd');
    var n = props.getProperty('day') === day ? Number(props.getProperty('count')) : 0;
    if (n >= DAY_MAX) { lock.releaseLock(); return reply({ ok: false, why: 'limit' }); }
    props.setProperties({ day: day, count: String(n + 1) });
    lock.releaseLock();

    var first = text.replace(/\s+/g, ' ');
    var body = text + '\n\n---\n' + (name ? 'From: ' + name + '\n' : '') +
      'Page version: ' + clean(d.version, 20) + '\nBrowser: ' + clean(d.browser, 200) + '\n';
    var r = UrlFetchApp.fetch('https://api.github.com/repos/' + REPO + '/issues', {
      method: 'post', contentType: 'application/json', muteHttpExceptions: true,
      headers: { Authorization: 'Bearer ' + props.getProperty('GITHUB_TOKEN'), Accept: 'application/vnd.github+json' },
      payload: JSON.stringify({
        title: (idea ? 'Idea: ' : 'Problem: ') + first.slice(0, 60) + (first.length > 60 ? '...' : ''),
        body: body, labels: [idea ? 'enhancement' : 'bug', 'from the page']
      })
    });
    if (r.getResponseCode() !== 201) return reply({ ok: false, why: 'github', code: r.getResponseCode() });
    var issue = JSON.parse(r.getContentText());
    return reply({ ok: true, number: issue.number, url: issue.html_url });
  } catch (err) {
    return reply({ ok: false, why: 'error' });
  }
}

// Run this one time in the editor. Google then asks for the approval that the helper needs.
function approve() {
  var r = UrlFetchApp.fetch('https://api.github.com/repos/' + REPO, { muteHttpExceptions: true });
  Logger.log('GitHub answer: ' + r.getResponseCode() + '. Key set: ' + !!PropertiesService.getScriptProperties().getProperty('GITHUB_TOKEN'));
}
