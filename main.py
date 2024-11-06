import logging
import os
import asyncio
import json
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.exceptions import TelegramAPIError
from aiogram.types import Message, ChatMemberUpdated, BotCommand, KeyboardButton, ReplyKeyboardMarkup, FSInputFile, \
    Update
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

API_TOKEN = '7887152677:AAE1fTiA9MHD7tWV6D0S07yvlR7p93tJSvU'
CHANNEL_ID = '-1002413152142'
admin_ids = [6699675868, 114253636]

bot = Bot(token=API_TOKEN)
dp = Dispatcher()

# Словари для хранения пригласительных ссылок и бонусов
user_links = {}
user_bonuses = {}
user_link_count = {}
photo_path = os.path.join(os.path.dirname(__file__), 'photos', 'id-group.jpg')

# Файл для сохранения данных
DATA_FILE = 'data.json'


# Загрузка данных из файла
def load_data():
    global user_links, user_bonuses, user_link_count
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            user_links = data.get('user_links', {})
            user_bonuses = data.get('user_bonuses', {})
            user_link_count = data.get('user_link_count', {})
    logger.info("Данные загружены из файла.")


# Сохранение данных в файл
def save_data():
    data = {
        'user_links': user_links,
        'user_bonuses': user_bonuses,
        'user_link_count': user_link_count
    }
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)
    logger.info("Данные сохранены в файл.")


class AdvertisementState(StatesGroup):
    waiting_for_ad = State()


# Админская клавиатура
admin_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="/top")],
        [KeyboardButton(text="/reklama")]
    ],
    resize_keyboard=True
)

back_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="Orqaga ↩️")]
    ],
    resize_keyboard=True
)


# Проверка на права администратора
def is_admin(user_id):
    return user_id in admin_ids


# Вернуться назад
@dp.message(lambda message: message.text == "Orqaga ↩️")
async def go_back(message: Message):
    if is_admin(message.from_user.id):
        await message.answer("Ishni tanlang: 🤔", reply_markup=admin_keyboard)


# Создание уникальной ссылки
@dp.message(Command("start"))
async def create_invite_link(message: Message):
    user_id = message.from_user.id
    if is_admin(user_id):
        await message.answer("Assalomu alaykum, Admin! 👋\n"
                             "Ishni Tanlang - 🤔", reply_markup=admin_keyboard)
    else:
        if user_link_count.get(user_id, 0) >= 3:
            await message.answer("❌ Siz faqatgina 3 ta havola yaratishingiz mumkin.")
            return

        try:
            invite_link = await bot.create_chat_invite_link(chat_id=CHANNEL_ID, member_limit=0)
            user_links[user_id] = invite_link.invite_link
            user_link_count[user_id] = user_link_count.get(user_id, 0) + 1

            caption_text = (
                f"💻 Kompyuter va noutbuklar.\n"
                f"📸 Videokuzatuvning barcha turlari.\n"
                f"📟 Domofonlar\n"
                f"📌 Gps-trekerlar\n"
                f"🛠 Ta'mirlash va o'rnatish.\n"
                f"☎️ Telefon: (99)381-58-58\n"
                f"☎️ Telefon: (33)620-58-58\n"
                f"📍 Manzil: Urganch P.Mahmud 2a\n"
                f"🗺 Mo'ljal: Лучевой\n\n"
                f"Mana sizning taklif qilish uchun noyob havolangiz: <a href=\"{invite_link.invite_link}\">Havola</a>"
            )

            photo = FSInputFile(photo_path)
            await bot.send_photo(chat_id=message.chat.id, photo=photo, caption=caption_text, parse_mode="HTML")
            save_data()
        except Exception as e:
            logger.error(f"Havola yaratishda xato: {e}")
            await message.answer("Sizning havolangizni yaratishda xato yuz berdi. Iltimos, keyinroq urinib ko'ring.")


# Проверка количества бонусов
@dp.message(Command("bonuses"))
async def check_bonuses(message: Message):
    bonuses = user_bonuses.get(message.from_user.id, 0)
    await message.answer(f"Sizning bonuslaringiz: {bonuses}")


# Отправка рекламы
@dp.message(Command("reklama"))
async def send_advertisement(message: Message, state: FSMContext):
    if not user_links:
        await message.answer("🔔 Hozirda reklama yuborish uchun foydalanuvchilar mavjud emas.")
        return

    if not is_admin(message.from_user.id):
        await message.answer("❌ Sizda ushbu buyruqni bajarish huquqi yo'q.")
        return

    await message.answer("📢 Reklama xabaringizni yuboring: ")
    await state.set_state(AdvertisementState.waiting_for_ad)


@dp.message(AdvertisementState.waiting_for_ad)
async def handle_advertisement(msg: types.Message, state: FSMContext):
    advertisement_text = ""

    if msg.photo:
        advertisement_text = msg.caption if msg.caption else None
    elif msg.video_note:
        advertisement_text = None
    elif msg.text:
        advertisement_text = msg.text
    elif msg.sticker:
        advertisement_text = None
    else:
        await msg.answer("❌ Iltimos, foto, matn, stiker yoki videoxabar (krujochek) yuboring.")
        return

    for user_id in user_links.keys():
        try:
            if msg.photo:
                await bot.send_photo(user_id, photo=msg.photo[-1].file_id, caption=advertisement_text)
            elif msg.video_note:
                await bot.send_video_note(user_id, video_note=msg.video_note.file_id)
            elif msg.sticker:
                await bot.send_sticker(user_id, sticker=msg.sticker.file_id)
            else:
                await bot.send_message(user_id, advertisement_text)
        except Exception as e:
            logging.error(f"Foydalanuvchi {user_id} ga xabar yuborishda xato: {e}")
            await msg.answer(f"❌ Xabar yuborishda xato: {user_id} ga xabar yuborilmadi.")

    await msg.answer("✅ Reklama xabari muvaffaqiyatli yuborildi.")
    await msg.answer("✅ Reklama yuborildi! Boshqa buyruq uchun tanlang:", reply_markup=back_keyboard)
    await state.clear()


# Отображение топа
@dp.message(Command("top"))
async def show_top_referrers(message: Message):
    if str(message.from_user.id) != str(admin_ids):
        await message.answer("❌ Sizda ushbu buyruqni bajarish huquqi yo'q.")
        return

    top_referrers = sorted(user_bonuses.items(), key=lambda x: x[1], reverse=True)[:10]
    if top_referrers:
        top_text = "🏆 Tashkil etilgan foydalanuvchilar:\n"
        for idx, (user_id, bonus) in enumerate(top_referrers, 1):
            try:
                user = await bot.get_chat(user_id)
                username = f"@{user.username}" if user.username else f"Foydalanuvchi {user_id}"
            except Exception:
                username = f"Foydalanuvchi {user_id}"

            top_text += f"{idx}. {username} - {bonus} taklif\n"
    else:
        top_text = "Hozirda takliflar bo'yicha ma'lumotlar mavjud emas."

    await message.answer(top_text)


# Обработка новых участников
@dp.chat_member()
async def handle_new_member(event: ChatMemberUpdated):
    if event.new_chat_member.status == "member" and event.invite_link:
        inviter_id = next((uid for uid, link in user_links.items() if link == event.invite_link.invite_link), None)
        if inviter_id is not None:
            new_member_name = event.new_chat_member.user.first_name
            user_bonuses[inviter_id] = user_bonuses.get(inviter_id, 0) + 1
            await bot.send_message(
                inviter_id,
                f"✅ - Sizning havolangizdan - {new_member_name} - qo'shildi!\n"
                f"Bonuslar: {user_bonuses[inviter_id]}"
            )
            save_data()


async def set_commands():
    commands = [
        types.BotCommand(command="start", description="Botni ishga tushirish"),
    ]
    await bot.set_my_commands(commands)


async def main():
    load_data()  # Загружаем данные при запуске
    await set_commands()  # Устанавливаем команды бота
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()  # Закрываем сессию при завершении работы


if __name__ == '__main__':
    asyncio.run(main())  # Запуск основного цикла бота
