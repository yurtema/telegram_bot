import config
import sqlite3
import re
from time import sleep
from numpy import rot90
from os import listdir
from random import choice
from schedule import every, run_pending, clear

from telegram import (
    Update,
    Bot,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove
    )

from telegram.ext import (
    Filters,
    Updater,
    CallbackContext,
    CommandHandler,
    MessageHandler,
    ConversationHandler
    )

ASK_TIME, CHECK_TIME, CHECK_TYPE, CHECK_QUOTE = range(4)


def isTimeFormat(input_):
    """Проверка, является ли строка временем"""
    
    hours = input_.split(':')[0]
    if re.fullmatch('[0-2]\d:[0-5]\d', input_) and int(hours) < 23:
        return True
    else:
        return False


def send_picture(person_id: int, pic_type: str, daily=0, quote='нет'):
    """ Отправка фото заданного типа """
    
    # Открытие рандомное фото из заданной дирректории.
    pic = open('pics/' + pic_type + '/' +
               choice(listdir('pics/' + pic_type)), 'rb')
    
    if daily:
        bot.send_message(person_id, 'Ваша рассылка на месте')
    
    bot.send_photo(person_id, pic)
    
    if quote == 'да':
        bot.send_photo(person_id, pic, caption=choice(config.auf))


def start_handler(update: Update, context: CallbackContext):
    """ Первая функция для всех пользователей """
    
    # Приветственное сообщение
    update.message.reply_text(config.start_text)
    
    # Запись в список id пользователей если такие есть.
    used_ids = []
    if cur.execute('SELECT * FROM main').fetchone():
        used_ids = list(
            rot90(list(cur.execute('SELECT * FROM main')), axes=[1, 0])[1])
    
    # Если нет id человека в списке, то запись в бд его id и ник
    if str(update.effective_chat.id) not in used_ids:
        cur.execute("insert into main values (?, ?, ?, ?, ?, ?)",
                    (
                        update.effective_chat.username,
                        update.effective_chat.id,
                        0, 0, 'None', 0)
                    )
        connection.commit()


def delete_profile_handler(update: Update, context: CallbackContext):
    """ Удаление профиля рассылки """
    
    # Удаление данных из бд
    cur.execute("UPDATE main SET "
                "send_daily = 0, time=' ', "
                "photo_type=' ', send_quote=' ' WHERE id = :id",
                {'id': update.effective_chat.id})
    connection.commit()
    
    # Пересоздание работ.
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
    """ Админ команды """
    
    # Проверка личности
    if update.effective_chat.id != 900808541:
        update.message.reply_text('Ты не пахнешь как мой хоязин.')
        return
    
    arg = context.args[0]
    
    # Вывод бд в личку админу.
    if arg == 'список':
        for i in cur.execute('SELECT * FROM main'):
            update.message.reply_text(str(i[0]) + ' ' + str(i[3]) + ' ' +
                                      str(i[4]) + ' ' + str(i[5]))
    
    # Отправка сообщения от имени бота всем пользователям.
    elif arg == 'сказать':
        line = ''
        for i in range(1, len(context.args)):
            line += context.args[i] + ' '
        for i in cur.execute('SELECT id FROM main WHERE id != '):
            bot.send_message(i[0], line)
    else:
        update.message.reply_text(
            'Самому написать бота и не знать команды.....')


def profile_handler(update: Update, context: CallbackContext):
    """
    Срабатывает при вызове функции /profile.
    Если аргументы корректны, то сразу записывает их в базу данных.
    В противном случае выводится профиль пользователся.
    Если его нет, то запускается диалог.
    """
    args = context.args
    
    # Проверка на корректность аргументов.
    if len(args) == 3 and isTimeFormat(args[0]) and args[1] \
            in pic_types and args[2] in ('да', 'нет'):
        
        # Запись в бд
        time, pic_type, quote = args
        cur.execute("UPDATE main SET "
                    "send_daily = 1, time=:time, "
                    "photo_type=:type, send_quote=:quote WHERE id = :id",
                    {'time': time, 'type': pic_type, 'quote': quote,
                     'id': update.effective_chat.id})
        connection.commit()
        
        # Заново создание работ.
        clear()
        for row in cur.execute('SELECT * FROM main'):
            if row[2]:
                every().day.at(row[3]).do(send_picture, row[1], row[4], 1,
                                          row[5])
        
        bot.send_message(update.effective_message.chat_id,
                         'Ваш профиль рассылки успешно обновлен.')
        
        # Выход из ветки диалога.
        return ConversationHandler.END
    
    nickname, person_id, send_daily, time, pic_type, quote = \
        cur.execute('SELECT * FROM main WHERE id = :id',
                    {'id': update.effective_chat.id}).fetchone()
    
    # Вывод профиля пользователя если подписан на рассылку.
    if send_daily:
        if quote == 'да':
            update.message.reply_text('Ваш профиль рассылки: %s в %s с цитатой'
                                      % (pic_type, time))
        else:
            update.message.reply_text('Ваш профиль рассылки: %s в %s'
                                      % (pic_type, time))
        return ConversationHandler.END
    
    # Если нет, начало диалога.
    update.message.reply_text('У вас нет профиля рассылки, хотите создать?',
                              reply_markup=ReplyKeyboardMarkup(
                                  [['да', 'нет']], one_time_keyboard=True,
                                  input_field_placeholder=
                                  ''
                                  ))
    return ASK_TIME


def ask_time(update: Update, context: CallbackContext):
    """ Запрос времени """
    update.message.reply_text('Во сколько хотите рассылку?',
                              reply_markup=ReplyKeyboardRemove()
                              )
    return CHECK_TIME


def check_time(update: Update, context: CallbackContext):
    """ Проверка времени и запрос типа фото"""
    global tmp
    msg = update.message.text
    if isTimeFormat(msg):
        update.message.reply_text('Какой тип фото желаете?',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [pic_types], one_time_keyboard=True,
                                      input_field_placeholder=
                                      ''
                                      ))
        
        tmp.append(msg)
        return CHECK_TYPE
    update.message.reply_text('Вы ввели некорректный аргумент')
    return ConversationHandler.END


def check_type(update: Update, context: CallbackContext):
    """ Проверка типа фото и запрос цитаты """
    global tmp
    msg = update.message.text
    if msg in pic_types:
        tmp.append(msg)
        update.message.reply_text('Присылать цитату?',
                                  reply_markup=ReplyKeyboardMarkup(
                                      [['да', 'нет']], one_time_keyboard=True,
                                      input_field_placeholder=
                                      ''
                                      ))
        return CHECK_QUOTE
    update.message.reply_text('Вы ввели некорректный аргумент')
    return ConversationHandler.END


def check_quote(update: Update, context: CallbackContext):
    """ Проверка цитаты и запись данных в бд """
    global tmp
    msg = update.message.text
    if msg in ('да', 'нет'):
        tmp.append(msg)
        update.message.reply_text('Записываю ваш профиль....',
                                  reply_markup=ReplyKeyboardRemove())

        # Запись данных в бд.
        cur.execute("UPDATE main SET "
                    "send_daily = 1, time=:time, "
                    "photo_type=:type, send_quote=:quote WHERE id = :id",
                    {'time': tmp[0], 'type': tmp[1], 'quote': tmp[2],
                     'id': update.effective_chat.id})
        connection.commit()
        tmp = []

        # Пересоаздание всех работ.
        clear()
        for row in cur.execute('SELECT * FROM main WHERE send_daily = 1'):
            every().day.at(row[3]).do(send_picture, row[1], row[4], 1, row[5])
        
        bot.send_message(update.effective_message.chat_id,
                         'Ваш профиль рассылки успешно записан.')
        return ConversationHandler.END
    
    update.message.reply_text('Вы ввели некорректный аргумент')
    return ConversationHandler.END


def cancel(update: Update, context: CallbackContext):
    """ Выход из диалога """
    update.message.reply_text(':)')
    return ConversationHandler.END


if __name__ == "__main__":
    
    pic_types = listdir(path="pics")
    bot = Bot(config.TOKEN)
    tmp = []
    
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
    
    # Диалог
    dispatcher.add_handler(ConversationHandler(
        entry_points=[CommandHandler('profile', profile_handler)],
        states={
            ASK_TIME: [MessageHandler(Filters.text('да'), ask_time),
                       MessageHandler(Filters.text('нет'), cancel)],
            CHECK_TIME: [MessageHandler(Filters.text, check_time)],
            CHECK_TYPE: [MessageHandler(Filters.text, check_type)],
            CHECK_QUOTE: [MessageHandler(Filters.text, check_quote)]
            },
        fallbacks=[CommandHandler('cancel', cancel)]
        ))
    
    # Привязка команд к функциям.
    dispatcher.add_handler(
        CommandHandler('start', start_handler))
    dispatcher.add_handler(
        CommandHandler('help', help_handler))
    dispatcher.add_handler(
        CommandHandler('delete_profile', delete_profile_handler))
    dispatcher.add_handler(
        CommandHandler('admin', admin_handler))
    
    # Привязка типов фоток к функции.
    for i in pic_types:
        dispatcher.add_handler(
            MessageHandler(Filters.regex(re.compile(i, re.IGNORECASE)),
            picture_command_handler))
    
    # Вывод при неизвестной команде.
    dispatcher.add_handler(
        MessageHandler(Filters.text | Filters.command, exception_handler))

    # Запуск бота.
    updater.start_polling()
    print('Bot online')

    # Проверка времени для всех работ раз в 10 секунд.
    while True:
        sleep(10)
        run_pending()
