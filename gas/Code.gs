// 早起きアプリの記録をこのスプレッドシートに置くための受け口。
// 「data」シートに1行1件で保存する: 種類 | id | 更新時刻(ms) | 中身の要約 | 中身(JSON)
// 合言葉は「プロジェクトの設定 → スクリプト プロパティ」に KEY という名前で入れる。

const SHEET = 'data';
const KINDS = ['settings', 'log', 'hlog', 'habits', 'todos', 'study', 'dead'];

function doPost(e) {
  let out;
  try {
    const req = JSON.parse(e.postData.contents);
    const key = PropertiesService.getScriptProperties().getProperty('KEY');
    if (!key || req.key !== key) throw new Error('合言葉が違います');
    const fn = { sync, add, list }[req.fn];
    if (!fn) throw new Error('知らない操作です: ' + req.fn);
    const lock = LockService.getScriptLock();
    lock.waitLock(20000);
    try { out = { ok: true, result: fn.apply(null, req.args || []) }; } finally { lock.releaseLock(); }
  } catch (err) {
    out = { ok: false, error: String(err && err.message || err) };
  }
  return ContentService.createTextOutput(JSON.stringify(out)).setMimeType(ContentService.MimeType.JSON);
}

// ---- 保存 ----
function sheet_() {
  const ss = SpreadsheetApp.getActive();
  let sh = ss.getSheetByName(SHEET);
  if (!sh) {
    sh = ss.insertSheet(SHEET);
    sh.getRange(1, 1, 1, 5).setValues([['kind', 'id', 'u', 'summary', 'json']]).setFontWeight('bold');
    sh.setFrozenRows(1);
  }
  return sh;
}
function read_() {
  const sh = sheet_();
  const doc = {}; KINDS.forEach(k => doc[k] = {});
  const n = sh.getLastRow() - 1;
  if (n > 0) sh.getRange(2, 1, n, 5).getValues().forEach(([kind, id, u, , json]) => {
    if (doc[kind] && id !== '') { try { doc[kind][String(id)] = JSON.parse(json); } catch (e) {} }
  });
  return doc;
}
function summary_(kind, v) {
  if (kind === 'todos') return (v.done ? '✓ ' : '') + (v.text || '') + (v.due ? '（' + v.due + 'まで）' : '');
  if (kind === 'habits') return v.name || '';
  if (kind === 'log') return ['c1', 'c2', 'c3'].map(k => v[k] ? k + ' ' + Utilities.formatDate(new Date(v[k]), Session.getScriptTimeZone(), 'HH:mm') : '').filter(String).join(' / ');
  if (kind === 'hlog') return (v.ids || []).length + '件';
  if (kind === 'study') return (v.at ? Utilities.formatDate(new Date(v.at), Session.getScriptTimeZone(), 'M/d HH:mm') + ' ' : '') + (v.min || 0) + '分';
  return '';
}
function write_(doc) {
  const sh = sheet_();
  const rows = [];
  KINDS.forEach(kind => Object.keys(doc[kind]).sort().forEach(id => {
    const v = doc[kind][id];
    rows.push([kind, id, v.u || 0, summary_(kind, v), JSON.stringify(v)]);
  }));
  const n = sh.getLastRow() - 1;
  if (n > 0) sh.getRange(2, 1, n, 5).clearContent();
  if (rows.length) sh.getRange(2, 1, rows.length, 5).setNumberFormat('@').setValues(rows);
}
// 同じものは更新時刻(u)が新しいほうを残す
function merge_(into, from) {
  KINDS.forEach(kind => {
    const src = (from && from[kind]) || {};
    Object.keys(src).forEach(id => {
      const a = into[kind][id], b = src[id];
      if (!a || (b.u || 0) > (a.u || 0)) into[kind][id] = b;
    });
  });
  return into;
}

// ---- 操作 ----
// アプリ: 手元の記録を送って、まざったものを受けとる
function sync(doc) {
  const merged = merge_(read_(), doc);
  write_(merged);
  return merged;
}
// Obsidian・Claude から TODO を足す。src が同じものは二度足さない(消したもの・終わったものも復活させない)
// items: [{ text, due, src, done }]。done:true のときは、すでにあるものを完了にする
function add(items) {
  const doc = read_();
  const now = Date.now();
  let added = 0, done = 0;
  (items || []).forEach(it => {
    const text = String(it.text || '').trim().slice(0, 80);
    if (!text) return;
    const id = it.src ? 'src-' + hash_(it.src) : 'cl-' + now.toString(36) + Math.random().toString(36).slice(2, 6);
    const cur = doc.todos[id];
    if (doc.dead[id]) return;
    if (!cur) {
      if (it.done) return;
      doc.todos[id] = { id, text, due: it.due || '', done: null, src: it.src || 'claude', u: now };
      added++;
    } else if (it.done && !cur.done) {
      cur.done = new Date().toISOString(); cur.u = now; done++;
    } else if (!cur.done && (cur.text !== text || (it.due || '') !== cur.due)) {
      cur.text = text; cur.due = it.due || ''; cur.u = now;
    }
  });
  write_(doc);
  return { added, done };
}
// Claude 用: 今の TODO・日課・最近の早起きの記録を返す
function list() {
  const doc = read_();
  const todos = Object.values(doc.todos).filter(x => !doc.dead[x.id]);
  return {
    todos: todos.filter(x => !x.done).map(x => ({ text: x.text, due: x.due, src: x.src || '' })),
    doneRecently: todos.filter(x => x.done).sort((a, b) => a.done < b.done ? 1 : -1).slice(0, 20).map(x => ({ text: x.text, done: x.done })),
    habits: Object.values(doc.habits).filter(h => !doc.dead[h.id]).map(h => ({ name: h.name, days: h.days })),
    wake: Object.keys(doc.log).sort().slice(-14).map(d => Object.assign({ day: d }, doc.log[d])),
    settings: doc.settings.main || null,
  };
}
function hash_(s) {
  return Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_1, s, Utilities.Charset.UTF_8)
    .slice(0, 8).map(b => ((b + 256) % 256).toString(16).padStart(2, '0')).join('');
}
