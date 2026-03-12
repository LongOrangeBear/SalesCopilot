# Деплой Asterisk на чистый VPS

Пошаговая инструкция для разворачивания Asterisk-прокси SalesCopilot на чистом Ubuntu 24.04 VPS.

**Минимальные требования:** 1 vCPU, 1 ГБ RAM, 10 ГБ диска. Рекомендуется: 2+ vCPU, 2+ ГБ RAM.

---

## 1. Swap (если RAM < 4 ГБ)

```bash
fallocate -l 2G /swapfile
chmod 600 /swapfile
mkswap /swapfile
swapon /swapfile
echo '/swapfile none swap sw 0 0' >> /etc/fstab
```

---

## 2. Установка Asterisk

```bash
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y asterisk
```

Проверка:

```bash
asterisk -V
# Asterisk 20.x.x
systemctl status asterisk
# Active: active (running)
```

---

## 3. Отключение chan_sip (устаревший модуль)

```bash
echo 'noload = chan_sip.so' >> /etc/asterisk/modules.conf
asterisk -rx 'module unload chan_sip.so'
```

---

## 4. Конфигурация PJSIP

Заменить `/etc/asterisk/pjsip.conf`:

```ini
; === SalesCopilot Asterisk PJSIP Config ===

; UDP Transport
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060
external_media_address=EXTERNAL_IP        ; <-- заменить на внешний IP сервера
external_signaling_address=EXTERNAL_IP    ; <-- заменить на внешний IP сервера
local_net=10.0.0.0/8
local_net=172.16.0.0/12
local_net=192.168.0.0/16

; TCP Transport (для клиентов за VPN/NAT)
[transport-tcp]
type=transport
protocol=tcp
bind=0.0.0.0:5060
external_media_address=EXTERNAL_IP        ; <-- заменить на внешний IP сервера
external_signaling_address=EXTERNAL_IP    ; <-- заменить на внешний IP сервера
local_net=10.0.0.0/8
local_net=172.16.0.0/12
local_net=192.168.0.0/16

; === Аккаунт: Manager (ext 100) ===
[manager]
type=endpoint
context=internal
disallow=all
allow=ulaw
allow=alaw
auth=manager-auth
aors=manager
direct_media=no                           ; Звук ВСЕГДА через Asterisk (для перехвата)
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[manager-auth]
type=auth
auth_type=userpass
username=manager
password=MANAGER_PASSWORD                 ; <-- заменить на надёжный пароль

[manager]
type=aor
max_contacts=5
remove_existing=yes

; === Аккаунт: Client (ext 200) ===
[client]
type=endpoint
context=internal
disallow=all
allow=ulaw
allow=alaw
auth=client-auth
aors=client
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[client-auth]
type=auth
auth_type=userpass
username=client
password=CLIENT_PASSWORD                  ; <-- заменить на надёжный пароль

[client]
type=aor
max_contacts=5
remove_existing=yes
```

**Ключевые параметры:**

| Параметр | Зачем |
|---|---|
| `direct_media=no` | Весь звук идет через Asterisk -- иначе мы не сможем перехватить аудиопоток |
| `rtp_symmetric=yes` | RTP ответы идут на тот же порт, откуда пришли -- решает проблемы NAT |
| `force_rport=yes` | Asterisk использует реальный IP/порт клиента вместо того, что указан в SIP-заголовке |
| `rewrite_contact=yes` | Перезаписывает Contact-заголовок реальным адресом -- без этого возвратные пакеты уходят "в никуда" |
| `external_media_address` | Внешний IP для RTP-пакетов -- без этого клиент за NAT не получит аудио |

---

## 5. Dialplan

Заменить `/etc/asterisk/extensions.conf`:

```ini
; === SalesCopilot Dialplan ===

[general]
static=yes
writeprotect=no

[internal]
; Manager: ext 100
exten => 100,1,NoOp(Incoming call to Manager)
 same => n,Set(MONITOR_FILENAME=/var/spool/asterisk/monitor/${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}-${CALLERID(num)}-to-100)
 same => n,MixMonitor(${MONITOR_FILENAME}.wav,r)
 same => n,Dial(PJSIP/manager,30,t)
 same => n,Hangup()

; Client: ext 200
exten => 200,1,NoOp(Incoming call to Client)
 same => n,Set(MONITOR_FILENAME=/var/spool/asterisk/monitor/${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}-${CALLERID(num)}-to-200)
 same => n,MixMonitor(${MONITOR_FILENAME}.wav,r)
 same => n,Dial(PJSIP/client,30,t)
 same => n,Hangup()

; Echo test: ext 600 (говоришь -- слышишь себя)
exten => 600,1,NoOp(Echo Test)
 same => n,Answer()
 same => n,Echo()
 same => n,Hangup()
```

**MixMonitor** -- записывает звонок в WAV. Параметр `r` записывает поток в формате, совместимом с дальнейшей обработкой. Записи хранятся в `/var/spool/asterisk/monitor/`.

---

## 6. Директория для записей

```bash
mkdir -p /var/spool/asterisk/monitor
chown asterisk:asterisk /var/spool/asterisk/monitor
```

---

## 7. Логирование (для отладки)

Заменить `/etc/asterisk/logger.conf`:

```ini
[general]
[logfiles]
console => notice,warning,error,verbose,debug
messages.log => notice,warning,error,verbose,debug
```

---

## 8. Применение конфигурации

```bash
# Перезагрузить всю конфигурацию Asterisk
asterisk -rx 'core reload'

# Или перезапустить сервис полностью
systemctl restart asterisk
```

Проверка:

```bash
# Транспорты (должно быть UDP + TCP)
asterisk -rx 'pjsip show transports'

# Эндпоинты (должно быть manager + client)
asterisk -rx 'pjsip show endpoints'

# SIP порт (должен слушать на 5060)
ss -lnp | grep 5060
```

---

## 9. Firewall (UFW)

```bash
apt-get install -y ufw

# Разрешить нужные порты ДО включения (иначе потеряешь SSH!)
ufw allow 22/tcp comment 'SSH'
ufw allow 80/tcp comment 'HTTP'
ufw allow 443/tcp comment 'HTTPS'
ufw allow 5060/udp comment 'SIP UDP'
ufw allow 5060/tcp comment 'SIP TCP'
ufw allow 10000:20000/udp comment 'RTP media'

# Включить
echo 'y' | ufw enable
ufw status
```

> **ВНИМАНИЕ:** Всегда добавляй `ufw allow 22/tcp` ПЕРЕД `ufw enable`, иначе потеряешь SSH-доступ.

---

## 10. Проверка

```bash
# 1. Asterisk работает
systemctl status asterisk

# 2. Порт слушает
ss -ulnp | grep 5060

# 3. Эндпоинты загружены
asterisk -rx 'pjsip show endpoints'

# 4. Зарегистрированные устройства (после подключения софтфона)
asterisk -rx 'pjsip show contacts'

# 5. Активные звонки
asterisk -rx 'core show channels'

# 6. Логи в реальном времени
tail -f /var/log/asterisk/messages.log

# 7. Интерактивная консоль Asterisk
asterisk -rvvv
```

---

## 11. Подключение софтфона (Zoiper)

Скачать: [zoiper.com](https://www.zoiper.com/en/voip-softphone/download/current)

Настройки аккаунта:

| Поле | Значение |
|---|---|
| Domain | IP-адрес сервера |
| Username | manager (или client) |
| Password | пароль из pjsip.conf |
| Transport | UDP (или TCP если за VPN) |

**Отключить STUN** в настройках Zoiper (Advanced -> STUN) -- наш Asterisk сам решает NAT через `rtp_symmetric` и `force_rport`.

Тест:
- Набрать **600** -- эхо-тест (слышишь свой голос = аудио работает)
- С второго устройства набрать **100** или **200** -- звонок между аккаунтами

---

## Быстрый деплой одной командой

```bash
#!/bin/bash
# deploy_asterisk.sh -- запускать от root на чистом Ubuntu 24.04
# Использование: ./deploy_asterisk.sh <EXTERNAL_IP> <MANAGER_PASS> <CLIENT_PASS>

set -e

EXTERNAL_IP=${1:?'Usage: ./deploy_asterisk.sh <EXTERNAL_IP> <MANAGER_PASS> <CLIENT_PASS>'}
MANAGER_PASS=${2:?'Manager password required'}
CLIENT_PASS=${3:?'Client password required'}

echo "[1/7] Swap..."
if [ ! -f /swapfile ]; then
    fallocate -l 2G /swapfile && chmod 600 /swapfile
    mkswap /swapfile && swapon /swapfile
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
fi

echo "[2/7] Asterisk..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq asterisk ufw

echo "[3/7] Disable chan_sip..."
echo 'noload = chan_sip.so' >> /etc/asterisk/modules.conf

echo "[4/7] PJSIP config..."
cat > /etc/asterisk/pjsip.conf << EOF
[transport-udp]
type=transport
protocol=udp
bind=0.0.0.0:5060
external_media_address=${EXTERNAL_IP}
external_signaling_address=${EXTERNAL_IP}
local_net=10.0.0.0/8
local_net=172.16.0.0/12
local_net=192.168.0.0/16

[transport-tcp]
type=transport
protocol=tcp
bind=0.0.0.0:5060
external_media_address=${EXTERNAL_IP}
external_signaling_address=${EXTERNAL_IP}
local_net=10.0.0.0/8
local_net=172.16.0.0/12
local_net=192.168.0.0/16

[manager]
type=endpoint
context=internal
disallow=all
allow=ulaw
allow=alaw
auth=manager-auth
aors=manager
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[manager-auth]
type=auth
auth_type=userpass
username=manager
password=${MANAGER_PASS}

[manager]
type=aor
max_contacts=5
remove_existing=yes

[client]
type=endpoint
context=internal
disallow=all
allow=ulaw
allow=alaw
auth=client-auth
aors=client
direct_media=no
rtp_symmetric=yes
force_rport=yes
rewrite_contact=yes

[client-auth]
type=auth
auth_type=userpass
username=client
password=${CLIENT_PASS}

[client]
type=aor
max_contacts=5
remove_existing=yes
EOF

echo "[5/7] Dialplan..."
cat > /etc/asterisk/extensions.conf << 'EOF'
[general]
static=yes
writeprotect=no

[internal]
exten => 100,1,NoOp(Call to Manager)
 same => n,Set(MONITOR_FILENAME=/var/spool/asterisk/monitor/${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}-${CALLERID(num)}-to-100)
 same => n,MixMonitor(${MONITOR_FILENAME}.wav,r)
 same => n,Dial(PJSIP/manager,30,t)
 same => n,Hangup()

exten => 200,1,NoOp(Call to Client)
 same => n,Set(MONITOR_FILENAME=/var/spool/asterisk/monitor/${STRFTIME(${EPOCH},,%Y%m%d-%H%M%S)}-${CALLERID(num)}-to-200)
 same => n,MixMonitor(${MONITOR_FILENAME}.wav,r)
 same => n,Dial(PJSIP/client,30,t)
 same => n,Hangup()

exten => 600,1,Answer()
 same => n,Echo()
 same => n,Hangup()
EOF

echo "[6/7] Dirs + logging..."
mkdir -p /var/spool/asterisk/monitor
chown asterisk:asterisk /var/spool/asterisk/monitor

cat > /etc/asterisk/logger.conf << 'EOF'
[general]
[logfiles]
console => notice,warning,error,verbose
messages.log => notice,warning,error,verbose
EOF

echo "[7/7] Firewall..."
ufw allow 22/tcp
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 5060/udp
ufw allow 5060/tcp
ufw allow 10000:20000/udp
echo 'y' | ufw enable

systemctl restart asterisk

echo ""
echo "=== DONE ==="
echo "Asterisk $(asterisk -V) running on ${EXTERNAL_IP}:5060"
echo "Accounts: manager/${MANAGER_PASS} (ext 100), client/${CLIENT_PASS} (ext 200)"
echo "Echo test: ext 600"
```
