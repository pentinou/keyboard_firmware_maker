#!/bin/bash

# Service de réveil (Wake-on-LAN) : seulement si une adresse MAC est configurée.
# Diffusion vers le réseau du serveur de calcul (x.y.z.255) quand son adresse est une IPv4.
_kfm_reveil() {
    if [ -n "${mac:-}" ]; then
        broadcast=$(echo "$upstream" | sed -nE 's#^[a-z]+://([0-9]+\.[0-9]+\.[0-9]+)\.[0-9]+.*#\1.255#p')
        case "$broadcast" in 127.*) broadcast="" ;; esac
        ynh_config_add_systemd --service="$app-reveil" --template="wake.service"
        systemctl restart "$app-reveil"
    else
        ynh_config_remove_systemd "$app-reveil"
    fi
}

_kfm_setup() {
    # URL du bouton de réveil (POST), derrière le SSO comme le reste de la tuile
    # (calculée ici : $path n'est défini qu'une fois les helpers chargés)
    path_reveil="${path%/}/__reveiller__"
    cp ../conf/wake.py "$install_dir/wake.py"
    ynh_config_add --template="pc_eteint.html" --destination="$install_dir/pc_eteint.html"
    chown -R "$app:www-data" "$install_dir"
    chmod -R g+rX "$install_dir"
    ynh_config_add_nginx
    _kfm_reveil
}
