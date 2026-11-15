// Keyboard Firmware Maker — interface web.
// Le projet (même format que les .kfm.json de l'application de bureau) vit dans
// le navigateur ; le serveur génère et compile à la demande.
// Les adresses sont relatives : l'interface marche aussi derrière un sous-chemin (YunoHost).
'use strict';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
const clone = o => JSON.parse(JSON.stringify(o));
let META = null, P = null, MODE = 'hardware', STATUS = null, JOB = null;
let JOBLOG = [], LASTJOB = null;   // journal et état de la dernière tâche, gardés après sa fin
const STORE = 'kfm.project', STORE_NAME = 'kfm.project.name';

async function api(path, opts = {}) {
  const r = await fetch(path, opts.body !== undefined && !(opts.body instanceof Blob)
    ? {method: 'POST', headers: {'Content-Type': 'application/json'}, ...opts, body: JSON.stringify(opts.body)}
    : opts);
  const data = await r.json().catch(() => ({error: `réponse illisible (HTTP ${r.status})`}));
  if (!r.ok || data.error) throw new Error(data.error || `HTTP ${r.status}`);
  return data;
}

function tr(key, vars = {}) {
  let s = (META && META.strings[key]) || key;
  for (const [k, v] of Object.entries(vars)) s = s.replace(`{${k}}`, v);
  return s;
}

function toast(msg, ms = 3500) {
  const t = $('toast');
  t.textContent = msg;
  t.classList.remove('hidden');
  clearTimeout(toast._t);
  toast._t = setTimeout(() => t.classList.add('hidden'), ms);
}

// ─────────────────────────────────────────────────────────── projet ──

function save() {
  try { localStorage.setItem(STORE, JSON.stringify(P)); } catch (e) { /* stockage plein ou interdit */ }
  renderSide();
}

function setProjectName(v) {
  try { localStorage.setItem(STORE_NAME, v); } catch (e) { /* ignore */ }
}

function projectName() {
  return ($('project-name').value || P.keyboard.model || 'projet').replace(/[^\w.-]+/g, '_');
}

function newProject() {
  if (P.keyboard.model && !confirm('Repartir d\'un projet vide ? Le projet courant sera perdu s\'il n\'est pas enregistré.')) return;
  P = clone(META.default_project);
  $('project-name').value = '';
  setProjectName('');
  save();
  showMode('hardware');
}

async function openProject(file) {
  if (!file) return;
  try {
    const data = JSON.parse(await file.text());
    P = (await api('api/project/normalize', {body: {project: data}})).project;
    $('project-name').value = file.name.replace(/(\.kfm)?\.json$/, '');
    setProjectName($('project-name').value);
    save();
    showMode(MODE);
    await Promise.all(['left', 'right'].flatMap(sd => P.oled[sd].images).map(i => loadImage(i.image_path)));
    const missing = allImages().length;
    toast(`Projet « ${file.name} » ouvert` + (missing ? ` — ${missing} image(s) OLED à renvoyer depuis l'onglet OLED` : ''), missing ? 8000 : 3500);
  } catch (e) {
    toast('Ouverture impossible : ' + e.message, 6000);
  }
}

function downloadProject() {
  const blob = new Blob([JSON.stringify(P, null, 2)], {type: 'application/json'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = projectName() + '.kfm.json';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

// ─────────────────────────────────────────────────────────── clavier ──

const kb = () => META.keyboards.find(k => k.model === P.keyboard.model);
const mcu = () => (kb()?.mcu_options || []).find(m => m.id === P.keyboard.mcu);
const firmware = () => mcu()?.firmware || 'qmk';
const hasOled = () => !!kb()?.capabilities?.oled && P.keyboard.oled_sides.length > 0;
const hasRgb = () => !!kb()?.capabilities?.rgb && P.keyboard.rgb_enabled;

function selectKeyboard(model) {
  const k = META.keyboards.find(x => x.model === model);
  if (!k || P.keyboard.model === model) return;
  // mêmes valeurs par défaut que l'onglet Matériel de l'application de bureau
  P.keyboard.model = model;
  P.keyboard.mcu = k.mcu_options[0]?.id || '';
  P.keyboard.layout_variant = k.layout_variants.length > 1 ? k.layout_variants[0].slug : '';
  P.keyboard.oled_sides = k.capabilities.oled ? ['left', 'right'] : [];
  P.keyboard.rgb_enabled = !!k.capabilities.rgb;
  save();
  renderHardware();
}

// Touches affichées : par moitié pour un split, sinon la variante choisie (ou le layout « keys »).
function kbPanels(k = kb()) {
  if (!k) return [];
  const rows = k.matrix.rows || 5, cols = k.matrix.cols || 6;
  const keysOf = list => (list || []).filter(x => !x.encoder);
  let panels;
  if (k.split) {
    panels = [['L', keysOf(k.layout.left)], ['R', keysOf(k.layout.right)]];
  } else {
    const v = k.layout_variants.find(x => x.slug === P.keyboard.layout_variant) || k.layout_variants[0];
    panels = [['L', keysOf(k.layout.keys).length ? keysOf(k.layout.keys) : keysOf(v?.keys)]];
  }
  return panels.map(([side, keys]) => {
    if (!keys.length) {   // pas de positions physiques : grille de la matrice
      keys = [];
      for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) keys.push({row: r, col: c, x: c, y: r, w: 1, h: 1});
    }
    return {side, keys: keys.map(x => ({...x, id: `${side}_r${x.row}_c${x.col}`}))};
  });
}

// Vue du clavier. opts : prefix (id HTML des touches : <prefix>-<id>), onKey(id, ev), color(id) → css,
// cls(id) → classes, label(id) → texte
function kbView(opts = {}, U = 36) {
  return '<div class="kbview">' + kbPanels().map(p => {
    const minX = Math.min(...p.keys.map(x => x.x)), minY = Math.min(...p.keys.map(x => x.y));
    const W = Math.max(...p.keys.map(x => x.x + (x.w || 1))) - minX, H = Math.max(...p.keys.map(x => x.y + (x.h || 1))) - minY;
    return `<div class="kpanel" style="width:${W * U}px;height:${H * U}px">` + p.keys.map(x => {
      const bg = opts.color ? opts.color(x.id) : '';
      const style = `left:${(x.x - minX) * U}px;top:${(x.y - minY) * U}px;width:${(x.w || 1) * U - 3}px;height:${(x.h || 1) * U - 3}px;` +
        (x.r ? `transform:rotate(${x.r}deg);` : '') + (bg ? `background:${bg};` : '');
      const cls = ['key', opts.onKey ? 'click' : '', opts.cls ? opts.cls(x.id) : ''].join(' ');
      const ev = opts.onKey ? ` onclick="${opts.onKey}('${x.id}', event)" oncontextmenu="${opts.onKey}('${x.id}', event); return false"` : '';
      return `<div class="${cls}" id="${opts.prefix || 'k'}-${x.id}" style="${style}" title="${x.id}"${ev}>${esc(opts.label ? opts.label(x.id) : '')}</div>`;
    }).join('') + '</div>';
  }).join('') + '</div>';
}

// ─────────────────────────────────────────────────────────── navigation ──

function showMode(m) {
  MODE = m;
  document.querySelectorAll('.mode').forEach(b => b.classList.toggle('active', b.dataset.mode === m));
  for (const id of ['hardware', 'oled', 'rgb', 'advanced', 'build']) $('mode-' + id).classList.toggle('hidden', id !== m);
  ({hardware: renderHardware, oled: renderOled, rgb: renderRgb, advanced: renderAdvanced, build: renderBuild})[m]();
}

function renderSide() {
  const k = kb(), m = mcu();
  $('side-kb').innerHTML = k
    ? `<b>${esc(k.display_name)}</b><br><span class="muted">${esc(m?.display_name || '—')}</span><br>` +
      `<span class="badge acc">${firmware().toUpperCase()}</span> ` +
      (hasOled() ? `<span class="badge">OLED ${P.keyboard.oled_sides.map(s => s === 'left' ? 'G' : 'D').join('+')}</span> ` : '') +
      (hasRgb() ? '<span class="badge">RGB</span> ' : '') +
      (P.keyboard.use_custom_keymap ? '<span class="badge ok">keymap importé</span>' : '')
    : '<span class="muted">aucun clavier choisi</span>';
  const fw = $('pill-fw');
  fw.textContent = k ? `${k.display_name} · ${firmware().toUpperCase()}` : 'aucun clavier';
  fw.className = 'pill' + (k ? ' ok' : '');
}

async function refreshStatus() {
  try { STATUS = await api('api/status'); } catch (e) { STATUS = null; }
  const s = STATUS;
  const line = (ok, label, hint) => `<div>${ok ? '✅' : '❌'} ${label}${!ok && hint ? ` <span class="muted">— ${hint}</span>` : ''}</div>`;
  $('side-tools').innerHTML = !s ? '<span class="muted">serveur injoignable</span>' :
    '<b>QMK</b>' + line(s.qmk.vial_qmk, 'Vial-QMK', 'à télécharger (onglet Build)') +
    line(s.qmk.gcc, `arm-none-eabi-gcc ${s.qmk.gcc ? esc(s.qmk.gcc_version) : ''}`, 'sudo apt install gcc-arm-none-eabi') +
    '<b>ZMK</b>' + line(s.zmk.sdk, 'Zephyr SDK', 'scripts/setup_zmk.sh') + line(s.zmk.west, 'west', 'pip install west');
  if (s?.running && !JOB) pollJob(s.running);
}

// ─────────────────────────────────────────────────────────── Matériel ──

function renderHardware() {
  const k = kb();
  const kbCards = META.keyboards.map(x => {
    const badges = [x.split ? 'split' : 'monobloc', x.capabilities.oled ? 'OLED' : '', x.capabilities.rgb ? 'RGB' : '',
      x.has_encoder ? 'encodeur' : '', [...new Set(x.mcu_options.map(m => m.firmware.toUpperCase()))].join(' / ')].filter(Boolean);
    return `<div class="mitem ${x.model === P.keyboard.model ? 'sel' : ''}" onclick="selectKeyboard('${esc(x.model)}')">
      <div class="n">${esc(x.display_name)}</div>
      <div class="s">${badges.map(b => `<span class="badge">${esc(b)}</span>`).join('')}</div>
      <div class="blurb">${esc(x.description)}</div></div>`;
  }).join('');
  let html = `<section class="card"><h1><span class="num">1</span> Clavier</h1>
    <p class="lead">Les claviers prédéfinis, et ceux créés dans l'application de bureau (éditeur de clavier / import KLE).</p>
    <div class="mlist">${kbCards}</div></section>`;
  if (k) {
    html += `<section class="card"><h1><span class="num">2</span> Microcontrôleur</h1>
      <p class="lead">Il décide du firmware : <b>QMK / Vial</b> pour les MCU filaires, <b>ZMK</b> pour les MCU Bluetooth (nRF52840).</p>
      <div class="mlist">${k.mcu_options.map(m => `<div class="mitem ${m.id === P.keyboard.mcu ? 'sel' : ''}" onclick="setKb('mcu','${esc(m.id)}')">
        <div class="n">${esc(m.display_name)}</div><div class="s"><span class="badge acc">${m.firmware.toUpperCase()}</span><span class="badge">${esc(m.bootloader)}</span></div>
        <div class="blurb">${esc(m.description)}</div></div>`).join('')}</div></section>`;
    const fw = firmware();
    const rows = [];
    if (k.layout_variants.length > 1) {
      rows.push(setting('Variante de disposition', `<select onchange="setKb('layout_variant', this.value)">${k.layout_variants.map(v =>
        `<option value="${esc(v.slug)}" ${v.slug === P.keyboard.layout_variant ? 'selected' : ''}>${esc(v.label)}</option>`).join('')}</select>`));
    }
    if (k.capabilities.oled) {
      const cur = P.keyboard.oled_sides.join(',');
      const opts = k.split ? [['left,right', 'les deux'], ['left', 'gauche'], ['right', 'droite'], ['', 'aucun']] : [['left', 'oui'], ['', 'aucun']];
      rows.push(setting('Écrans OLED', `<select onchange="setKb('oled_sides', this.value ? this.value.split(',') : [])">${opts.map(([v, l]) =>
        `<option value="${v}" ${v === cur ? 'selected' : ''}>${l}</option>`).join('')}</select>`));
    }
    if (k.capabilities.rgb) {
      rows.push(setting('LEDs RGB', `<label class="switch"><input type="checkbox" ${P.keyboard.rgb_enabled ? 'checked' : ''} onchange="setKb('rgb_enabled', this.checked)"> activées</label>`));
      if (fw === 'qmk' && P.keyboard.rgb_enabled) {
        rows.push(setting('LEDs underglow par moitié', `<input type="number" min="-1" max="20" value="${P.keyboard.rgb_underglow_per_side}" onchange="setKb('rgb_underglow_per_side', +this.value)">
          <span class="muted small">-1 = toutes celles du clavier d'origine ; à régler sur ce que porte réellement votre PCB</span>`));
      }
    }
    if (fw === 'zmk') {
      rows.push(setting('Transport ZMK Studio', `<select onchange="setKb('zmk_studio_transport', this.value)">
        <option value="ble" ${P.keyboard.zmk_studio_transport === 'ble' ? 'selected' : ''}>Bluetooth</option>
        <option value="usb" ${P.keyboard.zmk_studio_transport === 'usb' ? 'selected' : ''}>USB</option></select>`));
      rows.push(setting('Journal de débogage USB', `<label class="switch"><input type="checkbox" ${P.keyboard.debug_logging ? 'checked' : ''} onchange="setKb('debug_logging', this.checked)"> port série virtuel (ttyACM)</label>`));
    }
    if (rows.length) html += `<section class="card"><h1><span class="num">3</span> Options matérielles</h1>${rows.join('')}</section>`;
    html += `<section class="card"><h1>Disposition</h1><p class="lead">Identifiants des touches (côté, rangée, colonne) tels qu'utilisés dans les effets RGB.</p>
      ${kbView({label: id => id.replace(/^([LR])_r(\d+)_c(\d+)$/, '$2·$3')})}</section>`;
  }
  $('mode-hardware').innerHTML = html;
}

function setting(label, ctl, help = '', off = false, tip = '') {
  return `<div class="setting ${off ? 'off' : ''}" ${tip ? `title="${esc(tip)}"` : ''}><div class="lab">${label}${help ? `<small>${help}</small>` : ''}</div><div class="ctl">${ctl}</div></div>`;
}

function setKb(field, value) {
  P.keyboard[field] = value;
  save();
  renderHardware();
}

// ─────────────────────────────────────────────────────────── OLED ──

const IMG = {};   // image_path → {preview, natural_w, natural_h, frames} | {missing:true}
const allImages = () => ['left', 'right'].flatMap(s => P.oled[s].images).filter(i => IMG[i.image_path]?.missing);

// Renvoie la vérification en cours (à attendre), ou rien si l'image est déjà connue.
function loadImage(path) {
  if (!IMG[path]) IMG[path] = {loading: (async () => {
    try {
      IMG[path] = await api('api/oled/image?path=' + encodeURIComponent(path));
    } catch (e) {
      IMG[path] = {missing: true};
    }
    if (MODE === 'oled') renderOled();
  })()};
  return IMG[path].loading;
}

async function uploadImage(side, file, col = 0, line = 0) {
  if (!file) return;
  try {
    const info = await api('api/oled/image?name=' + encodeURIComponent(file.name), {method: 'POST', body: file});
    IMG[info.image_path] = info;
    const img = {image_path: info.image_path, natural_w: info.natural_w, natural_h: info.natural_h,
      col: 0, line: 0, inverted: false, layer: -1};
    [img.col, img.line] = clampPos('img', img, col, line);
    P.oled[side].images.push(img);
    OSEL = `${side}|img:${P.oled[side].images.length - 1}`;
    save();
    renderOled();
    if (info.frames > 1) toast(`GIF animé : ${info.frames} images`);
  } catch (e) {
    toast('Image refusée : ' + e.message, 6000);
  }
}

// Image du projet absente du serveur (projet venu de l'application de bureau) : on renvoie le
// fichier, l'entrée garde sa position et ses réglages.
let RESEND = null;
const imgName = path => path.split(/[\\/]/).pop();

function resendImage(side, i) {
  RESEND = [side, i];
  $('re-oled').click();
}

async function replaceImage(file) {
  if (!file || !RESEND) return;
  const img = P.oled[RESEND[0]].images[RESEND[1]];
  try {
    const info = await api('api/oled/image?name=' + encodeURIComponent(file.name), {method: 'POST', body: file});
    IMG[info.image_path] = info;
    Object.assign(img, {image_path: info.image_path, natural_w: info.natural_w, natural_h: info.natural_h});
    [img.col, img.line] = clampPos('img', img, img.col, img.line);
    save();
    renderOled();
  } catch (e) {
    toast('Image refusée : ' + e.message, 6000);
  }
}

function setOled(path, value) {
  // path : « left.layer.col », « anti_burnin »…
  const parts = path.split('.');
  let o = P.oled;
  for (const p of parts.slice(0, -1)) o = o[p];
  o[parts.at(-1)] = value;
  save();
  renderOled();
}

const QMK_OVERLAYS = [['layer', 'Couche active'], ['caps_lock', 'Verr. Maj'], ['wpm', 'WPM (mots/min)'], ['rgb_mode', 'Mode RGB'], ['kfm', 'Logo <KFM>']];
const QMK_ANIMS = [['luna', 'Luna (chien)'], ['ocean_dream', 'Ocean Dream'], ['bongo', 'Bongo Cat'], ['crab', 'Crabe'], ['katawajojo', 'KatawaJojo']];
const ZMK_WIDGETS = [['zmk_battery', 'Batterie'], ['zmk_output', 'Sortie (USB/BLE)'], ['zmk_layer', 'Couche active'], ['zmk_peripheral', 'Liaison des moitiés']];

// Éditeur des écrans : un seul encart, les écrans côte à côte comme deux moniteurs.
// Un élément se glisse à la souris (aimanté à la grille du firmware : colonne = 6 px, ligne = 8 px),
// y compris d'un écran à l'autre ; Ctrl au lâcher = copie au lieu de déplacement.
// Clé d'un élément : 'img:<index>', 'x:<index>' (exemplaire supplémentaire d'une information,
// dans `extras`), une clé d'information (1er exemplaire, champ dédié du modèle) ou d'animation.
// Les animations gardent un état global dans le firmware : un seul exemplaire par écran.
// Tailles et bornes : les mêmes que l'éditeur de l'application de bureau (oled_editor/widget.py).
const OS = 3;                                 // zoom de l'aperçu
const OW = 32, OH = 128;                      // écran en pixels
let OSEL = null;                              // élément sélectionné : '<côté>|<clé>'
const OLABEL = {layer: 'LAYER', caps_lock: 'CAPS', wpm: 'WPM', rgb_mode: 'RGB :', kfm: '<KFM>',
  zmk_battery: 'BAT', zmk_output: 'BLE', zmk_layer: 'L0', zmk_peripheral: 'LINK',
  luna: 'luna', ocean_dream: '~~~~', bongo: 'bongo', crab: 'crab', katawajojo: 'kata'};
const OPAGES = {layer: 3, caps_lock: 3, rgb_mode: 4, wpm: 1, kfm: 1, zmk_battery: 2, zmk_output: 2, zmk_layer: 2, zmk_peripheral: 2};
const OCOLS = {zmk_battery: 4, zmk_output: 4, zmk_layer: 5, zmk_peripheral: 3};
const OANIM_H = {luna: 22, katawajojo: 22, ocean_dream: 128, bongo: 32, crab: 32};

const isAnim = kind => kind in OANIM_H;
const oledKeys = () => (firmware() === 'zmk' ? ZMK_WIDGETS : [...QMK_OVERLAYS, ...QMK_ANIMS]);
const oledName = kind => kind === 'img' ? 'Image' : oledKeys().find(([k]) => k === kind)?.[1] || kind;
const extrasOf = side => (P.oled[side].extras ||= []);
// Type d'un élément ('img', une clé d'information ou d'animation)
const oledKind = (side, key) => key.startsWith('img:') ? 'img' : key.startsWith('x:') ? extrasOf(side)[+key.slice(2)]?.kind : key;
// Objet qui porte col/line de l'élément (null pour une animation, dont seule la ligne est gardée)
function oledEntry(side, key) {
  const s = P.oled[side];
  if (key.startsWith('img:')) return s.images[+key.slice(4)];
  if (key.startsWith('x:')) return extrasOf(side)[+key.slice(2)];
  return isAnim(key) ? null : s[key];
}

// Taille [l, h] en pixels écran d'un élément ; img = l'entrée image pour 'img'.
function oledSize(kind, img) {
  if (kind === 'img') return [Math.max(1, img.natural_w), Math.max(1, img.natural_h)];
  if (isAnim(kind)) return [OW, OANIM_H[kind]];
  return [(OCOLS[kind] || OW / 6) * 6, (OPAGES[kind] || 1) * 8];
}

// Position aimantée et bornée (colonne, ligne) : l'élément reste dans l'écran.
function clampPos(kind, img, col, line) {
  const [w, h] = oledSize(kind, img);
  const maxCol = isAnim(kind) ? 0 : kind === 'img' || kind in OCOLS ? Math.floor((OW - w) / 6) : 4;
  const maxLine = Math.floor((OH - h) / 8);
  return [Math.max(0, Math.min(col, maxCol)), Math.max(0, Math.min(line, maxLine))];
}

// Éléments affichés sur un écran : [{key, kind, col, line, img?}]
function oledItems(side) {
  const s = P.oled[side], kinds = oledKeys().map(([k]) => k);
  const items = s.images.map((img, i) => ({key: 'img:' + i, kind: 'img', col: img.col, line: img.line, img}));
  for (const kind of kinds) {
    if (isAnim(kind)) { if (s[kind + '_enabled']) items.push({key: kind, kind, col: 0, line: s[kind + '_line']}); }
    else if (s[kind].enabled) items.push({key: kind, kind, col: s[kind].col, line: s[kind].line});
  }
  extrasOf(side).forEach((e, i) => { if (kinds.includes(e.kind)) items.push({key: 'x:' + i, kind: e.kind, col: e.col, line: e.line}); });
  return items;
}

function oledItemHtml(side, it) {
  const [w, h] = oledSize(it.kind, it.img), sel = OSEL === `${side}|${it.key}`;
  const style = `left:${it.col * 6 * OS}px;top:${it.line * 8 * OS}px;width:${w * OS}px;height:${h * OS}px`;
  let inner;
  if (it.img) {
    const info = IMG[it.img.image_path] || {};
    inner = info.preview ? `<img src="${info.preview}" draggable="false"${it.img.inverted ? ' style="filter:invert(1)"' : ''}>`
      : `<span class="${info.missing ? 'miss' : ''}">${info.missing ? 'image à renvoyer' : '…'}</span>`;
  } else inner = `<span>${esc(OLABEL[it.kind])}</span>`;
  const cls = ['oitem', it.img ? 'pic' : isAnim(it.kind) ? 'anim' : 'txt', sel ? 'sel' : ''].join(' ');
  return `<div class="${cls}" style="${style}" title="${esc(oledName(it.kind))} — glisser pour déplacer, Ctrl = copier"
    onpointerdown="oledGrab(event, '${side}', '${it.key}')">${inner}</div>`;
}

// Retire un élément d'un écran (sans redessiner). Le 1er exemplaire d'une information qui en a
// d'autres est remplacé par le suivant : le champ dédié du modèle reste le 1er exemplaire.
function removeEntry(side, key) {
  const s = P.oled[side];
  if (key.startsWith('img:')) s.images.splice(+key.slice(4), 1);
  else if (key.startsWith('x:')) extrasOf(side).splice(+key.slice(2), 1);
  else if (isAnim(key)) s[key + '_enabled'] = false;
  else {
    const j = extrasOf(side).findIndex(e => e.kind === key);
    if (j < 0) s[key].enabled = false;
    else {
      const [e] = extrasOf(side).splice(j, 1);
      Object.assign(s[key], {col: e.col, line: e.line}, 'show_peer' in s[key] ? {show_peer: e.show_peer} : {});
    }
  }
}

// Déplace (ou copie) un élément vers un écran à la position donnée ; from = null : ajout depuis la palette.
function oledPlace(from, key, to, col, line, copy) {
  const src = from && P.oled[from], dst = P.oled[to], kind = from ? oledKind(from, key) : key;
  if (kind === 'img') {
    const i = +key.slice(4);
    let img = src.images[i];
    if (copy) img = clone(img);
    else if (from !== to) src.images.splice(i, 1);
    [img.col, img.line] = clampPos(kind, img, col, line);
    if (copy || from !== to) dst.images.push(img);
    OSEL = `${to}|img:${dst.images.indexOf(img)}`;
  } else if (isAnim(kind)) {
    if (dst[kind + '_enabled'] && (from !== to || copy)) {
      toast(`« ${oledName(kind)} » est déjà sur l'écran ${to === 'left' ? 'gauche' : 'droit'} (une animation n'y est qu'une fois)`, 5000);
      renderOled();
      return;
    }
    if (src && !copy) src[kind + '_enabled'] = false;
    dst[kind + '_enabled'] = true;
    dst[kind + '_line'] = clampPos(kind, null, col, line)[1];
    OSEL = `${to}|${kind}`;
  } else {
    [col, line] = clampPos(kind, null, col, line);
    if (from === to && !copy) {
      Object.assign(oledEntry(from, key), {col, line});
      OSEL = `${to}|${key}`;
    } else {
      const peer = from ? !!oledEntry(from, key).show_peer : false;
      if (from && !copy) removeEntry(from, key);
      if (!dst[kind].enabled) {
        Object.assign(dst[kind], {enabled: true, col, line}, kind === 'zmk_battery' ? {show_peer: peer} : {});
        OSEL = `${to}|${kind}`;
      } else {
        extrasOf(to).push({kind, col, line, show_peer: peer});
        OSEL = `${to}|x:${extrasOf(to).length - 1}`;
      }
    }
  }
  save();
  renderOled();
}

// Remet les deux écrans à vide (valeurs d'un projet neuf) ; les réglages généraux restent.
function oledReset() {
  if (!confirm('Retirer tous les éléments (images, informations, animations) des deux écrans ?')) return;
  for (const side of ['left', 'right']) P.oled[side] = clone(META.default_project.oled[side]);
  OSEL = null;
  save();
  renderOled();
}

function oledRemove(side, key) {
  removeEntry(side, key);
  OSEL = null;
  save();
  renderOled();
}

function oledSetPos(side, key, field, value) {
  const kind = oledKind(side, key), s = P.oled[side];
  if (isAnim(kind)) s[kind + '_line'] = clampPos(kind, null, 0, field === 'line' ? value : s[kind + '_line'])[1];
  else {
    const cur = oledEntry(side, key), pos = {col: cur.col, line: cur.line, [field]: value};
    [cur.col, cur.line] = clampPos(kind, kind === 'img' ? cur : null, pos.col, pos.line);
  }
  save();
  renderOled();
}

// Réglage propre à un élément (image : inverted, layer ; batterie ZMK : show_peer)
function oledSetField(side, key, field, value) {
  oledEntry(side, key)[field] = value;
  save();
  renderOled();
}

// Glisser : un fantôme suit librement la souris (comme une fenêtre), un cadre montre où l'élément
// tombera sur l'écran survolé. Sans mouvement, c'est un simple clic qui sélectionne.
function oledGrab(ev, from, key) {
  if (ev.button !== 0) return;
  ev.preventDefault();
  ev.stopPropagation();
  const el = ev.currentTarget, r = el.getBoundingClientRect();
  const kind = from ? oledKind(from, key) : key;
  const img = kind === 'img' ? P.oled[from].images[+key.slice(4)] : null;
  const [w, h] = oledSize(kind, img);
  // depuis la palette, on « tient » l'élément par son coin haut-gauche
  const offX = from ? ev.clientX - r.left : 4, offY = from ? ev.clientY - r.top : 4;
  const x0 = ev.clientX, y0 = ev.clientY;
  let ghost = null, target = null;
  const hint = document.createElement('div');
  hint.className = 'odrop hidden';

  const move = e => {
    if (!ghost) {
      if (Math.hypot(e.clientX - x0, e.clientY - y0) < 4) return;
      ghost = (from ? el.cloneNode(true) : document.createElement('div'));
      if (!from) { ghost.className = 'oitem txt'; ghost.innerHTML = `<span>${esc(OLABEL[kind])}</span>`; }
      ghost.classList.add('oghost');
      ghost.style.width = w * OS + 'px';
      ghost.style.height = h * OS + 'px';
      document.body.appendChild(ghost);
    }
    ghost.style.left = e.clientX - offX + 'px';
    ghost.style.top = e.clientY - offY + 'px';
    ghost.classList.toggle('copy', !!from && e.ctrlKey);
    target = null;
    for (const scr of document.querySelectorAll('.oscreen')) {
      const sr = scr.getBoundingClientRect();
      if (e.clientX < sr.left || e.clientX > sr.right || e.clientY < sr.top || e.clientY > sr.bottom) continue;
      const [col, line] = clampPos(kind, img, Math.round((e.clientX - offX - sr.left) / (6 * OS)),
        Math.round((e.clientY - offY - sr.top) / (8 * OS)));
      target = {side: scr.dataset.side, col, line};
      if (hint.parentNode !== scr) scr.appendChild(hint);
      Object.assign(hint.style, {left: col * 6 * OS + 'px', top: line * 8 * OS + 'px', width: w * OS + 'px', height: h * OS + 'px'});
      hint.classList.remove('hidden');
    }
    if (!target) hint.classList.add('hidden');
  };
  const up = e => {
    document.removeEventListener('pointermove', move);
    document.removeEventListener('pointerup', up);
    ghost?.remove();
    hint.remove();
    if (!ghost) {   // clic
      if (from) { OSEL = `${from}|${key}`; renderOled(); }
      return;
    }
    if (target) oledPlace(from, key, target.side, target.col, target.line, !!from && e.ctrlKey);
  };
  document.addEventListener('pointermove', move);
  document.addEventListener('pointerup', up);
}

// Fichier image lâché depuis l'explorateur sur un écran : envoyé et posé à l'endroit du lâcher.
function oledFileDrop(ev, side) {
  ev.preventDefault();
  const file = ev.dataTransfer.files[0], r = ev.currentTarget.getBoundingClientRect();
  uploadImage(side, file, Math.round((ev.clientX - r.left) / (6 * OS)), Math.round((ev.clientY - r.top) / (8 * OS)));
}

function oledProps() {
  if (!OSEL) return '<p class="muted small">Cliquez un élément sur un écran pour le régler.</p>';
  const [side, key] = OSEL.split('|'), s = P.oled[side], kind = oledKind(side, key);
  const entry = kind && oledEntry(side, key);
  const on = kind && (isAnim(kind) ? s[kind + '_enabled'] : entry && (entry.enabled ?? true));
  if (!on) { OSEL = null; return oledProps(); }
  const img = kind === 'img' ? entry : null;
  const col = isAnim(kind) ? 0 : entry.col, line = isAnim(kind) ? s[kind + '_line'] : entry.line;
  const info = img ? IMG[img.image_path] || {} : {};
  const field = (f, v) => `oledSetField('${side}','${key}','${f}',${v})`;
  return `<div class="oprops"><b>${esc(oledName(kind))}</b> <span class="muted small">· écran ${side === 'left' ? 'gauche' : 'droit'}</span>
    ${img ? `<div class="small muted" title="${esc(img.image_path)}">${esc(imgName(img.image_path))}${info.frames > 1 ? ` · ${info.frames} images` : ''}
      ${info.missing ? `<span class="badge err">absente du serveur</span> <button class="btn small" onclick="resendImage('${side}',${key.slice(4)})">Renvoyer le fichier…</button>` : ''}</div>` : ''}
    <div class="row-inline">col <input type="number" min="0" max="4" value="${col}" ${isAnim(kind) ? 'disabled' : ''} onchange="oledSetPos('${side}','${key}','col',+this.value)">
      ligne <input type="number" min="0" max="15" value="${line}" onchange="oledSetPos('${side}','${key}','line',+this.value)"></div>
    ${img ? `<div class="row-inline"><label class="switch small"><input type="checkbox" ${img.inverted ? 'checked' : ''} onchange="${field('inverted', 'this.checked')}"> inversée</label>
      couche <input type="number" min="-1" max="9" value="${img.layer}" title="-1 = toutes les couches" onchange="${field('layer', '+this.value')}"></div>` : ''}
    ${kind === 'zmk_battery' ? `<label class="switch small"><input type="checkbox" ${entry.show_peer ? 'checked' : ''} onchange="${field('show_peer', 'this.checked')}"> + batterie de l'autre moitié</label>` : ''}
    <div class="row-inline"><button class="btn small danger" onclick="oledRemove('${side}','${key}')" title="touche Suppr">Supprimer</button></div></div>`;
}

function renderOled() {
  const el = $('mode-oled');
  if (!kb()) { el.innerHTML = '<section class="card muted">Choisissez d\'abord un clavier (onglet Matériel).</section>'; return; }
  if (!hasOled()) { el.innerHTML = '<section class="card muted">Ce clavier n\'a pas d\'écran OLED activé (onglet Matériel).</section>'; return; }
  const fw = firmware(), o = P.oled, zmk = fw === 'zmk';
  const builtin = zmk && o.use_builtin_screen;
  const sides = P.keyboard.oled_sides;
  let html = `<section class="card"><h1>Écrans OLED</h1>
    ${setting('Anti-marquage', `<label class="switch"><input type="checkbox" ${o.anti_burnin ? 'checked' : ''} onchange="setOled('anti_burnin', this.checked)"> inversion + décalage d'un pixel toutes les 60 s</label>`)}
    ${setting('Mise en veille', `<label class="switch"><input type="checkbox" ${o.sleep_enabled ? 'checked' : ''} onchange="setOled('sleep_enabled', this.checked)"> éteindre écran et LEDs après</label>
      <input type="number" min="10" max="3600" value="${o.sleep_timeout_s}" onchange="setOled('sleep_timeout_s', +this.value)"> s`)}
    ${zmk ? setting('Écran ZMK d\'origine', `<label class="switch"><input type="checkbox" ${o.use_builtin_screen ? 'checked' : ''} onchange="setOled('use_builtin_screen', this.checked)"> couche + batterie + sortie (ignore la disposition ci-dessous)</label>`) : ''}
    ${zmk ? setting('Pourcentage batterie', `<label class="switch"><input type="checkbox" ${o.show_battery_percentage ? 'checked' : ''} onchange="setOled('show_battery_percentage', this.checked)"> afficher le % en texte</label>`) : ''}
    </section>`;
  if (!builtin) {
    for (const side of sides) for (const img of o[side].images) if (!IMG[img.image_path]) loadImage(img.image_path);
    const screens = sides.map(side => `<div class="ocol"><div class="small muted">${side === 'left' ? 'Gauche' : 'Droite'}</div>
      <div class="oscreen" data-side="${side}" style="width:${OW * OS}px;height:${OH * OS}px"
        onpointerdown="if (event.target === this) { OSEL = null; renderOled(); }"
        ondragover="event.preventDefault()" ondrop="oledFileDrop(event, '${side}')">${oledItems(side).map(it => oledItemHtml(side, it)).join('')}</div></div>`).join('');
    const palette = oledKeys().map(([key, label]) =>
      `<span class="chip ochip" onpointerdown="oledGrab(event, null, '${key}')" title="glisser sur un écran pour l'ajouter">${esc(label)}</span>`).join('');
    const lost = sides.flatMap(sd => o[sd].images.map((img, i) => ({sd, i, img}))).filter(x => IMG[x.img.image_path]?.missing);
    const lostHtml = lost.length ? `<div class="warn-item warn">${lost.length > 1 ? 'Ces images du projet ne sont' : 'Cette image du projet n\'est'} pas sur le serveur
      (projet créé sur un autre ordinateur ou avec l'application de bureau) : la compilation ${lost.length > 1 ? 'les ' : 'l\''}ignore.
      Renvoyez le fichier (la position et les réglages sont gardés) ou retirez-${lost.length > 1 ? 'les' : 'la'}.
      ${lost.map(x => `<div class="row-inline"><span class="mono small" title="${esc(x.img.image_path)}">${esc(imgName(x.img.image_path))}</span>
        <span class="muted small">écran ${x.sd === 'left' ? 'gauche' : 'droit'}</span>
        <button class="btn small" onclick="resendImage('${x.sd}',${x.i})">Renvoyer le fichier…</button>
        <button class="btn small danger" onclick="oledRemove('${x.sd}','img:${x.i}')">Retirer</button></div>`).join('')}</div>` : '';
    html += `<section class="card"><h1>Disposition</h1>
      <p class="lead">Glissez un élément de la liste sur un écran pour l'ajouter, autant de fois que vous voulez
      (les animations : une fois par écran). Sur les écrans : clic = sélection,
      <b>Suppr</b> = supprimer, glisser = déplacer, y compris d'un écran à l'autre (<b>Ctrl</b> au lâcher = copier).
      Ils s'aimantent à la grille du firmware : colonne de 6 px, ligne de 8 px. L'aperçu est indicatif : le texte réel dépend de la police du firmware.</p>${lostHtml}
      <div class="odesk"><div class="oscreens">${screens}</div>
        <div class="opanel"><h3>${zmk ? 'Widgets ZMK' : 'Informations et animations'}</h3><div class="chips">${palette}</div>
          <div class="row-inline"><button class="btn small" onclick="$('up-oled').click()">+ image</button>
            <button class="btn small danger" onclick="oledReset()" title="retirer tous les éléments des deux écrans">Vider les écrans</button>
            <span class="muted small">ou glissez un fichier image sur un écran</span>
            <input type="file" id="up-oled" class="hidden" accept="image/*" onchange="uploadImage('${sides[0]}', this.files[0]); this.value=''">
            <input type="file" id="re-oled" class="hidden" accept="image/*" onchange="replaceImage(this.files[0]); this.value=''"></div>
          <h3>Élément sélectionné</h3>${oledProps()}</div></div></section>`;
  }
  el.innerHTML = html;
}

// ─────────────────────────────────────────────────────────── Options avancées ──

// [clé, type, libellé, firmware(s), unité, min, max]
const ADV = [
  ['adv.section.keyboard_behavior', [
    ['nkro_enabled', 'bool', 'adv.nkro', 'qmk,zmk'],
    ['hid_indicators_enabled', 'bool', 'adv.hid_indicators', 'zmk'],
    ['usb_boot_protocol', 'bool', 'adv.usb_boot', 'zmk'],
    ['auto_shift_enabled', 'bool', 'adv.auto_shift', 'qmk'],
    ['auto_shift_timeout_ms', 'int', 'adv.auto_shift_timeout', 'qmk', 'ms', 50, 1000]]],
  ['adv.section.bluetooth', [['ble_passkey_entry', 'bool', 'adv.ble_passkey', 'zmk']]],
  ['adv.section.energy', [
    ['deep_sleep_timeout_min', 'int', 'adv.deep_sleep_timeout', 'zmk', 'min', 0, 240],
    ['battery_report_interval_s', 'int', 'adv.battery_report_interval', 'zmk', 's', 10, 3600],
    ['soft_off_enabled', 'bool', 'adv.soft_off', 'zmk']]],
  ['adv.section.ergo', [
    ['tap_dance_enabled', 'bool', 'adv.tap_dance', 'qmk,zmk'],
    ['sticky_key_enabled', 'bool', 'adv.sticky_key', 'qmk,zmk'],
    ['tapping_term_ms', 'int', 'adv.tapping_term', 'qmk', 'ms', 50, 1000],
    ['combo_term_ms', 'int', 'adv.combo_term', 'qmk', 'ms', 10, 500],
    ['permissive_hold', 'bool', 'adv.permissive_hold', 'qmk']]],
  ['adv.section.rgb_advanced', [
    ['rgb_hue_start', 'int', 'adv.rgb_hue_start', 'zmk', '°', 0, 359],
    ['rgb_on_start', 'bool', 'adv.rgb_on_start', 'zmk'],
    ['rgb_auto_off_idle', 'bool', 'adv.rgb_auto_off_idle', 'zmk'],
    ['rgb_auto_off_usb', 'bool', 'adv.rgb_auto_off_usb', 'zmk']]],
  ['adv.section.pointing', [
    ['pointing_enabled', 'bool', 'adv.pointing', 'zmk'],
    ['pointing_smooth_scroll', 'bool', 'adv.pointing_smooth_scroll', 'zmk']]],
  ['adv.section.mouse_keys', [
    ['mousekey_enabled', 'bool', 'adv.mousekey_enabled', 'qmk'],
    ['mousekey_delay_ms', 'int', 'adv.mousekey_delay', 'qmk', 'ms', 1, 1000],
    ['mousekey_interval_ms', 'int', 'adv.mousekey_interval', 'qmk', 'ms', 1, 1000],
    ['mousekey_max_speed', 'int', 'adv.mousekey_max_speed', 'qmk', '', 1, 50]]],
];

let KEYMAP_REPORT = '';

function renderAdvanced() {
  const fw = firmware(), a = P.advanced;
  const km = P.keyboard.custom_keymap;
  const kmStatus = !km ? tr('adv.keymap.no_file')
    : Array.isArray(km.zmk_layers) ? tr('adv.keymap.loaded_zmk', {n: km.zmk_layers.length})
    : tr('adv.keymap.loaded_vial', {n: (km.layout || []).length});
  let html = `<section class="card"><h1>${tr('adv.section.keymap_import')}</h1><p class="lead">${esc(tr('adv.keymap.help'))}</p>
    <div class="row-inline" title="${esc(tr('tip.adv_use_custom_keymap'))}"><label class="switch"><input type="checkbox" ${P.keyboard.use_custom_keymap ? 'checked' : ''}
      onchange="P.keyboard.use_custom_keymap=this.checked; save(); renderAdvanced()"> ${esc(tr('adv.keymap.use'))}</label></div>
    <div class="row-inline"><button class="btn" onclick="$('km-file').click()" title="${esc(tr('tip.adv_keymap_import_btn'))}">${esc(tr('adv.keymap.import_btn'))}</button>
      <span class="muted">${esc(kmStatus)}</span>
      <input type="file" id="km-file" class="hidden" accept=".vil,.json,.keymap" onchange="importKeymap(this.files[0]); this.value=''"></div>
    ${KEYMAP_REPORT}</section>
    <section class="card"><h1>${tr('adv.section.identification')}</h1>
    ${setting(esc(tr('adv.keyboard_name.label')), `<input size="30" value="${esc(a.keyboard_name)}" placeholder="${esc(tr('adv.keyboard_name.placeholder'))}" onchange="P.advanced.keyboard_name=this.value; save()" ${fw === 'zmk' ? '' : 'disabled'}>`,
      esc(tr('adv.keyboard_name.help')), fw !== 'zmk', tr('tip.adv_keyboard_name'))}</section>`;
  for (const [section, fields] of ADV) {
    html += `<section class="card"><h1>${esc(tr(section))}</h1>` + fields.map(([key, type, label, fws, unit, min, max]) => {
      const ok = fws.split(',').includes(fw);
      const only = ok ? '' : tr('adv.tooltip.firmware_only', {firmware: fws.toUpperCase()});
      const ctl = type === 'bool'
        ? `<label class="switch"><input type="checkbox" ${a[key] ? 'checked' : ''} ${ok ? '' : 'disabled'} onchange="P.advanced.${key}=this.checked; save()"> activé</label>`
        : `<input type="number" min="${min}" max="${max}" value="${a[key]}" ${ok ? '' : 'disabled'} onchange="P.advanced.${key}=Math.max(${min}, Math.min(${max}, +this.value)); save(); this.value=P.advanced.${key}"> ${unit}`;
      return setting(esc(tr(label)), ctl, only, !ok, tr('tip.adv_' + key));
    }).join('') + '</section>';
  }
  $('mode-advanced').innerHTML = html;
}

async function importKeymap(file) {
  if (!file) return;
  try {
    const r = await api('api/keymap/import', {body: {filename: file.name, content: await file.text(), firmware: firmware()}});
    if (r.cross_format && !confirm(r.format === 'zmk' ? tr('adv.keymap.cross_zmk_to_qmk') : tr('adv.keymap.cross_vial_to_zmk'))) return;
    P.keyboard.custom_keymap = r.keymap;
    P.keyboard.use_custom_keymap = true;
    save();
    const rep = r.report;
    KEYMAP_REPORT = rep.dropped.length || rep.warnings.length
      ? `<div class="warn-item warn">Conversion partielle : ${rep.converted} touche(s) converties, ${rep.dropped.length} abandonnée(s).
         ${rep.dropped.slice(0, 30).map(d => `<br>· couche ${d.layer}, position ${d.position} : <code>${esc(d.source)}</code> — ${esc(d.reason)}`).join('')}
         ${rep.warnings.map(w => `<br>⚠ ${esc(w)}`).join('')}</div>`
      : `<div class="warn-item info">« ${esc(file.name)} » importé.</div>`;
    renderAdvanced();
  } catch (e) {
    toast(tr('adv.keymap.error_title') + ' : ' + e.message, 6000);
  }
}

// ─────────────────────────────────────────────────────────── Build ──

function renderBuild() {
  const k = kb(), fw = firmware(), s = STATUS;
  const ready = s && (fw === 'zmk' ? s.zmk.sdk && s.zmk.west : s.qmk.vial_qmk && s.qmk.gcc);
  const flash = fw === 'zmk'
    ? `<ol class="small"><li>Brancher une moitié en USB, double-appui rapide sur reset : un lecteur <b>NICENANO</b> apparaît.</li>
       <li>Si vous changez de firmware : y copier d'abord <code>…settings_reset.uf2</code> (sinon ZMK Studio garde l'ancien keymap et l'état RGB), puis recommencer.</li>
       <li>Copier <code>…_left.uf2</code> sur la moitié gauche, <code>…_right.uf2</code> sur la droite.</li></ol>`
    : `<ol class="small"><li>Maintenir BOOT (ou double-appui sur reset) en branchant : un lecteur <b>RPI-RP2</b> apparaît.</li>
       <li>Y copier le <code>.uf2</code> ; le clavier redémarre seul. Pour un split, flasher les deux moitiés.</li>
       <li>Le keymap vit dans Vial : rechargez votre <code>.vil</code> si les touches ne tapent rien.</li></ol>`;
  $('mode-build').innerHTML = `<section class="card"><h1>Compiler le firmware</h1>
    <p class="lead">${k ? `<b>${esc(k.display_name)}</b> · ${esc(mcu()?.display_name || '')} · firmware <b>${fw.toUpperCase()}</b>` : 'Choisissez d\'abord un clavier.'}
    — la compilation tourne sur le serveur (quelques minutes ; la première compilation ZMK télécharge ~500 Mo).</p>
    ${s && fw === 'qmk' && !s.qmk.vial_qmk ? `<div class="warn-item warn">Vial-QMK n'est pas encore téléchargé sur le serveur (~1 Go avec ses sous-modules).
      <button class="btn small" onclick="setupVialQmk()">Télécharger Vial-QMK</button></div>` : ''}
    ${s && fw === 'qmk' && !s.qmk.gcc ? '<div class="warn-item error">arm-none-eabi-gcc manque sur le serveur : <code>sudo apt install gcc-arm-none-eabi</code></div>' : ''}
    ${s && fw === 'zmk' && !ready ? '<div class="warn-item error">Zephyr SDK ou west manque sur le serveur : lancer <code>scripts/setup_zmk.sh</code>.</div>' : ''}
    <div class="row-inline">
      <button class="btn primary" id="btn-build" onclick="startBuild()" ${k && ready && !JOB ? '' : 'disabled'}>🔨 Compiler</button>
      <button class="btn" id="btn-cancel" onclick="cancelJob()" ${JOB ? '' : 'disabled'}>■ Annuler</button>
      <span id="job-state" class="muted"></span></div>
    <div class="progress"><div id="job-bar" style="width:0"></div></div>
    <div id="job-files"></div>
    <details class="log" open><summary class="small muted">Journal</summary><pre id="job-log" class="logview"></pre></details></section>
    <section class="card"><h1>Flasher</h1>${flash}</section>`;
  if (LASTJOB) paintJob(LASTJOB);
}

async function startBuild() {
  try {
    const r = await api('api/build', {body: {project: P}});
    $('job-log').textContent = '';
    pollJob(r.job.id);
  } catch (e) {
    toast('Compilation refusée : ' + e.message, 6000);
  }
}

async function setupVialQmk() {
  try {
    const r = await api('api/setup/vial-qmk', {body: {}});
    showMode('build');
    pollJob(r.job.id);
  } catch (e) {
    toast(e.message, 6000);
  }
}

async function cancelJob() {
  if (JOB) await api(`api/jobs/${JOB.id}/cancel`, {body: {}}).catch(() => {});
}

async function pollJob(id) {
  if (JOB && JOB.id === id) return;
  JOB = {id, since: 0};
  JOBLOG = [];
  LASTJOB = null;
  if (MODE === 'build') renderBuild();
  while (JOB && JOB.id === id) {
    let j;
    try {
      j = await api(`api/jobs/${id}?since=${JOB.since}`);
    } catch (e) {
      toast(e.message, 6000);
      break;
    }
    JOB.since = j.log_next;
    JOBLOG.push(...j.log);
    if (JOBLOG.length > 5000) JOBLOG.splice(0, JOBLOG.length - 5000);
    LASTJOB = j;
    paintJob(j);
    if (j.state !== 'running') break;
    await new Promise(r => setTimeout(r, 1000));
  }
  JOB = null;
  refreshStatus();
  if (MODE === 'build') renderBuild();
}

function paintJob(j) {
  const pill = $('pill-build');
  pill.textContent = j.state === 'running' ? `${j.label || 'tâche'} · ${j.progress}%` : j.state === 'done' ? 'compilation réussie' : j.state === 'error' ? 'échec' : 'aucune compilation';
  pill.className = 'pill ' + ({running: 'busy', done: 'ok', error: 'err'}[j.state] || '');
  if (MODE !== 'build' || !$('job-log')) return;
  $('job-bar').style.width = (j.progress || 0) + '%';
  $('job-state').textContent = j.state === 'running' ? `${j.label} — ${j.progress}%` : j.state === 'done' ? '✅ terminé' : j.state === 'error' ? '❌ échec' : '';
  const log = $('job-log');
  const lines = JOBLOG;
  if (lines.length) {
    const atEnd = log.scrollTop + log.clientHeight >= log.scrollHeight - 30;
    log.innerHTML = lines.map(l => `<span class="${/error|erreur|\[ERREUR\]/i.test(l) ? 'le' : /warn/i.test(l) ? 'lw' : ''}">${esc(l)}</span>`).join('\n');
    if (atEnd) log.scrollTop = log.scrollHeight;
  }
  const files = (j.files || []).map(f => `<a class="btn small primary" href="api/jobs/${j.id}/files/${encodeURIComponent(f.name)}" download>⬇ ${esc(f.name)}</a>
    <span class="muted small">${(f.size / 1024).toFixed(0)} Ko${j.info?.flash_bytes ? ` / ${(j.info.flash_bytes / 1024).toFixed(0)} Ko de flash` : ''}</span>`).join(' ');
  $('job-files').innerHTML = (j.error ? `<div class="warn-item error" style="white-space:pre-wrap">${esc(j.error)}</div>` : '') +
    (files ? `<div class="row-inline">${files}</div>` : '');
}

// ─────────────────────────────────────────────────────────── démarrage ──

async function init() {
  try {
    META = await api('api/meta?lang=' + (navigator.language || 'fr').slice(0, 2));
  } catch (e) {
    document.body.innerHTML = `<p style="padding:20px">Serveur injoignable : ${esc(e.message)}</p>`;
    return;
  }
  let stored = null;
  try { stored = JSON.parse(localStorage.getItem(STORE) || 'null'); } catch (e) { /* projet corrompu : on repart à neuf */ }
  P = stored ? (await api('api/project/normalize', {body: {project: stored}}).catch(() => null))?.project : null;
  P = P || clone(META.default_project);
  try { $('project-name').value = localStorage.getItem(STORE_NAME) || ''; } catch (e) { /* ignore */ }
  renderSide();
  showMode(kb() ? MODE : 'hardware');
  refreshStatus();
}

document.addEventListener('keydown', e => {
  if (MODE !== 'oled' || !OSEL || e.target.closest('input, select, textarea')) return;
  if (e.key === 'Delete' || e.key === 'Backspace') { e.preventDefault(); oledRemove(...OSEL.split('|')); }
  else if (e.key === 'Escape') { OSEL = null; renderOled(); }
});

init();
