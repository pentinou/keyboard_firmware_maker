# modules/rgb_editor/effects.py
"""Définitions des types d'effets RGB disponibles.

Module pur Python sans dépendance Qt.
"""
from __future__ import annotations

from typing import NamedTuple


class EffectDef(NamedTuple):
    id: str            # stocké dans RgbEffect.type (rétro-compat : "static" conservé)
    name: str          # affiché dans le combo
    description: str   # affiché sous le combo
    preview: str       # type d'animation de preview
    custom: bool = False  # True = génère du code firmware


EFFECT_TYPES: tuple[EffectDef, ...] = (
    EffectDef("static",                    "Solid Color",                "Couleur unique uniforme sur tout le clavier.",                                        "solid"),
    EffectDef("alphas_mods",               "Alphas / Mods",              "Touches alpha d'une couleur, modificateurs d'une autre.",                            "two_zone"),
    EffectDef("gradient_up_down",          "Gradient Haut / Bas",        "Dégradé vertical continu de haut en bas.",                                           "gradient_v"),
    EffectDef("gradient_left_right",       "Gradient Gauche / Droite",   "Dégradé horizontal continu de gauche à droite.",                                     "gradient_h"),
    EffectDef("breathing",                 "Breathing",                  "Toutes les touches pulsent lentement entre couleur et noir.",                         "breathing"),
    EffectDef("band_sat",                  "Band Saturation",            "Bande de saturation défilant vers le bas.",                                           "band_v"),
    EffectDef("band_val",                  "Band Value",                 "Bande de luminosité défilant vers le bas.",                                           "band_v"),
    EffectDef("band_pinwheel_sat",         "Band Pinwheel Sat",          "Bande de saturation tournant en roue depuis le centre.",                              "pinwheel"),
    EffectDef("band_pinwheel_val",         "Band Pinwheel Val",          "Bande de luminosité tournant en roue depuis le centre.",                              "pinwheel"),
    EffectDef("band_spiral_sat",           "Band Spiral Sat",            "Spirale de saturation s'enroulant depuis le centre.",                                 "spiral"),
    EffectDef("band_spiral_val",           "Band Spiral Val",            "Spirale de luminosité s'enroulant depuis le centre.",                                 "spiral"),
    EffectDef("cycle_all",                 "Cycle All",                  "Toutes les touches changent de teinte simultanément — arc-en-ciel global.",           "cycle_all"),
    EffectDef("cycle_left_right",          "Cycle Gauche → Droite",      "Vague arc-en-ciel balayant de gauche à droite.",                                      "cycle_lr"),
    EffectDef("cycle_up_down",             "Cycle Haut → Bas",           "Vague arc-en-ciel balayant de haut en bas.",                                          "cycle_ud"),
    EffectDef("cycle_out_in",              "Cycle Extérieur → Centre",   "Vague arc-en-ciel entrant des bords vers le centre.",                                 "cycle_out_in"),
    EffectDef("cycle_out_in_dual",         "Cycle Ext→Centre (dual)",    "Double vague arc-en-ciel symétrique depuis chaque demi-clavier.",                     "cycle_out_in"),
    EffectDef("rainbow_moving_chevron",    "Rainbow Chevron",            "Chevron arc-en-ciel se déplaçant de gauche à droite.",                                "cycle_lr"),
    EffectDef("cycle_pinwheel",            "Cycle Pinwheel",             "Arc-en-ciel tournant en roue depuis le centre.",                                      "pinwheel"),
    EffectDef("cycle_spiral",              "Cycle Spiral",               "Arc-en-ciel en spirale s'éloignant du centre.",                                       "spiral"),
    EffectDef("dual_beacon",               "Dual Beacon",                "Deux phares tournants avec couleurs opposées.",                                        "pinwheel"),
    EffectDef("rainbow_beacon",            "Rainbow Beacon",             "Phare arc-en-ciel tournant lentement.",                                               "pinwheel"),
    EffectDef("rainbow_pinwheels",         "Rainbow Pinwheels",          "Plusieurs tourbillons arc-en-ciel simultanés.",                                        "pinwheel"),
    EffectDef("raindrops",                 "Raindrops",                  "Touches colorées aléatoirement comme des gouttes de pluie.",                           "raindrops"),
    EffectDef("jellybean_raindrops",       "Jellybean Raindrops",        "Pluie de couleurs bonbon pastel aléatoires.",                                          "raindrops"),
    EffectDef("hue_breathing",             "Hue Breathing",              "Toutes les touches pulsent en faisant évoluer la teinte.",                            "breathing"),
    EffectDef("hue_pendulum",              "Hue Pendulum",               "Teinte oscillant en pendule de gauche à droite.",                                      "cycle_lr"),
    EffectDef("hue_wave",                  "Hue Wave",                   "Vague de teinte traversant le clavier de gauche à droite.",                           "cycle_lr"),
    EffectDef("pixel_fractal",             "Pixel Fractal",              "Motif fractal coloré évoluant en continu.",                                            "raindrops"),
    EffectDef("pixel_flow",                "Pixel Flow",                 "Flux de pixels colorés défilant sur le clavier.",                                      "cycle_lr"),
    EffectDef("pixel_rain",                "Pixel Rain",                 "Pluie de pixels colorés tombant sur le clavier.",                                      "raindrops"),
    EffectDef("typing_heatmap",            "Typing Heatmap",             "Carte de chaleur montrant les touches les plus pressées.",                             "heatmap"),
    EffectDef("digital_rain",              "Digital Rain",               "Pluie de chiffres style Matrix — vert tombant.",                                       "raindrops"),
    EffectDef("solid_reactive_simple",     "Solid Reactive Simple",      "La touche pressée s'illumine brièvement en couleur primaire.",                        "reactive"),
    EffectDef("solid_reactive",            "Solid Reactive",             "La touche pressée illumine ses voisines en fondu.",                                    "reactive"),
    EffectDef("solid_reactive_wide",       "Solid Reactive Wide",        "Grande zone lumineuse autour de la touche pressée.",                                   "reactive"),
    EffectDef("solid_reactive_multiwide",  "Solid Reactive Multiwide",   "Multiples grandes zones lumineuses simultanées.",                                      "reactive"),
    EffectDef("solid_reactive_cross",      "Solid Reactive Cross",       "Croix lumineuse s'allumant à la pression.",                                            "reactive"),
    EffectDef("solid_reactive_multicross", "Solid Reactive Multicross",  "Multiples croix lumineuses simultanées.",                                              "reactive"),
    EffectDef("solid_reactive_nexus",      "Solid Reactive Nexus",       "Anneau lumineux se propageant depuis la touche pressée.",                              "reactive"),
    EffectDef("solid_reactive_multinexus", "Solid Reactive Multinexus",  "Multiples anneaux lumineux simultanés.",                                               "reactive"),
    EffectDef("splash",                    "Splash",                     "Éclaboussure arc-en-ciel depuis la touche pressée.",                                   "reactive"),
    EffectDef("multisplash",               "Multisplash",                "Multiples éclaboussures arc-en-ciel simultanées.",                                     "reactive"),
    EffectDef("solid_splash",              "Solid Splash",               "Éclaboussure couleur solide depuis la touche pressée.",                                "reactive"),
    EffectDef("solid_multisplash",         "Solid Multisplash",          "Multiples éclaboussures couleur solide simultanées.",                                  "reactive"),
    EffectDef("ripple",                    "Ripple (custom)",            "Ondulation circulaire précise au keystroke — code custom généré dans le firmware.",    "ripple", custom=True),
)
