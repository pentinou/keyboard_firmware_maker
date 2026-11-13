// Onglet RGB : effet au démarrage, effets disponibles, couleurs par touche, effets personnalisés.
'use strict';

let PAINT = '#ff0000';          // couleur du pinceau « par touche »
let CE_SEL = 0;                 // effet personnalisé affiché
let PICK = null;                // {track, field: 'keys_fixed' | 'trigger_keys'} : sélection de touches en cours
let SIM = null;                 // aperçu animé {hits: [{id, t0}], start, raf}

function rgbEffect() {
  if (!P.rgb.effects.length) {
    P.rgb.effects.push({type: 'static', color_primary: '#FFFFFF', color_secondary: '#888888', fade_ms: 500, speed: 128, brightness: 128, trigger_key: null});
  }
  return P.rgb.effects[0];
}

function renderRgb() {
  stopSim();
  const el = $('mode-rgb');
  if (!kb()) { el.innerHTML = '<section class="card muted">Choisissez d\'abord un clavier (onglet Matériel).</section>'; return; }
  if (!hasRgb()) { el.innerHTML = '<section class="card muted">Ce clavier n\'a pas de LEDs RGB activées (onglet Matériel).</section>'; return; }
  const zmk = firmware() === 'zmk';
  if (zmk) {
    el.innerHTML = `<section class="card"><h1>RGB (ZMK)</h1><p class="lead">ZMK pilote l'underglow avec ses propres effets, réglés au clavier
      (touches <code>&amp;rgb_ug</code>). Les réglages de démarrage sont dans <b>Options avancées → RGB avancé</b>.
      Les effets par touche et personnalisés sont propres à QMK.</p></section>`;
    return;
  }
  const e = rgbEffect();
  const types = META.effects.types;
  const groups = [['ambient', 'Ambiants'], ['reactive', 'Réactifs (appui touche)']];
  const opts = groups.map(([cat, label]) => `<optgroup label="${label}">${types.filter(t => t.category === cat).map(t =>
    `<option value="${t.id}" ${t.id === e.type ? 'selected' : ''}>${esc(t.name)}</option>`).join('')}</optgroup>`).join('');
  const desc = types.find(t => t.id === e.type)?.description || '';
  const enabled = new Set(P.rgb.enabled_effects.length ? P.rgb.enabled_effects : types.filter(t => t.id !== 'static').map(t => t.id));
  el.innerHTML = `<section class="card"><h1><span class="num">1</span> Effet au démarrage</h1>
    <p class="lead">Utilisé seulement au premier démarrage (EEPROM vierge) : ensuite le clavier reprend le dernier effet choisi au clavier (touches RGB_MOD, RGB_HUI…).</p>
    ${setting('Effet', `<select onchange="rgbEffect().type=this.value; save(); renderRgb()">${opts}</select><span class="muted small">${esc(desc)}</span>`)}
    ${setting('Couleur', `<input type="color" value="${e.color_primary}" onchange="rgbEffect().color_primary=this.value.toUpperCase(); save()">`)}
    ${setting('Luminosité', `<input type="range" min="0" max="255" value="${e.brightness}" oninput="rgbEffect().brightness=+this.value; this.nextElementSibling.textContent=this.value" onchange="save()"><span>${e.brightness}</span>`,
      'plafonnée par le clavier (Sofle : 200)')}
    ${setting('Vitesse', `<input type="range" min="0" max="255" value="${e.speed}" oninput="rgbEffect().speed=+this.value; this.nextElementSibling.textContent=this.value" onchange="save()"><span>${e.speed}</span>`)}
    </section>
    <section class="card"><h1><span class="num">2</span> Effets disponibles au clavier</h1>
    <p class="lead">Ceux que RGB_MOD fait défiler. En retirer allège le firmware.</p>
    <div class="row-inline"><button class="btn small" onclick="P.rgb.enabled_effects=[]; save(); renderRgb()">tout cocher</button></div>
    <div class="effgrid">${types.filter(t => t.id !== 'static').map(t => `<label class="switch small" title="${esc(t.description)}">
      <input type="checkbox" ${enabled.has(t.id) ? 'checked' : ''} onchange="toggleEnabled('${t.id}', this.checked)"> ${esc(t.name)}</label>`).join('')}</div>
    </section>
    <section class="card"><h1><span class="num">3</span> Couleurs par touche</h1>
    <p class="lead">Posées par-dessus l'effet actif. Clic = peindre, clic droit = effacer.</p>
    <div class="row-inline">Pinceau <input type="color" value="${PAINT}" onchange="PAINT=this.value">
      <button class="btn small" onclick="P.rgb.per_key={}; save(); renderRgb()">tout effacer</button></div>
    ${kbView({prefix: 'pk', onKey: 'paintKey', color: id => P.rgb.per_key[id] || ''})}
    </section>
    <section class="card" id="ce-card"></section>`;
  renderCustomEffects();
}

function toggleEnabled(id, on) {
  const all = META.effects.types.filter(t => t.id !== 'static').map(t => t.id);
  const set = new Set(P.rgb.enabled_effects.length ? P.rgb.enabled_effects : all);
  on ? set.add(id) : set.delete(id);
  P.rgb.enabled_effects = set.size === all.length ? [] : all.filter(x => set.has(x));
  save();
}

function paintKey(id, ev) {
  if (ev.type === 'contextmenu') delete P.rgb.per_key[id];
  else P.rgb.per_key[id] = PAINT.toUpperCase();
  save();
  $('pk-' + id).style.background = P.rgb.per_key[id] || '';
}

// ─────────────────────────────────────────────────── effets personnalisés ──

const ce = () => P.rgb.custom_effects[CE_SEL];

function renderCustomEffects() {
  const card = $('ce-card');
  if (!card) return;
  const list = P.rgb.custom_effects;
  if (CE_SEL >= list.length) CE_SEL = Math.max(0, list.length - 1);
  const e = ce();
  let html = `<h1><span class="num">4</span> Effets personnalisés</h1>
    <p class="lead">Animations par pistes, ajoutées après les effets QMK (dernières positions de RGB_MOD).
    Une piste cible la touche pressée, des touches <b>autour</b> d'elle, ou des touches <b>fixes</b> ; chaque étape a une couleur, une durée de maintien et un fondu.</p>
    <div class="chips">${list.map((x, i) => `<button class="chip ${i === CE_SEL ? 'on' : ''}" onclick="CE_SEL=${i}; PICK=null; renderCustomEffects()">${esc(x.name)}</button>`).join('')}
      <button class="chip" onclick="addEffect()">+ nouvel effet</button></div>`;
  if (e) {
    const reactive = e.effect_type === 'reactive';
    html += `<div class="row-inline">Nom <input value="${esc(e.name)}" maxlength="30" onchange="ce().name=this.value; save(); renderCustomEffects()">
      <select onchange="ce().effect_type=this.value; save(); renderCustomEffects()">
        <option value="reactive" ${reactive ? 'selected' : ''}>réactif (à l'appui)</option>
        <option value="ambient" ${!reactive ? 'selected' : ''}>ambiant (en boucle)</option></select>
      ${e.custom_code ? '<span class="badge warn" title="code C édité dans l\'application de bureau : les pistes ne sont pas utilisées">code C manuel</span>' : ''}
      <button class="btn small danger" onclick="if(confirm('Supprimer cet effet ?')){P.rgb.custom_effects.splice(CE_SEL,1); save(); renderCustomEffects()}">supprimer</button></div>`;
    html += e.tracks.map((t, ti) => trackHtml(e, t, ti)).join('');
    html += `<div class="row-inline"><button class="btn small" onclick="ce().tracks.push({name:'Piste ${e.tracks.length + 1}',enabled:true,target_mode:'default',trigger_keys:[],keys_offset:[],keys_fixed:[],steps:[{time_ms:0,color:'#FFFFFF',hold_ms:0,fade_ms:500,color_to:'#000000'}]}); save(); renderCustomEffects()">+ piste</button></div>`;
    html += `<h3>${PICK ? `Sélection : ${PICK.field === 'trigger_keys' ? 'touches déclencheuses' : 'touches éclairées'} de « ${esc(e.tracks[PICK.track].name)} »` : 'Aperçu'}</h3>
      <div class="row-inline">${PICK
        ? `<span class="muted small">Cliquez les touches à ajouter / retirer.</span><button class="btn small primary" onclick="PICK=null; renderCustomEffects()">terminé</button>`
        : reactive ? '<span class="muted small">Cliquez une touche pour simuler un appui (couleurs avant mise à l\'échelle par la luminosité).</span>'
          : '<button class="btn small" onclick="startSim()">▶ lancer</button><button class="btn small" onclick="stopSim(true)">■</button>'}</div>
      ${kbView({prefix: 'ck', onKey: 'ceKey', cls: ceKeyClass})}`;
  }
  card.innerHTML = html;
}

function trackHtml(e, t, ti) {
  const reactive = e.effect_type === 'reactive';
  const modes = [['default', 'la touche pressée'], ['relative', 'autour de la touche pressée'], ['fixed', 'des touches fixes']]
    .filter(([m]) => reactive || m === 'fixed' || m === t.target_mode);
  const steps = t.steps.map((s, si) => `<tr>
    <td><input type="number" min="0" max="60000" step="50" value="${s.time_ms}" onchange="setStep(${ti},${si},'time_ms',+this.value)"></td>
    <td><input type="color" value="${s.color}" onchange="setStep(${ti},${si},'color',this.value.toUpperCase())"></td>
    <td><input type="number" min="0" max="60000" step="50" value="${s.hold_ms || 0}" onchange="setStep(${ti},${si},'hold_ms',+this.value)"></td>
    <td><input type="number" min="0" max="60000" step="50" value="${s.fade_ms || 0}" onchange="setStep(${ti},${si},'fade_ms',+this.value)"></td>
    <td><input type="color" value="${s.color_to || '#000000'}" ${s.fade_ms ? '' : 'disabled'} onchange="setStep(${ti},${si},'color_to',this.value.toUpperCase())"></td>
    <td><button class="btn small danger" onclick="setStep(${ti},${si},'delete')">✕</button></td></tr>`).join('');
  let target = '';
  if (t.target_mode === 'relative') target = `<div class="row-inline small">Touches éclairées autour de la touche pressée (●) : ${offsetGrid(ti, t)}</div>`;
  if (t.target_mode === 'fixed') target = `<div class="row-inline small">${t.keys_fixed.length} touche(s) <button class="btn small ${PICK?.track === ti && PICK.field === 'keys_fixed' ? 'on' : ''}" onclick="startPick(${ti},'keys_fixed')">choisir sur le clavier</button></div>`;
  const trig = reactive ? `<div class="row-inline small">Déclenchée par : ${t.trigger_keys.length ? `${t.trigger_keys.length} touche(s) (${esc(t.trigger_keys.join(', '))})` : 'toutes les touches'}
    <button class="btn small ${PICK?.track === ti && PICK.field === 'trigger_keys' ? 'on' : ''}" onclick="startPick(${ti},'trigger_keys')">choisir</button>
    ${t.trigger_keys.length ? `<button class="btn small" onclick="ce().tracks[${ti}].trigger_keys=[]; save(); renderCustomEffects()">toutes</button>` : ''}</div>` : '';
  return `<div class="track ${t.enabled ? '' : 'off'}"><div class="row-inline">
    <label class="switch"><input type="checkbox" ${t.enabled ? 'checked' : ''} onchange="ce().tracks[${ti}].enabled=this.checked; save(); renderCustomEffects()"></label>
    <input value="${esc(t.name)}" size="16" onchange="ce().tracks[${ti}].name=this.value; save()">
    éclaire <select onchange="ce().tracks[${ti}].target_mode=this.value; save(); renderCustomEffects()">${modes.map(([m, l]) => `<option value="${m}" ${m === t.target_mode ? 'selected' : ''}>${l}</option>`).join('')}</select>
    <button class="btn small danger" onclick="ce().tracks.splice(${ti},1); PICK=null; save(); renderCustomEffects()">supprimer la piste</button></div>
    ${target}${trig}
    <table class="steps"><tr><th>début (ms)</th><th>couleur</th><th>maintien (ms)</th><th>fondu (ms)</th><th>vers</th><th></th></tr>${steps}</table>
    <button class="btn small" onclick="addStep(${ti})">+ étape</button></div>`;
}

function offsetGrid(ti, t) {
  const on = new Set(t.keys_offset.map(o => `${o.dr},${o.dc}`));
  let cells = '';
  for (let dr = -3; dr <= 3; dr++) for (let dc = -3; dc <= 3; dc++) {
    cells += dr === 0 && dc === 0 ? '<i class="c" title="touche pressée"></i>'
      : `<i class="${on.has(`${dr},${dc}`) ? 'on' : ''}" title="rangée ${dr > 0 ? '+' : ''}${dr}, colonne ${dc > 0 ? '+' : ''}${dc}" onclick="toggleOffset(${ti},${dr},${dc})"></i>`;
  }
  return `<span class="offgrid">${cells}</span>`;
}

function toggleOffset(ti, dr, dc) {
  const t = ce().tracks[ti];
  const i = t.keys_offset.findIndex(o => o.dr === dr && o.dc === dc);
  i >= 0 ? t.keys_offset.splice(i, 1) : t.keys_offset.push({dr, dc});
  save();
  renderCustomEffects();
}

function addEffect() {
  P.rgb.custom_effects.push({name: `Effet ${P.rgb.custom_effects.length + 1}`, effect_type: 'reactive', tracks: [
    {name: 'Touche pressée', enabled: true, target_mode: 'default', trigger_keys: [], keys_offset: [], keys_fixed: [],
     steps: [{time_ms: 0, color: '#FFFFFF', hold_ms: 0, fade_ms: 800, color_to: '#000000'}]}]});
  CE_SEL = P.rgb.custom_effects.length - 1;
  save();
  renderCustomEffects();
}

function addStep(ti) {
  const steps = ce().tracks[ti].steps, last = steps.at(-1);
  const end = last ? last.time_ms + (last.hold_ms || 0) + (last.fade_ms || 0) : 0;
  steps.push({time_ms: end, color: last?.color_to || last?.color || '#FFFFFF', hold_ms: 0, fade_ms: 500, color_to: '#000000'});
  save();
  renderCustomEffects();
}

function setStep(ti, si, field, value) {
  const steps = ce().tracks[ti].steps;
  if (field === 'delete') steps.splice(si, 1);
  else steps[si][field] = value;
  save();
  renderCustomEffects();
}

function startPick(ti, field) {
  stopSim();
  PICK = PICK && PICK.track === ti && PICK.field === field ? null : {track: ti, field};
  renderCustomEffects();
}

function ceKeyClass(id) {
  const e = ce();
  if (PICK) {
    const t = e.tracks[PICK.track];
    return (t[PICK.field].includes(id) ? 'mark' : '') + (PICK.field === 'keys_fixed' && t.trigger_keys.includes(id) ? ' trig' : '');
  }
  return e.tracks.some(t => t.enabled && t.trigger_keys.includes(id)) ? 'trig' : '';
}

function ceKey(id, ev) {
  if (ev.type === 'contextmenu' && !PICK) return;
  if (PICK) {
    const list = ce().tracks[PICK.track][PICK.field];
    const i = list.indexOf(id);
    i >= 0 ? list.splice(i, 1) : list.push(id);
    save();
        renderCustomEffects();
    return;
  }
  if (ce().effect_type === 'reactive') {
    if (!SIM) startSim();
    SIM.hits.push({id, t0: performance.now()});
    if (SIM.hits.length > 8) SIM.hits.shift();   // LED_HITS_TO_REMEMBER
  }
}

// ── Aperçu : même calcul que le code C généré (rgb_matrix_user.inc.j2 + _build_timeline_effects) ──

function compileEffect(e) {
  const hex = h => [1, 3, 5].map(i => parseInt((h || '#000000').slice(i, i + 2), 16) || 0);
  const tracks = e.tracks.filter(t => t.enabled);
  let total = 0;
  for (const t of tracks) {
    const l = t.steps.at(-1);
    if (l) total = Math.max(total, l.time_ms + (l.hold_ms || 0) + (l.fade_ms || 0));
  }
  total = Math.max(total, 100);
  return {total, loop: total + 500, reactive: e.effect_type === 'reactive', tracks: tracks.map(t => {
    const sorted = [...t.steps].sort((a, b) => a.time_ms - b.time_ms);
    return {...t, steps: sorted.map((s, i) => {
      const start = hex(s.color), end = s.fade_ms > 0 && s.color_to ? hex(s.color_to) : start;
      const explicit = s.time_ms + (s.hold_ms || 0) + (s.fade_ms || 0);
      const endMs = explicit <= s.time_ms ? Math.max(i + 1 < sorted.length ? sorted[i + 1].time_ms : total, s.time_ms + 1) : explicit;
      return {time: s.time_ms, hold: s.hold_ms || 0, fade: s.fade_ms || 0, holdEnd: s.time_ms + (s.hold_ms || 0), end: endMs, start, to: end};
    })};
  })};
}

function evalSteps(steps, t) {
  const lerp = (a, b, p) => a.map((x, i) => Math.trunc(x + (b[i] - x) * p / 255));
  for (let i = 0; i < steps.length; i++) {
    const s = steps[i];
    if (i === 0 && s.time > 0 && t < s.time) return null;   // pas encore actif
    if (t >= s.end) continue;
    if (s.hold > 0 && s.fade > 0) return t >= s.holdEnd ? lerp(s.start, s.to, Math.trunc((t - s.holdEnd) * 255 / s.fade)) : s.start;
    if (s.fade > 0) return lerp(s.start, s.to, t >= s.time ? Math.trunc((t - s.time) * 255 / s.fade) : 0);
    return s.start;
  }
  return null;
}

function matrixPos(id) {
  const m = id.match(/^([LR])_r(\d+)_c(\d+)$/), k = kb();
  return [+m[2] + (m[1] === 'R' && k.split ? k.matrix.rows : 0), +m[3]];
}

function simColors(fx, now) {
  const ids = kbPanels().flatMap(p => p.keys.map(x => x.id));
  const hits = SIM.hits.map(h => ({id: h.id, t: Math.min(65535, Math.trunc(now - h.t0)), pos: matrixPos(h.id)}));
  const colors = {};
  for (const id of ids) {
    let c = null;
    const pos = matrixPos(id);
    for (const t of fx.tracks) {
      const trig = h => !t.trigger_keys.length || t.trigger_keys.includes(h.id);
      if (t.target_mode === 'fixed') {
        if (!t.keys_fixed.includes(id)) continue;
        let tt;
        if (!fx.reactive) tt = Math.min((now - SIM.start) % fx.loop, fx.total);
        else if (t.trigger_keys.length) { tt = fx.total; for (const h of hits) if (trig(h) && h.t < tt) tt = h.t; }
        else tt = hits.length ? Math.min(hits.at(-1).t, fx.total) : fx.total;
        c = evalSteps(t.steps, tt) || c;
      } else if (fx.reactive) {
        for (const h of hits) {
          if (!trig(h) || h.t > fx.total) continue;
          const match = t.target_mode === 'default' ? h.id === id
            : t.keys_offset.some(o => h.pos[0] + o.dr === pos[0] && h.pos[1] + o.dc === pos[1]);
          if (match) c = evalSteps(t.steps, h.t) || c;
        }
      }
    }
    colors[id] = c;
  }
  return colors;
}

function startSim() {
  stopSim();
  SIM = {hits: [], start: performance.now()};
  const frame = () => {
    if (!SIM || !ce()) return;
    // recompilé à chaque image : une étape modifiée pendant l'aperçu est prise en compte tout de suite
    const colors = simColors(compileEffect(ce()), performance.now());
    for (const [id, c] of Object.entries(colors)) {
      const el = $('ck-' + id);
      if (el) el.style.background = c ? `rgb(${c[0]},${c[1]},${c[2]})` : '';
    }
    SIM.raf = requestAnimationFrame(frame);
  };
  frame();
}

function stopSim(repaint = false) {
  if (SIM) cancelAnimationFrame(SIM.raf);
  SIM = null;
  if (repaint) renderCustomEffects();
}
