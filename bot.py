import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.types import Message, PollAnswer
from aiogram.filters import Command
from database import Database
from config import API_TOKEN

# Initialize Bot and Dispatcher
bot = Bot(token=API_TOKEN)
dp = Dispatcher()
db = Database()

@dp.message(Command('start'))
async def cmd_start(message: Message):
    participant = db.get_participant(message.from_user.id)
    if not participant:
        db.add_participant(message.from_user.id, message.from_user.full_name)
        await message.answer("Вы успешно зарегистрированы.")
    else:
        await message.answer("Вы уже зарегистрированы.")

@dp.message(Command('set_admin'))
async def cmd_set_admin(message: Message):
    if db.is_admin(message.from_user.id):
        try:
            new_admin_id = int(message.get_args())
            db.set_admin(new_admin_id)
            await message.answer("Новый администратор назначен.")
        except ValueError:
            await message.answer("Укажите корректный Telegram ID.")
    else:
        await message.answer("У вас нет прав для выполнения этой команды.")

@dp.message(Command('create_poll'))
async def cmd_create_poll(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("Только администратор может создавать опросы.")
        return

    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: /create_poll Дата Время Место Сумма")
        return

    try:
        info = args[1].split()
        date, time, location, fee = info[0], info[1], info[2], float(info[3])
        training_id = db.add_training(date, time, location, fee)
        poll_question = f"Тренировка {date} в {time} на {location}. Стоимость: {fee} руб."
        poll_options = ["Смогу", "Приду с другом", "Не смогу", "Не определился"]
        poll_message = await bot.send_poll(
            message.chat.id,
            question=poll_question,
            options=poll_options,
            is_anonymous=False,
            allows_multiple_answers=False
        )
        db.link_poll_to_training(training_id, poll_message.poll.id)
    except Exception as e:
        await message.answer("Ошибка при создании опроса.")
        print(e)

@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    status_index = poll_answer.option_ids[0]
    status_mapping = {0: 'смогу', 1: 'приду с другом', 2: 'не смогу', 3: 'не определился'}
    status_text = status_mapping.get(status_index, 'не определился')

    training_id = db.get_training_id_by_poll(poll_id)
    if training_id:
        db.update_registration(user_id, training_id, status_text)
        if status_text in ['смогу', 'приду с другом']:
            fee = db.get_training_fee(training_id)
            db.add_payment(user_id, -fee, db.get_training_date(training_id))

@dp.message(Command('pay'))
async def cmd_pay(message: Message):
    args = message.text.split(maxsplit=1)
    if len(args) < 2:
        await message.answer("Формат: /pay сумма")
        return
    try:
        amount = float(args[1])
        if db.add_payment(message.from_user.id, amount):
            await message.answer("Оплата зарегистрирована.")
        else:
            await message.answer("Вы не зарегистрированы.")
    except ValueError:
        await message.answer("Укажите корректную сумму.")

@dp.message(Command('balance'))
async def cmd_balance(message: Message):
    balance = db.calculate_balance(message.from_user.id)
    await message.answer(f"Ваш текущий баланс: {balance:.2f} руб.")

@dp.message(Command('all_balances'))
async def cmd_all_balances(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("Только администратор может выполнять эту команду.")
        return
    report = db.get_all_balances()
    await message.answer(report)

@dp.message(Command('set_initial_balance'))
async def cmd_set_initial_balance(message: Message):
    if not db.is_admin(message.from_user.id):
        await message.answer("Только администратор может выполнять эту команду.")
        return
    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("Формат: /set_initial_balance TelegramID сумма")
        return
    try:
        telegram_id = int(args[1])
        balance = float(args[2])
        db.set_initial_balance(telegram_id, balance)
        await message.answer("Начальный баланс установлен.")
    except ValueError:
        await message.answer("Укажите корректные данные.")

async def main():
    # Start polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

