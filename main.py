# main.py
import os
import json
import io
from datetime import datetime
from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    InputFile
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)

DATA_FILE = "data.json"

# ---------------- load/save ----------------
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_data(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

DATA = load_data()

# ---------------- localization ----------------
TEXT = {
    "ua": {
        "welcome": "Привіт! Я бот для обліку витрат на вечірках 🎉",
        "choose_lang": "Оберіть мову / Choose language:",
        "menu": "Головне меню — оберіть дію:",
        "buttons": [
            ["🎉 Створити вечірку", "🎈 Обрати вечірку"],
            ["➕ Додати витрату", "👥 Учасники"],
            ["✏️ Редагувати учасників", "🗑️ Керування вечірками"],
            ["📊 Підсумок", "📤 Експорт у TXT"],
            ["🌐 Мова"]
        ],
        "ask_party_name": "Введіть назву нової вечірки:",
        "party_created": "🎉 Вечірку '{name}' створено і вибрано.",
        "no_parties": "Поки що немає вечірок.",
        "choose_party_prompt": "Оберіть вечірку зі списку:",
        "party_selected": "✅ Вибрано вечірку: {name}",
        "ask_amount": "💰 Введіть суму витрати (наприклад: 25.50):",
        "ask_desc": "📝 Введіть опис витрати (або '-' для пропуску):",
        "expense_added": "✅ Додано витрату {amount:.2f} від {user}",
        "invalid_amount": "❗ Некоректна сума. Спробуйте ще раз.",
        "no_current_party": "❗ Спочатку оберіть вечірку.",
        "members_none": "Поки що немає учасників.",
        "members_list": "👥 Учасники вечірки:\n",
        "edit_members_menu": "Керування учасниками — оберіть дію:",
        "ask_member_name": "Введіть нік або ім'я учасника (без @):",
        "member_added": "✅ Учасника {name} додано.",
        "member_removed": "🗑️ Учасника {name} видалено.",
        "choose_party_to_delete": "Оберіть вечірку для видалення (лише автор може видаляти):",
        "back_to_menu": "↩️ Повертаємось у меню.",
        "no_permission_delete": "⛔ Лише автор вечірки може її видалити.",
        "party_deleted": "🗑️ Вечірку '{name}' видалено.",
        "export_no_party": "❗ Спочатку оберіть вечірку.",
        "export_generating": "📤 Генерую підсумок і надсилаю файл...",
        "export_done": "✅ Файл надіслано.",
        "summary_header": "📊 Підсумок вечірки:",
        "all_settled": "✅ Усі розрахувалися.",
        "change_lang_prompt": "Оберіть мову:",
    },
    "en": {
        "welcome": "Hi! I’m a party expenses bot 🎉",
        "choose_lang": "Choose language / Оберіть мову:",
        "menu": "Main menu — choose action:",
        "buttons": [
            ["🎉 Create party", "🎈 Select party"],
            ["➕ Add expense", "👥 Members"],
            ["✏️ Edit members", "🗑️ Manage parties"],
            ["📊 Summary", "📤 Export to TXT"],
            ["🌐 Language"]
        ],
        "ask_party_name": "Enter new party name:",
        "party_created": "🎉 Party '{name}' created and selected.",
        "no_parties": "No parties yet.",
        "choose_party_prompt": "Choose a party from the list:",
        "party_selected": "✅ Selected party: {name}",
        "ask_amount": "💰 Enter amount (e.g. 25.50):",
        "ask_desc": "📝 Enter description (or '-' to skip):",
        "expense_added": "✅ Added expense {amount:.2f} from {user}",
        "invalid_amount": "❗ Invalid amount. Try again.",
        "no_current_party": "❗ Please select a party first.",
        "members_none": "No members yet.",
        "members_list": "👥 Party members:\n",
        "edit_members_menu": "Manage members — choose action:",
        "ask_member_name": "Enter member name or nickname (without @):",
        "member_added": "✅ Member {name} added.",
        "member_removed": "🗑️ Member {name} removed.",
        "choose_party_to_delete": "Choose a party to delete (only creator can delete):",
        "back_to_menu": "↩️ Returning to menu.",
        "no_permission_delete": "⛔ Only party creator can delete it.",
        "party_deleted": "🗑️ Party '{name}' deleted.",
        "export_no_party": "❗ Please select a party first.",
        "export_generating": "📤 Generating summary and sending file...",
        "export_done": "✅ File sent.",
        "summary_header": "📊 Party summary:",
        "all_settled": "✅ All settled.",
        "change_lang_prompt": "Choose language:",
    }
}

# ---------------- keyboards ----------------
def main_keyboard(lang):
    return ReplyKeyboardMarkup(TEXT[lang]["buttons"], resize_keyboard=True)

def choices_keyboard(items, back_label):
    buttons = [[i] for i in items]
    buttons.append([back_label])
    return ReplyKeyboardMarkup(buttons, resize_keyboard=True)

def edit_members_keyboard(lang):
    # add / remove / back
    if lang == "ua":
        return ReplyKeyboardMarkup([["➕ Додати учасника", "🗑️ Видалити учасника"], ["↩️ Назад"]], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([["➕ Add member", "🗑️ Remove member"], ["↩️ Back"]], resize_keyboard=True)

# ---------------- settlements ----------------
def compute_settlements(members_totals):
    # members_totals: dict name -> total_spent
    totals = {u: round(v,2) for u,v in members_totals.items()}
    n = len(totals) if totals else 1
    total_sum = round(sum(totals.values()),2)
    avg = round(total_sum / n, 2) if n else 0.0
    balances = {u: round(spent - avg, 2) for u, spent in totals.items()}
    creditors = sorted([(u,b) for u,b in balances.items() if b>0], key=lambda x:-x[1])
    debtors = sorted([(u,-b) for u,b in balances.items() if b<0], key=lambda x:-x[1])
    i=j=0
    debts=[]
    while i < len(debtors) and j < len(creditors):
        d_name, d_amt = debtors[i]
        c_name, c_amt = creditors[j]
        pay = round(min(d_amt, c_amt),2)
        if pay>0:
            debts.append((d_name, c_name, pay))
        debtors[i] = (d_name, round(d_amt - pay,2))
        creditors[j] = (c_name, round(c_amt - pay,2))
        if debtors[i][1] == 0: i += 1
        if creditors[j][1] == 0: j += 1
    return avg, balances, debts

# ---------------- helper ----------------
def get_lang(chat_id):
    return DATA.get(str(chat_id), {}).get("lang", "ua")

def ensure_chat(chat_id):
    DATA.setdefault(str(chat_id), {"lang": "ua", "parties": {}, "current": None})

# ---------------- handlers ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    ensure_chat(chat_id)
    lang = get_lang(chat_id)
    # If language not chosen before, ask; else show menu immediately
    if DATA[str(chat_id)].get("lang") is None:
        await update.message.reply_text(TEXT["ua"]["choose_lang"], reply_markup=ReplyKeyboardMarkup([["🇺🇦 Українська","🇬🇧 English"]], resize_keyboard=True))
    else:
        await update.message.reply_text(TEXT[lang]["menu"], reply_markup=main_keyboard(lang))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat = update.effective_chat
    chat_id = chat.id
    user = update.effective_user
    text = (update.message.text or "").strip()
    ensure_chat(chat_id)
    lang = get_lang(chat_id)
    t = TEXT[lang]

    # Language selection (first time or via menu)
    if text in ["🇺🇦 Українська", "🇬🇧 English", "🌐 Мова", "🌐 Language"]:
        # if explicit language buttons
        if text == "🇺🇦 Українська":
            DATA[str(chat_id)]["lang"] = "ua"
        elif text == "🇬🇧 English":
            DATA[str(chat_id)]["lang"] = "en"
        else:
            # Show explicit change language menu
            await update.message.reply_text(TEXT[lang]["change_lang_prompt"], reply_markup=ReplyKeyboardMarkup([["🇺🇦 Українська","🇬🇧 English"], [t["back_to_menu"]]], resize_keyboard=True))
            return
        save_data(DATA)
        lang = get_lang(chat_id)
        await update.message.reply_text(TEXT[lang]["menu"], reply_markup=main_keyboard(lang))
        return

    # MAIN MENU BUTTONS
    # Create party
    if text in [TEXT[lang]["buttons"][0][0], "🎉 Створити вечірку", "🎉 Create party"]:
        await update.message.reply_text(t["ask_party_name"], reply_markup=ReplyKeyboardRemove())
        context.user_data["creating_party"] = True
        return

    if context.user_data.get("creating_party"):
        name = text
        if not name:
            await update.message.reply_text(t["ask_party_name"])
            return
        # create party
        ensure_chat(chat_id)
        DATA[str(chat_id)]["parties"].setdefault(name, {"creator": user.id, "members": {}, "expenses": []})
        # add creator automatically
        p_name = user.username or user.first_name
        DATA[str(chat_id)]["parties"][name]["members"].setdefault(p_name, 0.0)
        DATA[str(chat_id)]["current"] = name
        save_data(DATA)
        context.user_data["creating_party"] = False
        await update.message.reply_text(t["party_created"].format(name=name), reply_markup=main_keyboard(lang))
        return

    # Select party
    if text in [TEXT[lang]["buttons"][0][1], "🎈 Обрати вечірку", "🎈 Select party"]:
        parties = list(DATA[str(chat_id)]["parties"].keys())
        if not parties:
            await update.message.reply_text(t["no_parties"], reply_markup=main_keyboard(lang))
            return
        await update.message.reply_text(t["choose_party_prompt"], reply_markup=choices_keyboard(parties, t["back_to_menu"]))
        context.user_data["choosing_party"] = True
        return

    if context.user_data.get("choosing_party"):
        if text == t["back_to_menu"] or text in ["↩️ Назад","↩️ Back"]:
            context.user_data["choosing_party"] = False
            await update.message.reply_text(t["back_to_menu"], reply_markup=main_keyboard(lang))
            return
        if text in DATA[str(chat_id)]["parties"]:
            DATA[str(chat_id)]["current"] = text
            save_data(DATA)
            context.user_data["choosing_party"] = False
            await update.message.reply_text(t["party_selected"].format(name=text), reply_markup=main_keyboard(lang))
        else:
            await update.message.reply_text(t["no_parties"], reply_markup=main_keyboard(lang))
        return

    # Add expense (init)
    if text in [TEXT[lang]["buttons"][1][0], "➕ Додати витрату", "➕ Add expense"]:
        if not DATA[str(chat_id)].get("current"):
            await update.message.reply_text(t["no_current_party"], reply_markup=main_keyboard(lang))
            return
        await update.message.reply_text(t["ask_amount"], reply_markup=ReplyKeyboardRemove())
        context.user_data["awaiting_amount"] = True
        return

    # Awaiting amount
    if context.user_data.get("awaiting_amount"):
        # parse float supporting comma
        try:
            amt = float(text.replace(",", "."))
            if amt < 0:
                raise ValueError
        except Exception:
            await update.message.reply_text(t["invalid_amount"], reply_markup=main_keyboard(lang))
            return
        context.user_data["pending_amount"] = round(amt, 2)
        context.user_data["awaiting_amount"] = False
        context.user_data["awaiting_desc"] = True
        await update.message.reply_text(t["ask_desc"], reply_markup=ReplyKeyboardRemove())
        return

    # Awaiting description -> save expense
    if context.user_data.get("awaiting_desc"):
        desc = text if text and text != "-" else ""
        amt = context.user_data.pop("pending_amount", 0.0)
        context.user_data["awaiting_desc"] = False
        cur = DATA[str(chat_id)].get("current")
        if not cur:
            await update.message.reply_text(t["no_current_party"], reply_markup=main_keyboard(lang))
            return
        party = DATA[str(chat_id)]["parties"].setdefault(cur, {"creator": None, "members": {}, "expenses": []})
        payer = user.username or user.first_name
        party["members"].setdefault(payer, 0.0)
        party["expenses"].append({"user": payer, "amount": amt, "desc": desc, "ts": datetime.utcnow().isoformat()})
        party["members"][payer] = round(party["members"].get(payer, 0.0) + amt, 2)
        save_data(DATA)
        await update.message.reply_text(t["expense_added"].format(amount=amt, user=payer), reply_markup=main_keyboard(lang))
        return

    # Members list
    if text in [TEXT[lang]["buttons"][1][1], "👥 Учасники", "👥 Members"]:
        cur = DATA[str(chat_id)].get("current")
        if not cur:
            await update.message.reply_text(t["no_current_party"], reply_markup=main_keyboard(lang))
            return
        party = DATA[str(chat_id)]["parties"].get(cur, {})
        members = party.get("members", {})
        if not members:
            await update.message.reply_text(t["members_none"], reply_markup=main_keyboard(lang))
            return
        msg = t["members_list"]
        for u, tot in members.items():
            msg += f"• {u}: {tot:.2f}\n"
        await update.message.reply_text(msg, reply_markup=main_keyboard(lang))
        return

    # Edit members menu
    if text in ["✏️ Редагувати учасників", "✏️ Edit members", TEXT[lang]["buttons"][2][0]]:
        await update.message.reply_text(t["edit_members_menu"], reply_markup=edit_members_keyboard(lang))
        context.user_data["editing_members"] = True
        return

    if context.user_data.get("editing_members"):
        # Add member
        if text in ["➕ Додати учасника", "➕ Add member"]:
            await update.message.reply_text(t["ask_member_name"], reply_markup=ReplyKeyboardRemove())
            context.user_data["adding_member"] = True
            context.user_data["editing_members"] = False
            return
        # Remove member
        if text in ["🗑️ Видалити учасника", "🗑️ Remove member"]:
            await update.message.reply_text(t["ask_member_name"], reply_markup=ReplyKeyboardRemove())
            context.user_data["removing_member"] = True
            context.user_data["editing_members"] = False
            return
        # Back
        if text in ["↩️ Назад", "↩️ Back", t["back_to_menu"]]:
            context.user_data["editing_members"] = False
            await update.message.reply_text(t["back_to_menu"], reply_markup=main_keyboard(lang))
            return

    if context.user_data.get("adding_member"):
        name = text.replace("@", "").strip()
        if not name:
            await update.message.reply_text(t["ask_member_name"])
            return
        cur = DATA[str(chat_id)].get("current")
        if not cur:
            await update.message.reply_text(t["no_current_party"], reply_markup=main_keyboard(lang))
            context.user_data["adding_member"] = False
            return
        party = DATA[str(chat_id)]["parties"].setdefault(cur, {"creator": None, "members": {}, "expenses": []})
        party["members"].setdefault(name, 0.0)
        save_data(DATA)
        context.user_data["adding_member"] = False
        await update.message.reply_text(t["member_added"].format(name=name), reply_markup=main_keyboard(lang))
        return

    if context.user_data.get("removing_member"):
        name = text.replace("@","").strip()
        if not name:
            await update.message.reply_text(t["ask_member_name"])
            return
        cur = DATA[str(chat_id)].get("current")
        if not cur:
            await update.message.reply_text(t["no_current_party"], reply_markup=main_keyboard(lang))
            context.user_data["removing_member"] = False
            return
        party = DATA[str(chat_id)]["parties"].get(cur, {})
        if name in party.get("members", {}):
            del party["members"][name]
            # leave historical expenses (optional: remove expense records)
            save_data(DATA)
            await update.message.reply_text(t["member_removed"].format(name=name), reply_markup=main_keyboard(lang))
        else:
            await update.message.reply_text("❗ Учасника не знайдено.", reply_markup=main_keyboard(lang))
        context.user_data["removing_member"] = False
        return

    # Manage / delete parties
    if text in ["🗑️ Керування вечірками", "🗑️ Manage parties", TEXT[lang]["buttons"][2][1]]:
        parties = list(DATA[str(chat_id)]["parties"].keys())
        if not parties:
            await update.message.reply_text(t["no_parties"], reply_markup=main_keyboard(lang))
            return
        await update.message.reply_text(t["choose_party_to_delete"], reply_markup=choices_keyboard(parties, t["back_to_menu"]))
        context.user_data["deleting_party"] = True
        return

    if context.user_data.get("deleting_party"):
        if text in [t["back_to_menu"], "↩️ Назад", "↩️ Back"]:
            context.user_data["deleting_party"] = False
            await update.message.reply_text(t["back_to_menu"], reply_markup=main_keyboard(lang))
            return
        selected = text.strip()
        if selected in DATA[str(chat_id)]["parties"]:
            party = DATA[str(chat_id)]["parties"][selected]
            creator = party.get("creator")
            if creator is None or int(user.id) == int(creator):
                del DATA[str(chat_id)]["parties"][selected]
                if DATA[str(chat_id)].get("current") == selected:
                    DATA[str(chat_id)]["current"] = None
                save_data(DATA)
                await update.message.reply_text(t["party_deleted"].format(name=selected), reply_markup=main_keyboard(lang))
            else:
                await update.message.reply_text(t["no_permission_delete"], reply_markup=main_keyboard(lang))
        else:
            await update.message.reply_text("❌ Такої вечірки немає.", reply_markup=main_keyboard(lang))
        context.user_data["deleting_party"] = False
        return

    # Summary
    if text in [TEXT[lang]["buttons"][3][0], "📊 Підсумок", "📊 Summary"]:
        cur = DATA[str(chat_id)].get("current")
        if not cur:
            await update.message.reply_text(t["no_current_party"], reply_markup=main_keyboard(lang))
            return
        party = DATA[str(chat_id)]["parties"].get(cur, {})
        members = party.get("members", {})
        if not members:
            await update.message.reply_text(t["members_none"], reply_markup=main_keyboard(lang))
            return
        avg, balances, debts = compute_settlements(members)
        lines = [t["summary_header"], f"Party: {cur}", ""]
        for u,tot in members.items():
            lines.append(f"{u}: {tot:.2f}")
        lines.append("")
        lines.append(f"Average: {avg:.2f}")
        lines.append("")
        if debts:
            lines.append("Suggested transfers:")
            for d,c,a in debts:
                lines.append(f"{d} -> {c} : {a:.2f}")
        else:
            lines.append(t["all_settled"])
        await update.message.reply_text("\n".join(lines), reply_markup=main_keyboard(lang))
        return

    # Export TXT
    if text in [TEXT[lang]["buttons"][3][1], "📤 Експорт у TXT", "📤 Export to TXT"]:
        cur = DATA[str(chat_id)].get("current")
        if not cur:
            await update.message.reply_text(t["export_no_party"], reply_markup=main_keyboard(lang))
            return
        await update.message.reply_text(t["export_generating"], reply_markup=ReplyKeyboardRemove())
        party = DATA[str(chat_id)]["parties"].get(cur, {})
        members = party.get("members", {})
        expenses = party.get("expenses", [])
        avg, balances, debts = compute_settlements(members)
        lines = []
        lines.append(f"Party: {cur}")
        lines.append(f"Creator ID: {party.get('creator')}")
        lines.append(f"Generated: {datetime.utcnow().isoformat()} UTC")
        lines.append("")
        lines.append("Members and totals:")
        for u,tot in members.items():
            lines.append(f" - {u}: {tot:.2f}")
        lines.append("")
        lines.append(f"Total: {sum(members.values()):.2f}")
        lines.append(f"Average: {avg:.2f}")
        lines.append("")
        lines.append("Balances (positive => should receive):")
        for u,b in balances.items():
            lines.append(f" - {u}: {b:+.2f}")
        lines.append("")
        lines.append("Suggested transfers:")
        if debts:
            for d,c,a in debts:
                lines.append(f" - {d} -> {c} : {a:.2f}")
        else:
            lines.append(" - All settled")
        txt = "\n".join(lines)
        bio = io.BytesIO(txt.encode("utf-8"))
        bio.name = f"{cur}_summary.txt"
        await update.message.reply_document(InputFile(bio), caption=t["export_done"])
        await update.message.reply_text(t["export_done"], reply_markup=main_keyboard(lang))
        return

    # fallback: show menu
    await update.message.reply_text(t["menu"], reply_markup=main_keyboard(lang))
    return

# ---------------- errors ----------------
async def err_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print("Error:", context.error)

# ---------------- main ----------------
def main():
    token = os.environ.get("BOT_TOKEN")
    if not token:
        print("ERROR: set BOT_TOKEN environment variable")
        return
    app = ApplicationBuilder().token(token).build()
    app.add_handler(CommandHandler("start", start))
    # respond when added to group
    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(err_handler)
    print("Bot started")
    app.run_polling()

if __name__ == "__main__":
    main()

