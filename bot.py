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
        f"{aP['practice']}\n\n"
        f"——\n\n"
        f"🤍 А ЕСЛИ ХОЧЕТСЯ ГЛУБЖЕ\n\n"
        f"Я не зову за собой. Каждый идёт сам.\n"
        f"Но если внутри что-то отозвалось — знай, что есть несколько дорог.\n"
        f"Со мной или без меня — твой выбор.\n\n"
        f"Если решишь, что хочется разобрать твою матрицу глубже,\n"
        f"увидеть свой денежный канал и закрыть кармические блоки —\n"
        f"напиши мне в личку. Я не давлю и не уговариваю.\n\n"
        f"Я просто рядом, если позовёшь."
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


def log_lead(state, msg):
    user = msg.get("from", {})
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


def handle(update):
    msg = update.get("message")
    if not msg or "text" not in msg:
        return
    chat_id = msg["chat"]["id"]
    text = msg["text"].strip()
    state = STATES.get(chat_id, {"step": "start"})

    if text == "/start" or state["step"] == "start":
        STATES[chat_id] = {"step": "ask_name"}
        send_message(
            chat_id,
            "Здравия 🤗\n\n"
            "Я Яна Афонина — энерготерапевт, ясновидящая, мастер Рейки.\n\n"
            "Сейчас покажу твой финансовый код — три аркана,\n"
            "которые управляют твоими деньгами.\n\n"
            "Это не про «как заработать».\n"
            "Это про то, ПОЧЕМУ деньги ведут себя именно так,\n"
            "как ведут себя у тебя.\n\n"
            "Как мне к тебе обращаться?"
        )
        return

    if state["step"] == "ask_name":
        state["name"] = text[:50]
        state["step"] = "ask_date"
        STATES[chat_id] = state
        send_message(
            chat_id,
            f"{state['name']}, какая у тебя дата рождения?\n\n"
            f"Введи в формате ДД.ММ.ГГГГ\n"
            f"(например: 11.03.1981)"
        )
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
            "Если хочешь, чтобы я разобрала твою матрицу лично —\n"
            "напиши мне в личку. Я не давлю и не уговариваю.\n\n"
            "Я просто рядом 🫶",
            reply_markup={
                "inline_keyboard": [[
                    {"text": "💬 Написать Яне", "url": "https://t.me/Neiya_Ya"}
                ]]
            }
        )

        try:
            log_lead(state, msg)
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
    while True:
        try:
            r = requests.get(
                f"{API}/getUpdates",
                params={"timeout": 25, "offset": offset},
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
      