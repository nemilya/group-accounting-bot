import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton, PollAnswer
from aiogram.dispatcher.router import Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from config import API_TOKEN, GROUP_CHAT_ID
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

@dp.message(Command('get_group_id'))
async def cmd_get_group_id(message: Message):
    chat_id = message.chat.id
    await message.answer(f"ID этой группы: {chat_id}")

@dp.message(Command('start'), lambda message: message.chat.type == 'private')
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
        ("Сообщить об оплате", "pay")
    ]
    
    # Add admin-specific buttons
    if db.is_admin(message.from_user.id):
        buttons.extend([
            ("Создать опрос", "create_poll"),
            ("Баланс всех участников", "all_balances"),
            ("Добавить администратора", "set_admin"),
            ("Список участников", "list_participants"),
            ("Установить начальный баланс", "set_initial_balance"),
            ("Список тренировок", "list_trainings"),
            ("Списать средства за тренировку", "debit_funds")
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
    participant = db.get_participant(callback_query.from_user.id)
    if not participant:
        await callback_query.message.answer("Вы не зарегистрированы. Пожалуйста, нажмите /start для регистрации.")
        return

    await callback_query.message.answer("Введите дату для тренировки (например, 2024-11-18) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_date)

@dp.message(PollCreation.waiting_for_date, lambda message: message.chat.type == 'private')
async def poll_date_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    await state.update_data(date=message.text)
    await message.answer("Введите время для тренировки (например, 18:00) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_time)

@dp.message(PollCreation.waiting_for_time, lambda message: message.chat.type == 'private')
async def poll_time_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    await state.update_data(time=message.text)
    await message.answer("Введите место для тренировки (например, спортивный зал) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_location)

@dp.message(PollCreation.waiting_for_location, lambda message: message.chat.type == 'private')
async def poll_location_received(message: Message, state: FSMContext):
    if message.text.lower() == '/cancel':
        await state.clear()
        await message.answer("Создание опроса отменено.")
        return
    await state.update_data(location=message.text)
    await message.answer("Введите стоимость тренировки (например, 500) или /cancel для выхода:")
    await state.set_state(PollCreation.waiting_for_fee)

@dp.message(PollCreation.waiting_for_fee, lambda message: message.chat.type == 'private')
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

    # Create poll
    poll_question = f"Тренировка {date} в {time} на {location}. Стоимость: {fee} руб."
    poll_options = ["Смогу", "Приду с другом", "Не смогу", "Не определился"]

    # Send poll to the group
    poll_message = await bot.send_poll(
        GROUP_CHAT_ID,
            question=poll_question,
            options=poll_options,
            is_anonymous=False,
            allows_multiple_answers=False
    )

    # Save poll to the database
    training_id = db.add_training(date, time, location, fee)
    db.link_poll_to_training(training_id, poll_message.poll.id)

    await message.answer("Опрос создан и отправлен всем участникам!")
    await state.clear()

@router.callback_query(lambda c: c.data == 'pay')
async def start_payment_process(callback_query: CallbackQuery, state: FSMContext):
    await bot.answer_callback_query(callback_query.id)
    await callback_query.message.answer("Введите сумму для оплаты или /cancel для выхода:")
    await state.set_state(PaymentProcess.waiting_for_amount)

@dp.message(PaymentProcess.waiting_for_amount, lambda message: message.chat.type == 'private')
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

@dp.message(Command('set_admin'), lambda message: message.chat.type == 'private')
async def cmd_set_admin(message: Message):
    if db.is_admin(message.from_user.id):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Формат: /set_admin UserID")
            return
        try:
            new_admin_user_id = int(args[1])
            db.set_admin_by_user_id(new_admin_user_id)
            await message.answer("Администратор успешно добавлен.")
            await bot.send_message(new_admin_user_id, "Вы были назначены администратором.")
        except ValueError:
            await message.answer("Укажите корректный UserID.")
    else:
        await message.answer("Только администратор может выполнять эту команду.")

@router.callback_query(lambda c: c.data == 'set_admin')
async def handle_set_admin_callback(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Чтобы добавить администратора, используйте команду:\n/set_admin UserID")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'list_participants')
async def list_participants(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        participants = db.get_all_participants()
        participant_list = "\n".join([
            f"{name} - [{user_id}]" + (" (Администратор)" if db.is_admin(telegram_id) else "")
            for name, user_id, telegram_id in participants
        ])
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, f"Список участников:\n{participant_list}")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'set_initial_balance')
async def set_initial_balance_prompt(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Введите UserID и начальный баланс в формате: /set_initial_balance UserID сумма")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'list_trainings')
async def list_trainings(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        trainings = db.get_all_trainings()
        training_list = []
        for training_id, date, time, location, fee, is_funds_debited in trainings:
            participants = db.execute(
                "SELECT p.name, r.status FROM training_registrations r JOIN participants p ON r.participant_id = p.id WHERE r.training_id = ?",
                (training_id,), fetchall=True
            )
            participant_list = ", ".join([
                f"{name}{' (с другом)' if status == 'приду с другом' else ''}"
                for name, status in participants if status in ['смогу', 'приду с другом']
            ])
            total_cost = sum(fee * (2 if status == 'приду с другом' else 1) for _, status in participants if status in ['смогу', 'приду с другом'])
            training_list.append(
                f"[{training_id}] {date}, {time}, {location}, {fee} руб. | Участники: {participant_list} | Итоговая стоимость: {total_cost} руб. | Средства списаны: {'Да' if is_funds_debited else 'Нет'}"
            )
        training_list = "\n".join(training_list)
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, f"Список тренировок:\n{training_list}")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@router.callback_query(lambda c: c.data == 'debit_funds')
async def handle_debit_funds_callback(callback_query: CallbackQuery):
    if db.is_admin(callback_query.from_user.id):
        await bot.answer_callback_query(callback_query.id)
        await bot.send_message(callback_query.from_user.id, "Введите ID тренировки для списания средств в формате: /debit_funds TrainingID")
    else:
        await bot.answer_callback_query(callback_query.id, "У вас нет прав для выполнения этой команды.")

@dp.poll_answer()
async def handle_poll_answer(poll_answer: PollAnswer):
    print(f"Received poll answer from user {poll_answer.user.id}")
    participant = db.get_participant(poll_answer.user.id)
    if not participant:
        return

    user_id = poll_answer.user.id
    poll_id = poll_answer.poll_id
    status_index = poll_answer.option_ids[0]
    status_mapping = {0: 'смогу', 1: 'приду с другом', 2: 'не смогу', 3: 'не определился'}
    status_text = status_mapping.get(status_index, 'не определился')

    training_id = db.get_training_id_by_poll(poll_id)
    if training_id:
        db.update_registration(user_id, training_id, status_text)

@dp.message(Command('balance'), lambda message: message.chat.type == 'private')
async def cmd_balance(message: Message):
    balance = db.calculate_balance(message.from_user.id)
    await message.answer(f"Ваш текущий баланс: {balance:.2f} руб.")

@dp.message(Command('all_balances'), lambda message: message.chat.type == 'private')
async def cmd_all_balances(message: Message):
    if db.is_admin(message.from_user.id):
        report = db.get_all_balances()
        await message.answer(report)
    else:
        await message.answer("Только администратор может выполнять эту команду.")

@dp.message(Command('set_initial_balance'), lambda message: message.chat.type == 'private')
async def cmd_set_initial_balance(message: Message):
    if db.is_admin(message.from_user.id):
        args = message.text.split(maxsplit=2)
        if len(args) < 3:
            await message.answer("Формат: /set_initial_balance UserID сумма")
            return
        try:
            user_id = int(args[1])
            balance = float(args[2])
            db.set_initial_balance_by_user_id(user_id, balance)
            await message.answer("Начальный баланс установлен.")
        except ValueError:
            await message.answer("Укажите корректные данные.")
    else:
        await message.answer("Только администратор может выполнять эту команду.")

@dp.message(Command('list_trainings'), lambda message: message.chat.type == 'private')
async def cmd_list_trainings(message: Message):
    if db.is_admin(message.from_user.id):
        trainings = db.get_all_trainings()
        training_list = "\n".join([
            f"ID: {training_id}, Дата: {date}, Время: {time}, Место: {location}, Стоимость: {fee} руб."
            for training_id, date, time, location, fee in trainings
        ])
        await message.answer(f"Список тренировок:\n{training_list}")
    else:
        await message.answer("Только администратор может выполнять эту команду.")

@dp.message(Command('debit_funds'), lambda message: message.chat.type == 'private')
async def cmd_debit_funds(message: Message):
    if db.is_admin(message.from_user.id):
        args = message.text.split(maxsplit=1)
        if len(args) < 2:
            await message.answer("Формат: /debit_funds TrainingID")
            return
        try:
            training_id = int(args[1])
            if db.debit_funds_for_training(training_id):
                await message.answer("Средства успешно списаны за тренировку.")
            else:
                await message.answer("Не удалось списать средства. Возможно, они уже списаны.")
        except ValueError:
            await message.answer("Укажите корректный TrainingID.")
    else:
        await message.answer("Только администратор может выполнять эту команду.")

async def main():
    # Start polling
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
