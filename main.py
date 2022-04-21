import config
import sqlite3
from re import fullmatch
from numpy import rot90
from os import listdir


from telegram import (
    Update
    )

from telegram.ext import (
    Updater,
    CallbackContext,
    CommandHandler
    )

pic_types = listdir(path="pics")

# Подключиться к базе данных, создать курсор для работы с ней.
connection = sqlite3.connect('users.db', check_same_thread=False)
cur = connection.cursor()
# Создать таблицу в бд.
cur.execute('CREATE TABLE IF NOT EXISTS main'
            '(username STR, id INTEGER, send_daily INTEGER, time STRING, '
            'photo_type STR, send_quote STR)')

# Updater получает обнолвения из тг и передает их в dispatcher.
# Dispatcher обрабатывает обновления.
updater = Updater(token=config.TOKEN)
dispatcher = updater.dispatcher

for row in cur.execute('SELECT * FROM main'):
    print(row)


def isTimeFormat(input_):
    """Проверка, является ли строка временем"""
    tmp = input_.split(':')
    # Проверка на формат и число до двоеточия.
    if fullmatch('[0-2]\d:[0-5]\d', input_) and int(tmp[0]) < 23:
        return True
    else:
        return False


def start(update: Update, context: CallbackContext):
    """ Первая функция для всех пользователей """
    
    # Приветственное сообщение
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text=config.start_text)
    
    # Если уже есть записанные в бд id, то засунуть их в список.
    used_ids = []
    if cur.execute('SELECT * FROM main').fetchone():
        used_ids = list(
            rot90(list(cur.execute('SELECT * FROM main')), axes=[1, 0])[1])
    
    # Если нет id человека в списке, то записать в бд id и ник
    if str(update.effective_chat.id) not in used_ids:
        cur.execute("insert into main values (?, ?, ?, ?, ?, ?)",
                    (
                        update.effective_chat.username,
                        update.effective_chat.id,
                        0, 0, 'None', 0)
                    )
        connection.commit()


def add_profile_data(update: Update, context: CallbackContext):
    """Запись в бд данных о пользователе"""
    
    args = context.args
    
    # Прекратить функцию если аргументы некорректны.
    if len(args) != 3 or not isTimeFormat(args[0]) or args[1] not \
            in pic_types or args[2] not in ('да', 'нет'):
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text='Вы ввели некорректные агрументы. \n'
                                      'Правильный вариант: \n'
                                      '[часы:минуты] [тип пикчи] [да\нет]')
        return
    
    # Если корректны, то записать их в бд.
    cur.execute("UPDATE main SET "
                "send_daily = 1, time=:time, "
                "photo_type=:type, send_quote=:quote",
                {'time': args[0], 'type': args[1], 'quote': args[2]})
    connection.commit()
    
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text='Ваш профиль рассылки успешно обновлен.')


if __name__ == "__main__":
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('profile', add_profile_data))
    
    updater.start_polling()
