"""
Бот «Финансовый код» — Яна Афонина.
Авторская формула. Прямая интеграция с Telegram Bot API через long polling.
"""

import json
import re
import time
import requests
import os

TOKEN = os.environ.get("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("Установи BOT_TOKEN в переменных окружения")

ADMIN_CHAT_ID = os.environ.get("ADMIN_CHAT_ID", "").strip()
SHEETS_WEBHOOK_URL = os.environ.get("SHEETS_WEBHOOK_URL", "").strip()

API = f"https://api.telegram.org/bot{TOKEN}"

ENTER_DATE_PHOTO_URL = "https://raw.githubusercontent.com/NeiyaYa/financial-code-bot/main/enter_date.jpg"

CHANNEL_USERNAME = "@yana_afonina_neiya"
CHANNEL_URL = "https://t.me/yana_afonina_neiya"
PRACTICE_URL = "https://t.me/yana_afonina_neiya/2097"

with open(os.path.join(os.path.dirname(__file__), "arcana_texts.json"), encoding="utf-8") as f:
    ARCANA = json.load(f)

STATES = {}


def reduce_arcana(n):
    while n > 22:
        n = sum(int(d) for d in str(n))
    return 22 if n == 0 else n


def calculate_finance(day, month, year):
    D = reduce_arcana(day)
    M_month = reduce_arcana(month)
    G = reduce_arcana(sum(int(d) for d in str(year)))
    X = reduce_arcana(D + M_month + G)
    K = reduce_arcana(D + M_month + G + X)
    arcana_M = reduce_arcana(K + X)
    arcana_S = reduce_arcana(K + G)
    arcana_P = reduce_arcana(arcana_M + arcana_S)
    return arcana_M, arcana_S, arcana_P


def parse_date(s):
    s = s.strip()
    m = re.match(r"^(\d{1,2})[.\/\-](\d{1,2})[.\/\-](\d{4})$", s)
    if not m:
        return None
    day, month, year = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= day <= 31 and 1 <= month <= 12 and 1900 <= year <= 2025):
        return None
    return day, month, year


def build_post(name, M, S, P):
    aM, aS, aP = ARCANA[str(M)], ARCANA[str(S)], ARCANA[str(P)]
    post = (
        f"🔮 {name}, ТВОЙ ФИНАНСОВЫЙ КОД: {M} – {S} – {P}\n\n"
        f"Каждое число — это аркан Таро.\n"
        f"И у каждого своя роль в твоих финансах.\n\n"
        f"——\n\n"
        f"1️⃣ Аркан {M} — {aM['name']}. ТВОЁ МЫШЛЕНИЕ О ДЕНЬГАХ.\n\n"
        f"{aM['mind_block']}\n\n"
        f"——\n\n"
        f"2️⃣ Аркан {S} — {aS['name']}. ТВОЯ СФЕРА ДЕНЕГ.\n\n"
        f"{aS['sphere_block']}\n\n"
        f"——\n\n"
        f"3️⃣ Аркан {P} — {aP['name']}. ТВОЙ ПОТОК.\n\n"
        f"{aP['flow_block']}\n\n"
        f"——\n\n"
        f"💎 СВЯЗКА {M}–{S}–{P}\n\n"
        f"Смотри, какая у тебя комбинация.\n\n"
        f"{aM['key']} — это твоё мышление.\n"
        f"{aS['key']} — это твоя сфера.\n"
        f"{aP['key']} — это твой поток.\n\n"
        f"Когда ты застряла в одном — два других проседают.\n"
        f"Когда переключаешься между ними — деньги идут к тебе как магнит к железу.\n\n"
        f"——\n\n"
        f"✨ ЧТО МОЖНО СДЕЛАТЬ УЖЕ СЕГОДНЯ\n\n"
        f"Не надо никуда бежать и ничего покупать.\n"
        f"Вот несколько простых вещей — попробуй на этой неделе.\n\n"
        f"{aM['practice']}\n"
        f"{aS['practice']}\n"
        f"{aP['practice']}"
    )
    return post


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text}
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
    if len(text) <= 4096:
        try:
            requests.post(f"{API}/sendMessage", json=payload, timeout=10)
        except Exception as e:
            print("send error:", e, flush=True)
        return
    parts, current = [], ""
    for chunk in text.split("\n"):
        if len(current) + len(chunk) + 1 > 4000:
            parts.append(current)
            current = chunk
        else:
            current = current + "\n" + chunk if current else chunk
    if current:
        parts.append(current)
    for p in parts:
        try:
            requests.post(f"{API}/sendMessage", json={"chat_id": chat_id, "text": p}, timeout=10)
            time.sleep(0.3)
        except Exception as e:
            print("send error:", e, flush=True)


def send_photo(chat_id, photo_url, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
    try:
        r = requests.post(f"{API}/sendPhoto", json=payload, timeout=15)
        if r.ok:
            return True
        print("photo error:", r.status_code, r.text[:200], flush=True)
    except Exception as e:
        print("photo error:", e, flush=True)
    if caption:
        send_message(chat_id, caption)
    return False


def answer_callback(callback_id, text=None, show_alert=False):
    payload = {"callback_query_id": callback_id}
    if text:
        payload["text"] = text
    if show_alert:
        payload["show_alert"] = True
    try:
        requests.post(f"{API}/answerCallbackQuery", json=payload, timeout=10)
    except Exception as e:
        print("callback answer error:", e, flush=True)


def is_subscribed(user_id):
    """Проверяем подписку через getChatMember. Бот должен быть админом канала."""
    try:
        r = requests.get(
            f"{API}/getChatMember",
            params={"chat_id": CHANNEL_USERNAME, "user_id": user_id},
            timeout=10,
        )
        data = r.json()
        if data.get("ok"):
            status = data["result"].get("status", "left")
            return status in ("member", "administrator", "creator")
        print("subscription check failed:", data, flush=True)
    except Exception as e:
        print("subscription check error:", e, flush=True)
    return False


def log_lead(state, user):
    username = user.get("username", "")
    user_id = user.get("id", "")
    full_name = (user.get("first_name", "") + " " + user.get("last_name", "")).strip()

    name = state.get("name", "")
    birth = state.get("birth_date", "")
    M, S, P = state.get("M"), state.get("S"), state.get("P")
    code = f"{M}-{S}-{P}"
    ts = time.strftime("%Y-%m-%d %H:%M:%S")

    if ADMIN_CHAT_ID:
        text = (
            "🌟 НОВЫЙ ЛИД В БОТЕ\n\n"
            f"Имя в боте: {name}\n"
            f"ДР: {birth}\n"
            f"Финансовый код: {code}\n"
            f"  • {M} — мышление\n"
            f"  • {S} — сфера\n"
            f"  • {P} — поток\n\n"
            f"Telegram: {full_name}"
            + (f" (@{username})" if username else "")
            + f"\nID: {user_id}\n"
            f"Время: {ts}"
        )
        try:
            requests.post(
                f"{API}/sendMessage",
                json={"chat_id": ADMIN_CHAT_ID, "text": text},
                timeout=10,
            )
        except Exception as e:
            print("admin notify error:", e, flush=True)

    if SHEETS_WEBHOOK_URL:
        try:
            requests.post(
                SHEETS_WEBHOOK_URL,
                json={
                    "timestamp": ts,
                    "name": name,
                    "birth_date": birth,
                    "M": M, "S": S, "P": P, "code": code,
                    "user_id": user_id,
                    "username": username,
                    "full_name": full_name,
                },
                timeout=5,
            )
        except Exception as e:
            print("sheets error:", e, flush=True)


WELCOME = (
    "Привет 🤍\n\n"
    "Я Яна Афонина — энерготерапевт, ясновидящая, регрессолог, мастер Рейки.\n\n"
    "Как реализовать своё предназначение и зарабатывать большие деньги? 💫\n\n"
    "Ты можешь это сделать, зная и правильно используя свои сильные и слабые стороны "
    "по дате рождения. И я готова тебе их раскрыть.\n\n"
    "Сейчас покажу твой финансовый код — три аркана, которые управляют твоими деньгами.\n\n"
    "Изучай прямо сейчас 👇\n\n"
    "Как мне к тебе обращаться?"
)

PRACTICE_PROMO = (
    "А пока, мой друг, можешь забрать ПРАКТИКУ «Корни денежного сценария» ☀️\n\n"
    "Отдаю её тебе за простое действие — подписку на мой личный ТГ-канал, "
    "там много полезной информации и практик.\n\n"
    "1️⃣ Жми «Подписаться на канал»\n"
    "2️⃣ Возвращайся и жми «Я подписалась(лся) — проверить»\n\n"
    "И я открою тебе доступ к практике 🍀"
)


def handle_callback(cb):
    cb_id = cb.get("id")
    user = cb.get("from", {})
    user_id = user.get("id")
    data = cb.get("data", "")
    msg = cb.get("message") or {}
    chat_id = msg.get("chat", {}).get("id")

    if data == "check_sub":
        if not chat_id:
            answer_callback(cb_id)
            return
        if is_subscribed(user_id):
            answer_callback(cb_id, "Подписка подтверждена! 🌟")
            send_message(
                chat_id,
                "Готово, мой друг 🤍\n\nДержи свою практику 👇",
                reply_markup={
                    "inline_keyboard": [[
                        {"text": "🎁 Забрать практику", "url": PRACTICE_URL}
                    ]]
                }
            )
        else:
            answer_callback(
                cb_id,
                "Подписки пока не вижу 🙈\nПодпишись на канал и нажми снова",
                show_alert=True,
            )


def handle(update):
    if "callback_query" in update:
        handle_callback(update["callback_query"])
        return

    msg = update.get("message")
    if not msg or "text" not in msg:
        return
    chat_id = msg["chat"]["id"]
    text = msg["text"].strip()
    state = STATES.get(chat_id, {"step": "start"})

    if text == "/start" or state["step"] == "start":
        STATES[chat_id] = {"step": "ask_name"}
        send_message(chat_id, WELCOME)
        return

    if state["step"] == "ask_name":
        state["name"] = text[:50]
        state["step"] = "ask_date"
        STATES[chat_id] = state
        time.sleep(0.3)
        caption = f"{state['name']}, введи свою дату рождения 📆\n\nВ формате ДД.ММ.ГГГГ (например: 11.03.1981)"
        send_photo(chat_id, ENTER_DATE_PHOTO_URL, caption=caption)
        return

    if state["step"] == "ask_date":
        parsed = parse_date(text)
        if not parsed:
            send_message(chat_id, "Не разобралась с датой 🙈 Попробуй в формате 11.03.1981")
            return
        day, month, year = parsed
        state["birth_date"] = text
        state["day"], state["month"], state["year"] = day, month, year
        state["step"] = "calculating"
        STATES[chat_id] = state

        send_message(chat_id, "Считаю твою матрицу... ✨")
        time.sleep(3)

        M, S, P = calculate_finance(day, month, year)
        state["M"], state["S"], state["P"] = M, S, P
        state["step"] = "done"
        STATES[chat_id] = state

        post = build_post(state["name"], M, S, P)
        send_message(chat_id, post)
        time.sleep(1)
        send_message(
            chat_id,
            PRACTICE_PROMO,
            reply_markup={
                "inline_keyboard": [
                    [{"text": "📢 Подписаться на канал", "url": CHANNEL_URL}],
                    [{"text": "✅ Я подписалась(лся) — проверить", "callback_data": "check_sub"}],
                ]
            }
        )

        try:
            log_lead(state, msg.get("from", {}))
        except Exception as e:
            print("log_lead error:", e, flush=True)
        return

    if state["step"] == "done":
        send_message(chat_id, "Если хочешь начать сначала — отправь /start")
        return


def main():
    print("Бот запущен. Long polling...", flush=True)
    print(
        f"admin_chat: {'есть' if ADMIN_CHAT_ID else 'нет'} | "
        f"sheets: {'есть' if SHEETS_WEBHOOK_URL else 'нет'}",
        flush=True,
    )
    offset = 0
    allowed = ["message", "callback_query"]
    while True:
        try:
            r = requests.get(
                f"{API}/getUpdates",
                params={"timeout": 25, "offset": offset, "allowed_updates": json.dumps(allowed)},
                timeout=30,
            )
            data = r.json()
            if data.get("ok"):
                for upd in data.get("result", []):
                    offset = upd["update_id"] + 1
                    try:
                        handle(upd)
                    except Exception as e:
                        print("handle error:", e, flush=True)
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print("poll error:", e, flush=True)
            time.sleep(2)


if __name__ == "__main__":
    main()
