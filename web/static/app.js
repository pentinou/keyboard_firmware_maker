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
    const missing = allImages().length;
    toast(`Projet « ${file.name} » ouvert` + (missing ? ` — ${missing} image(s) OLED à vérifier dans l'onglet OLED` : ''));
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

async function loadImage(path) {
  if (IMG[path]) return;
  IMG[path] = {loading: true};
  try {
    IMG[path] = await api('api/oled/image?path=' + encodeURIComponent(path));
  } catch (e) {
    IMG[path] = {missing: true};
  }
  if (MODE === 'oled') renderOled();
}

async function uploadImage(side, file) {
  if (!file) return;
  try {
    const info = await api('api/oled/image?name=' + encodeURIComponent(file.name), {method: 'POST', body: file});
    IMG[info.image_path] = info;
    P.oled[side].images.push({image_path: info.image_path, natural_w: info.natural_w, natural_h: info.natural_h,
      col: 0, line: 0, inverted: false, layer: -1});
    save();
    renderOled();
    if (info.frames > 1) toast(`GIF animé : ${info.frames} images`);
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

function setImage(side, i, field, value) {
  if (field === 'delete') P.oled[side].images.splice(i, 1);
  else P.oled[side].images[i][field] = value;
  save();
  renderOled();
}

const QMK_OVERLAYS = [['layer', 'Couche active'], ['caps_lock', 'Verr. Maj'], ['wpm', 'WPM (mots/min)'], ['rgb_mode', 'Mode RGB'], ['kfm', 'Logo <KFM>']];
const QMK_ANIMS = [['luna', 'Luna (chien)'], ['ocean_dream', 'Ocean Dream'], ['bongo', 'Bongo Cat'], ['crab', 'Crabe'], ['katawajojo', 'KatawaJojo']];
const ZMK_WIDGETS = [['zmk_battery', 'Batterie'], ['zmk_output', 'Sortie (USB/BLE)'], ['zmk_layer', 'Couche active'], ['zmk_peripheral', 'Liaison des moitiés']];

function renderOled() {
  const el = $('mode-oled');
  if (!kb()) { el.innerHTML = '<section class="card muted">Choisissez d\'abord un clavier (onglet Matériel).</section>'; return; }
  if (!hasOled()) { el.innerHTML = '<section class="card muted">Ce clavier n\'a pas d\'écran OLED activé (onglet Matériel).</section>'; return; }
  const fw = firmware(), o = P.oled, zmk = fw === 'zmk';
  const builtin = zmk && o.use_builtin_screen;
  let html = `<section class="card"><h1>Écrans OLED</h1>
    <p class="lead">Écran 32×128 vertical. Position en <b>colonnes</b> (0-4, un caractère = 6 px) et <b>lignes</b> (0-15, une ligne = 8 px).
    L'aperçu est indicatif : le texte réel dépend de la police du firmware.</p>
    ${setting('Anti-marquage', `<label class="switch"><input type="checkbox" ${o.anti_burnin ? 'checked' : ''} onchange="setOled('anti_burnin', this.checked)"> inversion + décalage d'un pixel toutes les 60 s</label>`)}
    ${setting('Mise en veille', `<label class="switch"><input type="checkbox" ${o.sleep_enabled ? 'checked' : ''} onchange="setOled('sleep_enabled', this.checked)"> éteindre écran et LEDs après</label>
      <input type="number" min="10" max="3600" value="${o.sleep_timeout_s}" onchange="setOled('sleep_timeout_s', +this.value)"> s`)}
    ${zmk ? setting('Écran ZMK d\'origine', `<label class="switch"><input type="checkbox" ${o.use_builtin_screen ? 'checked' : ''} onchange="setOled('use_builtin_screen', this.checked)"> couche + batterie + sortie (ignore les réglages ci-dessous)</label>`) : ''}
    ${zmk ? setting('Pourcentage batterie', `<label class="switch"><input type="checkbox" ${o.show_battery_percentage ? 'checked' : ''} onchange="setOled('show_battery_percentage', this.checked)"> afficher le % en texte</label>`) : ''}
    </section>`;
  if (!builtin) {
    for (const side of P.keyboard.oled_sides) {
      const s = o[side];
      for (const img of s.images) if (!IMG[img.image_path]) loadImage(img.image_path);
      const imgs = s.images.map((img, i) => {
        const info = IMG[img.image_path] || {};
        return `<div class="imgrow">${info.preview ? `<img src="${info.preview}">` : `<span class="badge ${info.missing ? 'err' : ''}">${info.missing ? 'à renvoyer' : '…'}</span>`}
          <span class="small muted" title="${esc(img.image_path)}">${esc(img.image_path.split('/').pop())}${info.frames > 1 ? ` · ${info.frames} images` : ''}</span>
          col <input type="number" min="0" max="4" value="${img.col}" onchange="setImage('${side}',${i},'col',+this.value)">
          ligne <input type="number" min="0" max="15" value="${img.line}" onchange="setImage('${side}',${i},'line',+this.value)">
          <label class="switch small"><input type="checkbox" ${img.inverted ? 'checked' : ''} onchange="setImage('${side}',${i},'inverted',this.checked)"> inversée</label>
          couche <input type="number" min="-1" max="9" value="${img.layer}" title="-1 = toutes les couches" onchange="setImage('${side}',${i},'layer',+this.value)">
          <button class="btn small danger" onclick="setImage('${side}',${i},'delete')">✕</button></div>`;
      }).join('');
      const items = zmk ? ZMK_WIDGETS : QMK_OVERLAYS;
      const ovl = items.map(([key, label]) => `<label class="switch"><input type="checkbox" ${s[key].enabled ? 'checked' : ''} onchange="setOled('${side}.${key}.enabled', this.checked)"> ${label}</label>
        <span>col <input type="number" min="0" max="4" value="${s[key].col}" onchange="setOled('${side}.${key}.col', +this.value)"></span>
        <span>ligne <input type="number" min="0" max="15" value="${s[key].line}" onchange="setOled('${side}.${key}.line', +this.value)"></span>
        <span>${key === 'zmk_battery' ? `<label class="switch small"><input type="checkbox" ${s[key].show_peer ? 'checked' : ''} onchange="setOled('${side}.zmk_battery.show_peer', this.checked)"> + l'autre moitié</label>` : ''}</span>`).join('');
      const anims = zmk ? '' : '<h3>Animations</h3><div class="ovl">' + QMK_ANIMS.map(([key, label]) => `<label class="switch"><input type="checkbox" ${s[key + '_enabled'] ? 'checked' : ''} onchange="setOled('${side}.${key}_enabled', this.checked)"> ${label}</label>
        <span>ligne <input type="number" min="0" max="15" value="${s[key + '_line']}" onchange="setOled('${side}.${key}_line', +this.value)"></span><span></span><span></span>`).join('') + '</div>';
      html += `<section class="card"><h1>Écran ${side === 'left' ? 'gauche' : 'droit'}</h1><div class="oledwrap">
        <canvas class="oled" id="oled-${side}" width="32" height="128" style="width:96px;height:384px"></canvas>
        <div><h3>Images</h3>${imgs || '<p class="muted small">aucune image</p>'}
          <div class="row-inline"><button class="btn small" onclick="$('up-${side}').click()">+ ajouter une image</button>
          <span class="muted small">PNG, JPG, GIF animé… convertie en noir et blanc 1 bit</span>
          <input type="file" id="up-${side}" class="hidden" accept="image/*" onchange="uploadImage('${side}', this.files[0]); this.value=''"></div>
          <h3>${zmk ? 'Widgets ZMK' : 'Informations'}</h3><div class="ovl">${ovl}</div>${anims}</div></div></section>`;
    }
  }
  el.innerHTML = html;
  if (!builtin) for (const side of P.keyboard.oled_sides) drawOled(side);
}

function drawOled(side) {
  const cv = $('oled-' + side);
  if (!cv) return;
  const ctx = cv.getContext('2d'), s = P.oled[side], zmk = firmware() === 'zmk';
  ctx.fillStyle = '#000';
  ctx.fillRect(0, 0, 32, 128);
  for (const img of s.images) {
    const info = IMG[img.image_path];
    if (!info?.preview) continue;
    const im = new Image();
    im.onload = () => {
      ctx.save();
      if (img.inverted) ctx.filter = 'invert(1)';
      ctx.drawImage(im, img.col * 6, img.line * 8);
      ctx.restore();
    };
    im.src = info.preview;
  }
  ctx.fillStyle = '#fff';
  ctx.font = '7px monospace';
  ctx.textBaseline = 'top';
  const labels = zmk
    ? {zmk_battery: 'BAT', zmk_output: 'BLE', zmk_layer: 'L0', zmk_peripheral: 'LINK'}
    : {layer: 'LAYER', caps_lock: 'CAPS', wpm: 'WPM', rgb_mode: 'RGB :', kfm: '<KFM>'};
  for (const [key, text] of Object.entries(labels)) {
    if (s[key].enabled) ctx.fillText(text, s[key].col * 6, s[key].line * 8);
  }
  if (!zmk) {
    ctx.strokeStyle = '#fff';
    for (const [key, h] of [['luna', 3], ['bongo', 4], ['crab', 4], ['katawajojo', 3]]) {
      if (s[key + '_enabled']) { ctx.strokeRect(1.5, s[key + '_line'] * 8 + .5, 29, h * 8 - 1); ctx.fillText(key.slice(0, 4), 3, s[key + '_line'] * 8 + 2); }
    }
    if (s.ocean_dream_enabled) ctx.fillText('~~~~', 4, 60);
  }
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

init();
