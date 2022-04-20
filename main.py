import config
import sqlite3
from numpy import rot90

from telegram import (
    Update
    )

from telegram.ext import (
    Updater,
    Dispatcher,
    CallbackContext,
    CommandHandler
    )

# Подключиться к базе данных, создать курсор для работы с ней.
connection = sqlite3.connect('users.db', check_same_thread=False)
cur = connection.cursor()
# Создать таблицу в бд.
cur.execute('CREATE TABLE IF NOT EXISTS main'
            '(username STR, id INTEGER, send_daily INTEGER, time INTEGER, '
            'photo_type STR, send_quote INTEGER)')

for row in cur.execute('SELECT * FROM main'):
    print(row)

# Updater получает обнолвения из тг и передает их в dispatcher.
# Dispatcher обрабатывает обновления.
updater = Updater(token=config.TOKEN)
dispatcher = updater.dispatcher


def start(update: Update, context: CallbackContext):
    """ Первая функция для всех пользователей """
    
    # Приветственное сообщение
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=config.start_text)
    

    # Если уже есть записанные в бд id, то вернуть их.
    if list(cur.execute('SELECT * FROM main')):
        used_ids = list(rot90(list(cur.execute('SELECT * FROM main')), axes=[1, 0])[1])
    else:
        used_ids = []

    # Если нет id человека в списке, то записать в бд id и ник
    if str(update.effective_chat.id) not in used_ids:
        cur.execute("insert into main values (?, ?, ?, ?, ?, ?)",
                    (
                        update.effective_chat.username,
                        update.effective_chat.id,
                        0, 0, 'None', 0)
                    )
        connection.commit()



start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)
updater.start_polling()
