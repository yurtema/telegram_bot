import config
import sqlite3
from re import fullmatch
from time import sleep
from numpy import rot90
from os import listdir
from random import choice
from schedule import every, run_pending, clear

from telegram import (
    Update,
    Bot
    )

from telegram.ext import (
    Filters,
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler
    )


def isTimeFormat(input_):
    """Проверка, является ли строка временем"""
    tmp = input_.split(':')
    # Проверка на формат и число до двоеточия.
    if fullmatch('[0-2]\d:[0-5]\d', input_) and int(tmp[0]) < 23:
        return True
    else:
        return False


def send_picture(person_id: int, pic_type: str,
                 daily: bool = 0, quote: str = 'нет'):
    """Отправка фото заданного типа"""
    
    # Открытие рандомное фото из заданной дирректории.
    pic = open('pics/' + pic_type + '/' +
               choice(listdir('pics/' + pic_type)), 'rb')
    
    if daily:
        bot.send_message(person_id, 'Ваша рассылка на месте')
    if quote == 'да':
        bot.send_photo(person_id, pic, caption=choice(config.auf))
    else:
        bot.send_photo(person_id, pic)


def start(update: Update, context: CallbackContext):
    """ Первая функция для всех пользователей """
    
    # Приветственное сообщение
    update.message.reply_text(config.start_text)
    
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
        bot.send_message(update.effective_chat.id,
                         config.wrong_profile_args_text)
        return
    
    # Если корректны, то записать их в бд.
    time, pic_type, quote = args
    cur.execute("UPDATE main SET "
                "send_daily = 1, time=:time, "
                "photo_type=:type, send_quote=:quote WHERE id = :id",
                {'time': time, 'type': pic_type, 'quote': quote,
                 'id': update.effective_chat.id})
    connection.commit()
    
    clear()
    for row in cur.execute('SELECT * FROM main'):
        if row[2]:
            every().day.at(row[3]).do(send_picture, row[1], row[4], 1, row[5])
    
    bot.send_message(update.effective_message.chat_id,
                     'Ваш профиль рассылки успешно обновлен.')


def delete_profile(update: Update, context: CallbackContext):
    cur.execute("UPDATE main SET "
                "send_daily = 0, time=' ', "
                "photo_type=' ', send_quote=' ' WHERE id = :id",
                {'id': update.effective_chat.id})
    clear()
    for row in cur.execute('SELECT * FROM main WHERE send_daily = 1'):
        every().day.at(row[3]).do(send_picture, row[1], row[4], 1, row[5])
    update.message.reply_text('Ваш профиль успешно удален')


def exception_handler(update: Update, context: CallbackContext):
    """Вывод текста при нераспознании команды"""
    update.message.reply_text(config.exception_text)


def picture_command_handler(update: Update, context: CallbackContext):
    """Функция обработчик запроса картинки"""
    send_picture(update.effective_chat.id, update.message.text)


def help_handler(update: Update, context: CallbackContext):
    """Функция обработчик запроса списка команд"""
    update.message.reply_text(config.help_text)


def admin_handler(update: Update, context: CallbackContext):
    if update.effective_chat.id != 900808541:
        update.message.reply_text('Ты не пахнешь как мой хоязин.')
        return
    
    arg = context.args[0]
    
    if arg == 'список':
        for i in cur.execute('SELECT * FROM main'):
            update.message.reply_text(str(i[0]) + ' ' + str(i[3]) + ' ' +
                                      str(i[4]) + ' ' + str(i[5]))
    elif arg == 'сказать':
        line = ''
        for i in range(1, len(context.args)):
            line += context.args[i] + ' '
        for i in cur.execute('SELECT id FROM main'):
            bot.send_message(i[0], line)
    else:
        update.message.reply_text(
            'Самому написать бота и не знать команды.....')


if __name__ == "__main__":
    
    pic_types = listdir(path="pics")
    bot = Bot(config.TOKEN)
    
    # Подключиться к базе данных, создать курсор для работы с ней.
    connection = sqlite3.connect('users.db', check_same_thread=False)
    cur = connection.cursor()
    # Создать таблицу в бд.
    cur.execute('CREATE TABLE IF NOT EXISTS main'
                '(username STR, id INTEGER, send_daily INTEGER, time STRING, '
                'photo_type STR, send_quote STR)')
    # Вывести бд
    for row in cur.execute('SELECT * FROM main'):
        print(row)
    
    # Создать по задаче для каждой строки бд с подпиской на рассылку.
    for row in cur.execute('SELECT * FROM main WHERE send_daily = 1'):
        every().day.at(row[3]).do(send_picture, row[1], row[4], 1, row[5])
    
    # Updater получает обнолвения из тг и передает их в dispatcher.
    # Dispatcher обрабатывает обновления.
    updater = Updater(token=config.TOKEN)
    dispatcher = updater.dispatcher
    
    dispatcher.add_handler(CommandHandler('start', start))
    dispatcher.add_handler(CommandHandler('help', help_handler))
    dispatcher.add_handler(CommandHandler('profile', add_profile_data))
    dispatcher.add_handler(CommandHandler('delete_profile', delete_profile))
    dispatcher.add_handler(CommandHandler('admin', admin_handler))
    dispatcher.add_handler(MessageHandler(
        Filters.text(pic_types) & ~Filters.command, picture_command_handler))
    
    dispatcher.add_handler(MessageHandler(
        Filters.text | Filters.command, exception_handler))
    
    updater.start_polling()
    print('Bot online')
    
    while True:
        sleep(10)
        run_pending()
