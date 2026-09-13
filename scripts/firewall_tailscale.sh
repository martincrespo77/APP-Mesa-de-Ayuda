#!/usr/bin/env bash
# scripts/firewall_tailscale.sh
# Configura reglas de firewall con iptables para restringir el acceso a la app
# en el puerto 8000 exclusivamente al celular vía Tailscale (100.109.79.72).

set -euo pipefail

PHONE_IP="100.109.79.72"
APP_PORT="8000"

check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo "Este script requiere privilegios de root (usa sudo)." >&2
        exit 1
    fi
}

apply_rules() {
    check_root
    echo "Aplicando reglas de firewall para permitir únicamente a $PHONE_IP en el puerto $APP_PORT..."

    # 1. Asegurar que la cadena DOCKER-USER exista (Docker la crea al iniciar)
    if ! iptables -L DOCKER-USER -n >/dev/null 2>&1; then
        echo "Creando cadena DOCKER-USER (en caso de que Docker aún no la haya inicializado)..."
        iptables -N DOCKER-USER 2>/dev/null || true
    fi

    # Limpiar reglas previas de APP_MESA si ya existían para evitar duplicados
    clear_rules_silent

    # --- Reglas en DOCKER-USER (tráfico enrutado a los contenedores) ---
    iptables -I DOCKER-USER 1 -m conntrack --ctstate RELATED,ESTABLISHED -m comment --comment "APP_MESA_CONNTRACK" -j ACCEPT
    iptables -I DOCKER-USER 2 -p tcp --dport "$APP_PORT" -s "$PHONE_IP" -m comment --comment "APP_MESA_PHONE" -j ACCEPT
    iptables -I DOCKER-USER 3 -p tcp --dport "$APP_PORT" -s 127.0.0.1 -m comment --comment "APP_MESA_LOCAL" -j ACCEPT
    iptables -A DOCKER-USER -p tcp --dport "$APP_PORT" -m comment --comment "APP_MESA_DROP" -j DROP

    # --- Reglas en INPUT (tráfico directo al host / docker-proxy) ---
    iptables -I INPUT 1 -m conntrack --ctstate RELATED,ESTABLISHED -m comment --comment "APP_MESA_CONNTRACK" -j ACCEPT
    iptables -I INPUT 2 -p tcp --dport "$APP_PORT" -s "$PHONE_IP" -m comment --comment "APP_MESA_PHONE" -j ACCEPT
    iptables -I INPUT 3 -p tcp --dport "$APP_PORT" -s 127.0.0.1 -m comment --comment "APP_MESA_LOCAL" -j ACCEPT
    iptables -I INPUT 4 -p tcp --dport "$APP_PORT" -m comment --comment "APP_MESA_DROP" -j DROP

    echo "Reglas de firewall aplicadas exitosamente."
}

clear_rules_silent() {
    # Eliminar reglas asociadas a APP_MESA en DOCKER-USER e INPUT
    for chain in DOCKER-USER INPUT; do
        if iptables -L "$chain" -n >/dev/null 2>&1; then
            while iptables -D "$chain" -m comment --comment "APP_MESA_DROP" -p tcp --dport "$APP_PORT" -j DROP 2>/dev/null; do :; done
            while iptables -D "$chain" -m comment --comment "APP_MESA_PHONE" -p tcp --dport "$APP_PORT" -s "$PHONE_IP" -j ACCEPT 2>/dev/null; do :; done
            while iptables -D "$chain" -m comment --comment "APP_MESA_LOCAL" -p tcp --dport "$APP_PORT" -s 127.0.0.1 -j ACCEPT 2>/dev/null; do :; done
            while iptables -D "$chain" -m comment --comment "APP_MESA_CONNTRACK" -m conntrack --ctstate RELATED,ESTABLISHED -j ACCEPT 2>/dev/null; do :; done
        fi
    done
}

clear_rules() {
    check_root
    echo "Limpiando reglas de firewall para el puerto $APP_PORT..."
    clear_rules_silent
    echo "Reglas removidas."
}

status_rules() {
    check_root
    echo "=== Cadena DOCKER-USER ==="
    iptables -L DOCKER-USER -n -v --line-numbers 2>/dev/null || echo "No existe DOCKER-USER"
    echo ""
    echo "=== Cadena INPUT (Puerto $APP_PORT) ==="
    iptables -L INPUT -n -v --line-numbers | grep -E "($APP_PORT|Chain|target)" || true
}

case "${1:-status}" in
    apply)
        apply_rules
        status_rules
        ;;
    clear)
        clear_rules
        status_rules
        ;;
    status)
        status_rules
        ;;
    *)
        echo "Uso: $0 {apply|clear|status}"
        exit 1
        ;;
esac
