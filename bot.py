import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PollAnswer
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN
from database import Database

# Initialize Bot, Dispatcher, and FSM Storage
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
db = Database()

# Create a router for handling callback queries
router = Router()
dp.include_router(router)

# Define states for poll creation
class PollCreation(StatesGroup):
    waiting_for_date = State()
    waiting_for_time = State()
    waiting_for_location = State()
    waiting_for_fee = State()

# Define states for payment process
class PaymentProcess(StatesGroup):
    waiting_for_amount = State()

# Helper function to create an inline keyboard with buttons
def create_inline_keyboard(buttons: list) -> InlineKeyboardMarkup:
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=text, callback_data=data)] for text, data in buttons
    ])
    return keyboard

@dp.message(Command('start'))
async def cmd_start(message: Message):
    participant = db.get_participant(message.from_user.id)
    if not participant:
        db.add_participant(message.from_user.id, message.from_user.full_name)
        await message.answer("Вы успешно зарегистрированы.")
    else:
        await message.answer("Вы уже зарегистрированы.")

    # Add buttons for various actions
    buttons = [
        ("Проверить баланс", "check_balance"),
        ("Создать опрос", "create_poll"),
        ("Оплатить", "pay")
    ]
    
    # Add admin-specific buttons
    if db.is_admin(message.from_user.id):
        buttons.extend([
            ("Баланс всех участников", "all_balances"),
            ("Сменить администратора", "set_admin"),
            ("Список участников", "list_participants"),
            ("Установить начальный баланс", "set_initial_balance")
        ])

    keyboard = create_inline_keyboard(buttons)
    await message.answer("Выберите действие:", reply_markup=keyboard)

@router.callback_query(lambda c: c.data == 'check_balance')
async def process_check_balance_callback(callback_query: CallbackQuery):
    balance = db.calculate_balance(callback_query.from_user.id)
    await bot.answer_callback_query(callback_query.id)
    await bot.send_message(callback_query.from_user.id, f"Ваш текущий баланс: {balance:.2f} руб.")

@router.callback_query(lambda c: c.data == 'create_poll')
async def start_poll_creation(callback_query: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Введите дату для тренировки (например, 2024-11-18) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_date)

@dp.message(PollCreation.waiting_for_date)
async def poll_date_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    await state.update_data(date=message.text)
    await message.answer("Введите время для тренировки (например, 18:00) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_time)

@dp.message(PollCreation.waiting_for_time)
async def poll_time_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    await state.update_data(time=message.text)
    await message.answer("Введите место для тренировки (например, спортивный зал) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_location)

@dp.message(PollCreation.waiting_for_location)
async def poll_location_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    await state.update_data(location=message.text)
    await message.answer("Введите стоимость тренировки (например, 500) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_fee)

@dp.message(PollCreation.waiting_for_fee)
async def poll_fee_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    try:
        fee = float(message.text)
    except ValueError:
        await message.answer("Стоимость должна быть числом. Попробуйте еще раз.")
        return

    await state.update_data(fee=fee)
    user_data = await state.get_data()
    date = user_data['date']
    time = user_data['time']
    location = user_data['location']
    fee = user_data['fee']

    # Create poll
    poll_question = f"Тренировка {date} в {time} на {location}. Стоимость: {fee} руб."
    poll_options = ["Смогу", "Приду с другом", "Не смогу", "Не определился"]
    poll_message = await bot.send_poll(
        message.chat.id,
        question=poll_question,
        options=poll_options,
        is_anonymous=False,
        allows_multiple_answers=False
    )

    # Save poll to the database
    training_id = db.add_training(date, time, location, fee)
    db.link_poll_to_training(training_id, poll_message.poll.id)

    await message.answer("Опрос создан успешно!")
    await state.clear()

@router.callback_query(lambda c: c.data == 'pay')
async def start_payment_process(callback_query: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Введите сумму для оплаты или /cancel для выхода:")
    await state.set_state(PaymentProcess.waiting_for_amount)

@dp.message(PaymentProcess.waiting_for_amount)
async def payment_amount_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Процесс оплаты отменен.")
        return
    try:
        amount = float(message.text)
        if db.add_payment(message.from_user.id, amount):
            await message.answer("Оплата зарегистрирована.")
        else:
            await message.answer("Вы не зарегистрированы.")
    except ValueError:
        await message.answer("Укажите корректную сумму.")
    await state.clear()

@router.callback_query(lambda c: c.data == 'all_balances')
async def process_all_balances_callback(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        report = db.get_all_balances()
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, report)
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'set_admin')
async def process_set_admin_callback(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Введите Telegram ID нового администратора в формате: /set_admin TelegramID")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'list_participants')
async def list_participants(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        participants = db.get_all_participants()
        participant_list = "\n".join([f"{name} - {telegram_id}" for name, telegram_id in participants])
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, f"Список участников:\n{participant_list}")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'set_initial_balance')
async def set_initial_balance_prompt(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Введите Telegram ID и начальный баланс в формате: /set_initial_balance TelegramID сумма")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

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
            if db.add_payment(user_id, -fee, db.get_training_date(training_id)):
                await bot.send_message(user_id, f"Вы записаны на тренировку. С вашего счета списано {fee} руб.")

@dp.message(Command('balance'))
async def cmd_balance(message: Message):
    balance = db.calculate_balance(message.from_user.id)
    await message.answer(f"Ваш текущий баланс: {balance:.2f} руб.")

@dp.message(Command('all_balances'))
async def cmd_all_balances(message: Message):
    if db.is_admin(message.from_user.id):
        report = db.get_all_balances()
        await message.answer(report)
    else:
        await message.answer("Только администратор может выполнять эту команду.")

@dp.message(Command('set_initial_balance'))
async def cmd_set_initial_balance(message: Message):
    if db.is_admin(message.from_user.id):
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
    else:
        await message.answer("Только администратор может выполнять эту команду.")

async def main():
    # Start polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

