import os
import pickle
import telebot
import knowledge
import emoji
import json
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler


BOT_TOKEN = knowledge.BOT_TOKEN_TEST
bot = telebot.TeleBot(BOT_TOKEN)

scheduler = BackgroundScheduler()
scheduler.start()


# List of commands
@bot.message_handler(commands=['help'])
def send_help(message):
    bot.reply_to(message,
                 "Список комманд: \n"
                 "/help - Узнать команды :)\n"
                 "/hello - Скажите мне привет :)\n"
                 "/monday - Запустить опросы на Понедельник по расписанию\n"
                 "/thursday - Запустить опросы на Четверг по расписанию\n"
                 "/nomonday,/nothursday - Остановить соответствующие расписания\n"
                 "/create <Poll Message> - Создать опрос вручную\n"
                 "/stop - Остановить существующий опрос\n"
                 "/stopper - Автоматическая остановка опросов по расписанию\n"
                 "/halt - Отмена автоматической остановки\n"
                 "/deploy - Полный старт. Запуск всех расписаний, в том числе и остановки\n"
                 "/kill - Полная остановка всех расписаний\n"
                 "/users - Получить информацию о игроках\n"
                 "/days - Статистика по дням")


# Say hi to the Bot
@bot.message_handler(commands=['hello'])
def send_welcome(message):
    commandlogger(message)
    bot.reply_to(message, "Приветик")


# Get Users
@bot.message_handler(commands=['users'])
def get_users(message):
    commandlogger(message)
    user = message.from_user.username
    chat_id = message.chat.id

    msg = ""

    # Check Admin
    if user in knowledge.Admins:
        with open('users.json', 'r') as f:
            users = json.load(f, object_hook=keystoint)

        for u, logs in users.items():
            us = bot.get_chat_member(-598933221, u).user
            msg += "| {}({}): {} |".format(us.full_name, us.id, logs)
        bot.reply_to(message, msg)
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для этого")


# New and removed Users
@bot.message_handler(content_types=["new_chat_members"])
def greet_user(message):

    # Add a new user to a list
    with open('users.json', 'r') as f:
        users = json.load(f, object_hook=keystoint)

    for u in message.new_chat_members:
        # Greet new user
        user = u.id
        nickname = u.full_name
        bot.reply_to(message, "Welcome, {}".format(nickname))
        users.update({user: [0, 0]})

    with open('users.json', 'w', encoding='windows-1251') as f:
        json.dump(users, f, ensure_ascii=False)


@bot.message_handler(content_types=["left_chat_member"])
def farewell_user(message):
    user = message.left_chat_member.id
    nickname = message.left_chat_member.full_name

    # Say goodbye to a user
    bot.reply_to(message, "Goodbye, {}".format(nickname))

    # Delete a lost user from a list
    with open('users.json', 'r') as f:
        users = json.load(f, object_hook=keystoint)
    users.pop(user)
    with open('users.json', 'w', encoding='windows-1251') as f:
        json.dump(users, f, ensure_ascii=False)


# Stats
@bot.message_handler(commands=['me'])
def get_stats(message):
    commandlogger(message)
    with open('users.json', 'r') as f:
        users = json.load(f, object_hook=keystoint)
        user = message.from_user.id
        try:
            strike = users[user][0]
            miss = users[user][1]
        except:
            # Add a new user to a list
            with open('users.json', 'r') as f:
                users = json.load(f, object_hook=keystoint)
            users.update({user: [0, 0]})
            with open('users.json', 'w', encoding='windows-1251') as f:
                json.dump(users, f, ensure_ascii=False)
            bot.reply_to(message, "Пропущено опросов подряд: {}\nПропущено игр подряд: {}".format(0, 0))
        else:
            bot.reply_to(message, "Пропущено опросов подряд: {}\nПропущено игр подряд: {}".format(strike, miss))


# Schedule polls stopper
@bot.message_handler(commands=['stopper'])
def start_stopper(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username

    # Check Admin
    if user in knowledge.Admins:
        bot.reply_to(message, "Теперь я сам буду останаваливать опросы")
        scheduler.add_job(stop_latest_poll, trigger='cron', day_of_week='mon,thu', hour=19, minute=30, id='stop_day', args=[message])
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Stop poll stopper
@bot.message_handler(commands=['halt'])
def stop_stopper(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username
    # Check Admin
    if user in knowledge.Admins:
        scheduler.remove_job('stop_day')
        bot.send_message(chat_id, "Теперь я не буду сам останаваливать опросы")
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


@bot.message_handler(commands=['deploy'])
def deploy_bot(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username
    # Check Admin
    if user in knowledge.Admins:
        scheduler.add_job(stop_latest_poll, trigger='cron', day_of_week='mon,thu', hour=19, minute=30, id='stop_day', args=[message])
        scheduler.add_job(create_m_poll, trigger='cron', day_of_week='sun', hour=12, minute=0, id='monday', args=[message])
        scheduler.add_job(create_t_poll, trigger='cron', day_of_week='wed', hour=12, minute=0, id='thursday', args=[message])
        scheduler.add_job(announce_player_amount, trigger='cron', day_of_week='mon', hour=12, minute=0, id='ann_monday', args=[message.chat.id])
        scheduler.add_job(announce_player_amount, trigger='cron', day_of_week='thu', hour=12, minute=0, id='ann_thursday',args=[message.chat.id])
        bot.send_message(chat_id, "Работаем!")
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


@bot.message_handler(commands=['kill'])
def kill_bot(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username

    if user in knowledge.Admins:
        scheduler.remove_job('stop_day')
        scheduler.remove_job('monday')
        scheduler.remove_job('thursday')
        scheduler.remove_job('ann_monday')
        scheduler.remove_job('ann_thursday')
        bot.send_message(chat_id, "Я спать.")
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Schedule polls creation for Monday
@bot.message_handler(commands=['monday'])
def start_schedule_m(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username

    # Check Admin
    if user in knowledge.Admins:
        bot.reply_to(message, "Опросы на понедельники будут создаваться по расписанию")
        scheduler.add_job(create_m_poll, trigger='cron', day_of_week='sun', hour=12, minute=0, id='monday', args=[message])
        scheduler.add_job(announce_player_amount, trigger='cron', day_of_week='mon', hour = 12, minute=0,id='ann_monday', args=[message.chat.id])
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Schedule polls creation for Thursday
@bot.message_handler(commands=['thursday'])
def start_schedule_t(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username

    # Check Admin
    if user in knowledge.Admins:
        bot.reply_to(message, "Опросы на четверги будут создаваться по расписанию")
        scheduler.add_job(create_t_poll, trigger='cron', day_of_week='wed', hour=12, minute=0, id='thursday', args=[message])
        scheduler.add_job(announce_player_amount, trigger='cron', day_of_week='thu', hour=12, minute=0, id='ann_thursday',args=[message.chat.id])

    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Stop Monday Schedule
@bot.message_handler(commands=['nomonday'])
def stop_schedule_m(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username
    # Check Admin
    if user in knowledge.Admins:
        scheduler.remove_job('monday')
        scheduler.remove_job('ann_monday')
        bot.send_message(chat_id, "Опросы на понедельники остановлены")
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Stop Thursday Schedule
@bot.message_handler(commands=['nothursday'])
def stop_schedule_t(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username
    # Check Admin
    if user in knowledge.Admins:
        scheduler.remove_job('thursday')
        scheduler.remove_job('ann_thursday')
        bot.send_message(chat_id, "Опросы на четверги остановлены")
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Check for users who didn't answer the poll
def get_poll_info(message, strikes, answers, playing):

    # Temporary variables
    chat_id = message.chat.id
    msg = ""
    bad_ucount = 0
    bad_string = ""
    bad_users = {}
    gamers = 0

    # Find bad users
    for u, strike in strikes.items():
        if u not in answers:
            bad_users[u] = [strike[0]+1, strike[1]+1]

    # Get bad users info
    for u, strike in bad_users.items():
        if strike[0] > 1:
            nickname = bot.get_chat_member(message.chat.id, u).user.full_name
            msg = msg + "\n{}: {}".format(nickname, strike[0])
            bad_ucount += 1

    # Send response
    bot.send_message(chat_id, "Опрос окончен")
    bot.send_message(chat_id, "Игроков: {}".format(playing))
    if bad_ucount > 0:
        bot.send_message(chat_id, 'Прогульщики: {}'.format(msg))
    else:
        bot.send_message(chat_id,
                         emoji.emojize('Все молодцы :smiling_face:'))

    # Track Strikes
    for u, miss in answers.items():
        if miss == 1:
            viewer = strikes[u][1] + 1
            strikes.update({u: [0, viewer]})
        else:
            gamers+=1
            strikes.update({u: [0, 0]})

    for u, strike in bad_users.items():
        strikes.update({u: strike})
        nickname = bot.get_chat_member(message.chat.id, u)
        bad_string += "{}: {}\n ".format(nickname.user.full_name, strike[0])

    # Logging
    file1 = open("PollLog.txt", "a")

    # Log date time
    file1.write(str(datetime.now()) + "\n")

    # Log Chat ID
    file1.write("Chat: " + str(chat_id) + "\n")

    # Log users that skipped and their strikes
    file1.write(bad_string)
    file1.write("\n\n--------------------------\n\n")
    file1.close()

    # Get weekday
    weekday = datetime.today().weekday()

    with open('days.json', 'r') as f:
        days = json.load(f)

    if weekday == 0:
        monday = days["monday"]
        monday[1] = round((monday[1] * monday[0] + gamers) / (monday[0]+1))
        monday[0] = monday[0] + 1
    elif weekday == 3:
        thursday = days["thursday"]
        thursday[1] = round((thursday[1] * thursday[0] + gamers) / (thursday[0] + 1))
        thursday[0] = thursday[0] + 1

    with open('days.json', 'w', encoding='windows-1251') as f:
        json.dump(days, f, ensure_ascii=False)

    with open(str(message.chat.id), 'wb') as f:
        pickle.dump([0, 0], f)

    with open('users.json', 'w', encoding='windows-1251') as f:
        json.dump(strikes, f, ensure_ascii=False)

# Get users who answered the poll
@bot.poll_answer_handler()
def track_user_answers(poll_answer):
    poll_id = poll_answer.poll_id
    user = poll_answer.user.id
    print(user)
    answers = {}
    playing = 0
    # Get Poll Data
    with open(str(poll_id), 'rb') as f:
        answers, playing, poll_msg = pickle.load(f)
    # Track answered users or remove them if they retracted their vote
    print(poll_answer.option_ids)
    if poll_answer.option_ids:
        if poll_answer.option_ids == [1] or poll_answer.option_ids == [2]:
            answers.update({user: 1})
        else:
            playing += 1
            answers.update({user: 0})
            if playing == 13 or playing == 14:
                bot.reply_to(poll_msg, "Уже записалось {} игроков! Места скоро закончатся!".format(playing))
            elif playing == 15:
                bot.reply_to(poll_msg, "Уже записалось 15 игроков! Мест больше нет.")
            elif playing > 15:
                bot.reply_to(poll_msg, "Уже мест нет,прошу пожалуйста переголосовать,{}".format(poll_answer.user.full_name))
    else:
        if answers[user] == 0:
            playing -= 1
            if playing == 14:
                bot.reply_to(poll_msg, "Освободилось место! {} игроков.Видимо кто-то передумал".format(playing))
        answers.pop(user)

    print(playing)

    with open(str(poll_id), 'wb') as f:
        pickle.dump([answers, playing, poll_msg], f)


# Create a new poll
@bot.message_handler(commands=['create'])
def create_new_poll(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username
    # Check Admin
    if user in knowledge.Admins:

        poll_text = message.text.replace('/create ', '')
        poll_creation(message, poll_text)

    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


# Create a poll for a Monday game
def create_m_poll(message):
    tomorrow = datetime.now() + timedelta(1)

    poll_text = "Понедельник {}. Старт в 21:00 (14руб) малый зал СК 'Горизонт'".format(tomorrow.strftime('%d.%m'))

    # Poll creation
    poll_creation(message, poll_text)


# Create a poll for a Thursday game
def create_t_poll(message):
    tomorrow = datetime.now() + timedelta(1)

    # Poll creation
    poll_text = "Четверг {}. Старт в 20:30 (18руб) Большой зал СК 'Горизонт'".format(tomorrow.strftime('%d.%m'))
    poll_creation(message, poll_text)


# Stop polling last created poll
@bot.message_handler(commands=['stop'])
def stop_latest_poll(message):
    commandlogger(message)
    chat_id = message.chat.id
    # Check Admin
    user = message.from_user.username

    if user in knowledge.Admins:

        strikes = {}
        poll_id = 0
        poll_msg_id = 0
        answers = []
        playing = 0

        with open('users.json', 'r') as f:
            strikes = json.load(f, object_hook=keystoint)

        with open(str(message.chat.id), 'rb') as f:
            poll_id, poll_msg_id = pickle.load(f)

        with open(str(poll_id), 'rb') as f:
            answers, playing, temp = pickle.load(f)
        print(playing)
        for u in answers:
            if u not in strikes:
                strikes.update({u: [0,0]})

        bot.stop_poll(chat_id, poll_msg_id)
        get_poll_info(message, strikes, answers, playing)
        delete_poll_file(poll_id)
    # Deny message
    else:
        bot.send_message(chat_id, "У вас не хватает прав для создания опросов")


def announce_player_amount(chat_id):
    with open(str(chat_id), 'rb') as f:
        poll_id, poll_msg_id = pickle.load(f)

    with open(str(poll_id), 'rb') as f:
        answers, playing, temp = pickle.load(f)

    bot.send_message(chat_id, "Игроков на данный момент: {}".format(playing))


def create_poll_file(poll_id):
    f = open(str(poll_id), "x")


def delete_poll_file(poll_id):
    os.remove('./{}'.format(poll_id))


def poll_creation(message, create_text):
    msg = bot.send_poll(
        message.chat.id,
        create_text, [
            emoji.emojize('Играю :smiling_face:'),
            emoji.emojize("Не играю :disappointed_face:"),
            '15+(не успел записаться,на замену готов зайти)'
        ],
        is_anonymous=False)

    poll_id = msg.poll.id
    poll_msg_id = msg.id

    with open(str(message.chat.id), 'wb') as f:
        pickle.dump([poll_id, poll_msg_id], f)

    with open(str(poll_id), 'wb') as f:
        pickle.dump([{}, 0, msg], f)


@bot.message_handler(commands=['days'])
def getDays(message):
    chat_id = message.chat.id
    with open('days.json', 'r') as f:
        days = json.load(f)

    bot.send_message(chat_id,"Было {} игр по понедельникам, в среденем игроков: {}\n"
                             "Было {} игр по четвергам, в среднем игроков: {}".format(days["monday"][0], days["monday"][1],
                                                                                      days["thursday"][0], days["thursday"][1]))


@bot.message_handler(commands=['snipe'])
def snipe(message):
    commandlogger(message)
    chat_id = message.chat.id
    user = message.from_user.username

    # Check Admin
    if user in knowledge.Admins:
        poll_text = message.text.replace('/snipe ', '')
        with open('users.json', 'r') as f:
            users = json.load(f, object_hook=keystoint)
        try:
            u = int(poll_text)
            users.pop(u)
        except:
            bot.reply_to(message, "Не могу найти такого игрока")
        with open('users.json', 'w') as f:
            json.dump(users, f)
    # Deny message
    else:
        bot.send_message(chat_id, "Не хватает прав")


def keystoint(x):
    return {int(k): v for k, v in x.items()}


def commandlogger(message):
    with open('CommandsLog.txt', 'a') as f:
        f.write("{} used command: {}\n".format(message.from_user.full_name, message.text))


bot.infinity_polling()
