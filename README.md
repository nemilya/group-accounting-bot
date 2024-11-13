# Group Accounting Bot

This is a Telegram bot for managing group balances related to training sessions and payments.

## Features

- Register participants and track their balances
- Admin can create polls for training sessions
- Track payments and calculate balances
- Set initial balances for users

## Setup

1. Clone the repository.
2. Install:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create and setup db:
   ```bash
   python initialize_db.py
   ```
4. Create TG bot in @BotFather, setup token in `.env`
5. Start:
   ```bash
   python3 bot.py
   ```

