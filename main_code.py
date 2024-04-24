import logging
import sqlite3
import random
import requests
import csv
from PIL import (Image, ImageDraw)
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from data_for_db_with_correct_answers import db_session
from data_for_db_with_correct_answers.name_of_tests import Nameoftest
from data_for_db_with_correct_answers.question_answer_for_test import Questionandanswer
from telegram.ext import (
    Updater,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    CallbackContext,
    MessageHandler,
    Filters,
)

# Ведение журнала логов
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Переменная начала работы
started = False
# Задаем спсиски с именами БД
databases = ["tests_with_correct_answers.db", "coords_tests.db"]
# Подключаемся к базам данных
con_c_t = sqlite3.connect(databases[1])
cur_ct = con_c_t.cursor()
# достаем из БД все имена тестов с выбором ответов
coord_tests = cur_ct.execute('''SELECT test_name FROM tests''').fetchall()
# Этапы/состояния разговора
start_function,\
tests_with_correct_answers,\
astral_tests,\
tests_with_selection_of_answers,\
start_coord_question,\
user_answer_for_tests_with_correct_answers,\
user_choose_zz,\
next_question_for_tests_with_correct_answers,\
end_of_test_with_correct_answers,\
next_test, \
place_prediction, \
end_of_test, \
results_of_coord_test, \
continue_coord_test \
    = range(14)
# Данные обратного вызова
first_test, second_test, third_test, back = range(1, 5)
# Задаем переменные с обозначением следующего вопроса и номера астрального теста
next_question = 0
number_of_astral_test = 0
# Создаем список с правилами ввода для каждого теста из тестов с правильными ответами
rules_for_tests_with_correct_answers = ["Правила теста:\n\nЕсли требуется найти пропущенную фигуру или выбрать нужную,"
                                        " введите номер выбранной вами фигуры\n\nЕсли требуется ввести пропущенное"
                                        " число, буквы или слово или продолжить ряд, введите его любым шрифтом\n\n"
                                        "Если требуется расшифровать анаграмму и исключить лишнюю, введите выбранное"
                                        " расшифрованное слово\n\nЕсли требуется найти несколько пропущенных букв"
                                        " или чисел, то введите их в любом порядке через пробел",
                                        "Правила теста:\n\nОтвет склоняйте по вопросу, используя если нужно предлог."
                                        " Например: вопрос - У каких ...?, ответ - у синих\n\nЕсли вопрос СКОЛЬКО,"
                                        " то дайте ответ числом, если нужно пояснить величину ответа, допишите её"
                                        " через пробел в нужном склонении\n\nЕсли требуется ввести два ответа,"
                                        " то введите их через пробел",
                                        "Правила теста:\n\nВсе ответы вводите в именительном падеже.\n\nЕсли"
                                        " спрашивается верно высказывание или нет, отвечайте да или нет\n\nЕсли "
                                        "задается вопрос по типу СКОЛЬКО, то введите число"]
# Создаем словарь с ключами - зз, значениями - предсказание по зз
predictions_of_zodiac_sign = {}
with open("predictions_of_zodiac_sign.txt", "r", encoding="utf-8") as f:
    f = f.read().split("=")
    for k in f:
        j = k.split(":")
        predictions_of_zodiac_sign[j[0]] = j[1].strip("\n")
# Задаем начальную встроенную клавиатуру
start_keyboard = [
    [
        InlineKeyboardButton("Тесты с правильными ответами", callback_data=str(tests_with_correct_answers))
    ],
    [
        InlineKeyboardButton("Астральные тесты", callback_data=str(astral_tests))
    ],
    [
        InlineKeyboardButton("Тесты с выбором ответов", callback_data=str(tests_with_selection_of_answers))
    ]
]
# Создаем список функций для тестов с координатами, чтобы понимать, какой тест выбрал пользователь
dict_of_func_to_coord_tests = {}
for j in coord_tests:
    def test_func(update: Update, context: CallbackContext, test_name=j[0]):
        context.user_data['question_num'] = 1
        context.user_data['coord_test_name'] = test_name
        context.user_data['coords'] = [0, 0]
        query = update.callback_query
        query.answer()
        keyboard = [
            [InlineKeyboardButton('Начать!', callback_data='test_started')],
            [InlineKeyboardButton("Назад", callback_data=str(back))]
                    ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        query.edit_message_text(
            text="Вы уверены, что хотите начать тест?", reply_markup=reply_markup
        )
        return start_coord_question
    dict_of_func_to_coord_tests[j[0]] = test_func


def start(update: Update, context: CallbackContext):
    """Вызывается по команде `/start`."""
    if not context.user_data.get(started):
        update.message.reply_text(text="Привет! Я бот Бесснер! Ты можешь пройти разные тесты.")
        # Получаем пользователя, который запустил команду `/start`
        user = update.message.from_user
        logger.info("Пользователь %s начал разговор", user.first_name)
    else:
        update.message.reply_text(text="Вы вернулись в главное меню.")
    context.user_data["test_started"] = False
    # Создаем `InlineKeyboard`, где пользователь выберет тип тестов
    keybord = start_keyboard
    reply_markup = InlineKeyboardMarkup(keybord)
    # Отправляем сообщение с текстом и добавленной клавиатурой `reply_markup`
    update.message.reply_text(
        text="Выбери тип теста:", reply_markup=reply_markup
    )
    context.user_data[started] = True
    # Сообщаем `ConversationHandler`, что сейчас состояние `start_function`
    return start_function


def start_over(update: Update, context: CallbackContext):
    """Вызывается после того, как пользователь нажал 'Назад' или прошел тест."""
    context.user_data["test_started"] = False
    # Получаем `CallbackQuery` из обновления `update`
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    # Создаем `InlineKeyboard`, где пользователь выберет тип тестов
    keybord = start_keyboard
    reply_markup = InlineKeyboardMarkup(keybord)
    # Отправляем сообщение с текстом и добавленной клавиатурой `reply_markup`
    query.edit_message_text(
        text="Выбери тип теста:", reply_markup=reply_markup
    )
    # Сообщаем `ConversationHandler`, что сейчас состояние `start_function`
    return start_function


def help(update: Update, context: CallbackContext):
    update.message.reply_text(text="Это бот \"Бесснер\". Здесь вы можете пройти тесты по разным категориям. Чтобы "
                                   "начать разговор нажмите /start. Чтобы прервать разговор и вернуться в главное меню"
                                   " нажмите /stop. Для помощи нажмите /help. Управление ботом происходит посредством "
                                   "клавиатуры под сообщениями. Если возникла ошибка, для перезапуска нажмите /stop.")


def choose_test_with_correct_answers(update: Update, context: CallbackContext):
    """Вызывается после выбора пользователем в /start или start_over варианта 'Тесты с правильными ответами'"""
    """Служит для выбора теста с правильными ответами"""
    # Получаем `CallbackQuery` из обновления `update`
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    # Создаем пустую клавиатуру
    keyboard = []
    # Создаем сессию с БД и достаем из неё все имена тестов с правильными ответами
    db_sess = db_session.create_session()
    name_of_tests_with_correct_answers = db_sess.query(Nameoftest).all()
    # Создаем по одной кнопки для каждого теста и добавляем кнопку "Назад"
    for i in range(len(name_of_tests_with_correct_answers)):
        keyboard.append([InlineKeyboardButton(name_of_tests_with_correct_answers[i].name, callback_data=i + 1)])
    keyboard.append([InlineKeyboardButton("Назад", callback_data=str(back))])
    # Создаем InlineKeyboardMarkup, где пользователь выберет тест
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Отредактируем сообщение, вызвавшее обратный вызов.
    # Это создает ощущение интерактивного меню.
    query.edit_message_text(
        text="Выберите тест", reply_markup=reply_markup
    )
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `tests_with_correct_answers`
    return tests_with_correct_answers


def main_handler_for_tests_with_correct_answers(update: Update, context: CallbackContext):
    """Вызывается после выбора какого-либо теста с правильными ответами, служит для отправки вопросов и правил юзеру"""
    # Если сейчас только начало теста, задаем номер вопроса, имя теста(id в БД), количество правильно отвеченных
    # вопросов и количество вопросов в выбранном тесте, а затем устанавливаем значение для переменной
    # "test_started" на True(то есть тест начат)
    if not context.user_data["test_started"]:
        context.user_data["number_of_question"] = 1
        context.user_data["name_of_test"] = update.callback_query.data
        context.user_data["test_started"] = True
        context.user_data["count_of_correct_answers"] = 0
        if update.callback_query.data == "1":
            context.user_data["count_of_questions"] = 40
        elif update.callback_query.data == "2":
            context.user_data["count_of_questions"] = 14
        else:
            context.user_data["count_of_questions"] = 16
    # Создаем сессию с БД и достаем из неё все вопрос с определнным номером для выбранного теста
    db_sess = db_session.create_session()
    context.user_data["current_question"] = db_sess.query(Questionandanswer).filter(
        Questionandanswer.name_of_test == context.user_data["name_of_test"],
        Questionandanswer.number_of_question == context.user_data["number_of_question"])[0]
    # Каждый раз присылаем вместе с вопросом правила теста, чтобы пользователю было удобнее пользоваться ботом
    context.bot.send_message(chat_id=update.callback_query.message.chat_id,
                             text=rules_for_tests_with_correct_answers[
                                 context.user_data["current_question"].name_of_test - 1])
    # Удаляем встроенную клавиутуру из последнего сообщения,
    # чтобы пользователь не мог ей воспользоваться посередине теста
    context.bot.edit_message_reply_markup(update.callback_query.message.chat_id,
                                          message_id=update.callback_query.message.message_id,
                                          reply_markup=InlineKeyboardMarkup([]))
    # Проверяем нужно ли выводить картинку
    if "/question_" in context.user_data["current_question"].question:
        # Если нужно, то присылаем картинку
        context.bot.send_photo(chat_id=update.callback_query.message.chat_id,
                               photo=open(context.user_data["current_question"].question, "rb"),
                               caption="Дайте ответ на вопрос.")
    else:
        # Иначе присылаем обычный текстовый вопрос
        context.bot.send_message(chat_id=update.callback_query.message.chat_id,
                                 text=context.user_data["current_question"].question)
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `user_answer_for_tests_with_correct_answers`
    return user_answer_for_tests_with_correct_answers


def func_user_answer_for_tests_with_correct_answers(update: Update, context: CallbackContext):
    """Вызывается после того, как пользователь ввел ответ на вопрос"""
    """Служит для проверки ответа юзера и для его уведомления о результате"""
    # Приводим ответ пользователя к общему виду (избавляемся от лишних пробелов и больших букв)
    user_answer = sorted(str(update.message.text).strip().lower().split())
    # Создаем 'InlineKeyboardMarkup' с одной кнопкой 'Далее' для следующего вопроса
    keyboard = [[InlineKeyboardButton("Далее", callback_data=str(next_question))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Из объекта БД достаем ответ на вопрос и объяснение ответа
    explanation = context.user_data["current_question"].explanation
    answer = str(context.user_data["current_question"].answer)
    # Увеличиваем переменную с номером вопроса на 1(таким образом в следующий раз программа задаст следующий вопрос)
    context.user_data["number_of_question"] += 1
    # Узнаем, правильный ли ответ дал пользователь
    if user_answer == sorted(answer.lower().split()):
        # Если пользователь дал верный ответ, увеличиваеми количество правильно данных ответов на 1
        # Выводим сообщение о верности ответа и с ним показываем объяснение ответа
        context.user_data["count_of_correct_answers"] += 1
        update.message.reply_text(
            text="Верно! " + explanation, reply_markup=reply_markup
        )
    else:
        # Если пользователь дал неправильный ответ, выводим Сообщение о неправильности ответа и
        # показываем правильный ответ с объяснением(если есть)
        update.message.reply_text(
            text="Неправильно! Верный ответ - " + answer.lower().capitalize() + " " + explanation,
            reply_markup=reply_markup
        )
    if context.user_data["number_of_question"] != context.user_data["count_of_questions"] + 1:
        # Сообщаем `ConversationHandler`,
        # что сейчас находимся в состоянии `next_question_for_tests_with_correct_answers`,
        # если вопросы в тесте остались
        return next_question_for_tests_with_correct_answers
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `end_of_test_with_correct_answers`,
    # если вопросы у теста закончились
    return end_of_test_with_correct_answers


def end_of_test_with_correct_answers(update: Update, context: CallbackContext):
    """Вызывается после завершения теста с правильными вопросами"""
    """Служит для уведомления пользователя о результатах теста"""
    # Получаем `CallbackQuery` из обновления `update`
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    # Удаляем встроенную клавиутуру из последнего сообщения,
    # чтобы пользователь не мог ей воспользоваться после завершения теста
    context.bot.edit_message_reply_markup(chat_id=update.callback_query.message.chat_id,
                                          message_id=update.callback_query.message.message_id,
                                          reply_markup=InlineKeyboardMarkup([]))
    # Для каждого из тестов делаем свой собственный вывод результатов
    if int(context.user_data["current_question"].name_of_test) == 1:
        text = "Вы прошли тест на IQ Айзенка и ответили правильно на " +\
              str(context.user_data["count_of_correct_answers"]) + " вопросов из " +\
              str(context.user_data["count_of_questions"]) + ". Таким образом ваш IQ составляет " +\
              str(context.user_data["count_of_correct_answers"] * 4) + " из 160  возможных."
    elif int(context.user_data["current_question"].name_of_test) == 2:
        text = "Вы прошли тест c 'детскими вопросами' и ответили правильно на " + \
               str(context.user_data["count_of_correct_answers"]) + " вопросов из " + \
               str(context.user_data["count_of_questions"])
    else:
        text = "Вы прошли географический тест и ответили правильно на " + \
               str(context.user_data["count_of_correct_answers"]) + " вопросов из " + \
               str(context.user_data["count_of_questions"])
    # Создаем 'InlineKeyboardMarkup' с одной кнопкой 'Вернуться в глвное меню',
    # чтобы пользователь после получения результатов теста мог пройти другой тест
    reply_markup = InlineKeyboardMarkup([[InlineKeyboardButton(text="Вернуться в глвное меню",
                                                               callback_data=str(back))]])
    # Присылаем юзеру результаты теста
    query.bot.send_message(chat_id=update.callback_query.message.chat_id, text=text, reply_markup=reply_markup)
    # Меняем переменную 'test_started', так как тест закончился
    context.user_data["test_started"] = False
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `next_test`
    return next_test


def choose_astral_test(update: Update, context: CallbackContext):
    """Вызывается после выбора пользователем в /start варианта 'Астральные тесты'"""
    """Служит для выбора астрального теста"""
    # Получаем `CallbackQuery` из обновления `update`
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    # Создаем 'InlineKeyboardMarkup' с названиями астральных тестов и кнопкой 'Назад'
    keyboard = [
            [InlineKeyboardButton('Тест "Какой у тебя сегодня день?"', callback_data=str(first_test))],
            [InlineKeyboardButton('Тест предсказание по твоему месту', callback_data=str(second_test))],
            [InlineKeyboardButton('Тест "Твоя личность"', callback_data=str(third_test))],
            [InlineKeyboardButton("Назад", callback_data=str(back))]
        ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Отредактируем сообщение, вызвавшее обратный вызов
    # Это создает ощущение интерактивного меню
    query.edit_message_text(
        text="Выберите тест", reply_markup=reply_markup
    )
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `astral_tests`
    return astral_tests


def main_handler_for_tests_with_zodiac_sign(update: Update, context: CallbackContext):
    """Вызывается после выбора теста с зз, служит для показа выбора зз пользователя"""
    # Получаем `CallbackQuery` из обновления `update`
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    # По нажатой кнопки определяем, какой тест выбрал пользователь и записываем значение в переменную
    context.user_data[number_of_astral_test] = update.callback_query.data
    # Создаем клавиатуру с 12 знаками зодиака
    keyboard = []
    for i in range(12):
        if i % 2 == 0:
            keyboard.append([])
        keyboard[i // 2].append(InlineKeyboardButton(text=list(predictions_of_zodiac_sign.keys())[i],
                                                     callback_data=str(i)))
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Предлагаем пользователю выбрать свой зз
    query.edit_message_text(text="Хорошо! А теперь выберите свой знак зодиака!", reply_markup=reply_markup)
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `user_choose_zz`
    return user_choose_zz


def answer_for_tests_with_zodiac_sign(update: Update, context: CallbackContext):
    """Вызывается после выбора зз пользователем, служит для показа предсказания по зз"""
    # Получаем `CallbackQuery` из обновления `update`
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    # по нажатой кнопки запоминаем выбранный зз
    name_of_zz = list(predictions_of_zodiac_sign.keys())[int(query.data)]
    # Определяем номер теста и запоминаем ответ для пользователя
    if context.user_data[number_of_astral_test] == "3":
        text = predictions_of_zodiac_sign[name_of_zz]
    else:
        with open("ans_for_your_test.txt", "r", encoding="utf-8") as ans:
            ans = ans.read().split("\n")
            text = ans[random.randrange(12)]
    # Создаем 'InlineKeyboardMarkup' с кнопкой 'Главное меню'
    keyboard = [[InlineKeyboardButton(text="Главное меню", callback_data=str(back))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Отредактируем сообщение, вызвавшее обратный вызов, передав ответ для пользователя
    # Это создает ощущение интерактивного меню
    query.edit_message_text(text=text,
                            reply_markup=reply_markup)
    # Сообщаем `ConversationHandler`, что сейчас находимся в состоянии `next_test`
    return next_test


# основной оброботчик теста с предсказанием по месту
def main_handler_for_place_prediction(update: Update, context: CallbackContext):
    query = update.callback_query
    # Отвечаем на запрос обратного вызова
    query.answer()
    query.edit_message_text(text='Введите ваше местоположение')
    return place_prediction


# Функция, которая возвращает координаты обьекта obj на я картах
def coord(obj):
    geocoder_request = f"http://geocode-maps.yandex.ru/1.x/?apikey=40d1649f" \
                       f"-0493-4b70-98ba-98533de7710b&geocode={obj}&format=json"
    # получаем json с информацией об этом месте
    response = requests.get(geocoder_request)
    try:
        json_response = response.json()
        toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
        return toponym["Point"]["pos"]
    except IndexError:
        return 1
        # Если место не нашлось, возвращаем 1, которая потом будет обрабатываться


# Фнкция, которая выводит предсказание, основываясь на том, что пользователь ввел
def answer_for_place_prediction(update: Update, context: CallbackContext):
    keyboard = [[InlineKeyboardButton("Назад", callback_data=str(back))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Если предыдущая функция вернула 1, говорим, что адрес неверен
    if coord(update.message.text) == 1:
        print("Ошибка выполнения запроса:")
        context.bot.send_message(chat_id=update.message.chat_id, text="Неверный адрес",
                                 reply_markup=reply_markup)
    else:
        # Иначе получаем фотографию используя Static-API
        x, y = coord(update.message.text).split()
        map_request = f"http://static-maps.yandex.ru/1.x/?ll={x},{y}&spn=0.002,0.002&l=sat"
        response = requests.get(map_request)
        if response:
            # Получаем все строки из csv файла, чтобы выбрать случайную
            with open('place_predictions.csv', encoding="utf8") as csvfile:
                reader = csv.reader(csvfile, delimiter=';', quotechar='"')
                lines = []
                for i in enumerate(reader):
                    lines.append(i[1])
            # Выводим результат и обрабатываем непредвиденные ошибки
            context.bot.send_photo(chat_id=update.message.chat_id,
                                   photo=response.content,
                                   caption=random.choice(lines)[0].replace('~', ''))
            context.bot.send_message(chat_id=update.message.chat_id, text="Выход в главное меню",
                                     reply_markup=reply_markup)
        else:
            context.bot.send_message(chat_id=update.message.chat_id, text="Oшибка запроса",
                                     reply_markup=reply_markup)
    return end_of_test


# Функция меню всех тестов с координатами. Тут все очевидно из кода
def choose_test_with_selections_of_answers(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    keyboard = []
    # В coord_tests лежат имена всех тестов
    for i in coord_tests:
        keyboard.append([InlineKeyboardButton(i[0], callback_data=i[0])])
    keyboard.append([InlineKeyboardButton("Назад", callback_data=str(back))])
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text="Выберете тест:", reply_markup=reply_markup
    )
    return tests_with_selection_of_answers


# Функция вывода вопроса теста с координатами
def question_of_coord_test(update: Update, context: CallbackContext):
    con_coords_tests = sqlite3.connect("coords_tests.db")
    cur_coords_tests = con_coords_tests.cursor()
    query = update.callback_query
    query.answer()

    # изменяем координаты пользователя в соответствии с предыдущим ответом
    if context.user_data['question_num'] != 1:
        next_coord_chanches = list(
            map(lambda x: tuple(map(int, x.split(', '))), context.user_data['next_coord_chanches'][0].split('|')))
        context.user_data['coords'][0] += next_coord_chanches[int(query.data) - 1][0]
        context.user_data['coords'][1] += next_coord_chanches[int(query.data) - 1][1]

    # Записываем в юзер дата изменение координат после этого вопроса
    context.user_data['next_coord_chanches'] = cur_coords_tests.execute('''
    SELECT (coord_chanches) FROM questions WHERE test_number = ? 
    AND test_id in (SELECT id FROM tests WHERE test_name = ?)
    ''', (context.user_data['question_num'], context.user_data['coord_test_name'])).fetchall()[0]

    # Достаем вопрос и варианты ответа
    questions = cur_coords_tests.execute('''SELECT ans1, ans2, ans3, ans4, question FROM questions WHERE test_number = ? 
    AND test_id in (SELECT id FROM tests WHERE test_name = ?)''',
                                         (context.user_data['question_num'],
                                          context.user_data['coord_test_name'])).fetchall()
    keyboard = [[InlineKeyboardButton(questions[0][0], callback_data='1')],
                [InlineKeyboardButton(questions[0][1], callback_data='2')],
                [InlineKeyboardButton(questions[0][2], callback_data='3')],
                [InlineKeyboardButton(questions[0][3], callback_data='4')]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    query.edit_message_text(
        text=questions[0][4], reply_markup=reply_markup
    )
    context.user_data['question_num'] += 1
    # Проверем, не последний ли это вопрос
    if context.user_data['question_num'] - 1 == len(cur_coords_tests.execute('''SELECT question FROM questions WHERE 
    test_id in (SELECT id FROM tests WHERE test_name = ?)''', (context.user_data['coord_test_name'],)).fetchall()):
        return results_of_coord_test
    else:
        return continue_coord_test


# Вывод результата теста с координатами
def result_of_coord_test(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    # изменяем координаты пользователя в соответствии с предыдущим ответом
    next_coord_chanches = list(
        map(lambda z: tuple(map(int, z.split(', '))), context.user_data['next_coord_chanches'][0].split('|')))
    context.user_data['coords'][0] += next_coord_chanches[int(query.data) - 1][0]
    context.user_data['coords'][1] += next_coord_chanches[int(query.data) - 1][1]
    # Создаем клавиатуру выхода в главное меню
    keyboard = [[InlineKeyboardButton("Назад", callback_data=str(back))]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    # Достаем картинку для этого теста и рисуем на ней точку
    im = Image.open("coordinates images/" +
                    context.user_data['coord_test_name'] + '.jpg')
    draw = ImageDraw.Draw(im)
    x, y = context.user_data['coords']
    draw.ellipse((
        (245 + x, 245 - y),
        (255 + x, 255 - y)
    ),
        '#99ff99'
    )
    im.save('cash.jpg')
    # Выводим результаты
    context.bot.send_photo(chat_id=update.callback_query.message.chat_id,
                           photo=open("cash.jpg", "rb"),
                           caption="Поздравляем с окончанием теста. Ваши координаты - это зеленая точка")
    query.edit_message_text(
        text="-"
    )
    context.bot.send_message(chat_id=update.callback_query.message.chat_id, text="Выход в главное меню",
                             reply_markup=reply_markup)
    return end_of_test


def main():
    # Инициализируем глобальное подключение к БД для тестов с правильными ответами
    db_session.global_init(databases[0])
    # Подключаемся к боту
    updater = Updater("5381678110:AAEfhtBCZtWmjYUYZL_3g7HbjiDBFyKZF2w")
    dispatcher = updater.dispatcher
    # словарь состояний разговора, возвращаемых callback функциями
    states = {
        start_function: [
            CallbackQueryHandler(choose_test_with_correct_answers, pattern='^' +
                                                                           str(tests_with_correct_answers) + '$'),
            CallbackQueryHandler(choose_astral_test, pattern='^' + str(astral_tests) + '$'),
            CallbackQueryHandler(choose_test_with_selections_of_answers,
                                 pattern='^' + str(tests_with_selection_of_answers) + '$')
        ],
        tests_with_correct_answers: [
            CallbackQueryHandler(main_handler_for_tests_with_correct_answers, pattern="^" + str(first_test) + "$"),
            CallbackQueryHandler(main_handler_for_tests_with_correct_answers, pattern="^" + str(second_test) + "$"),
            CallbackQueryHandler(main_handler_for_tests_with_correct_answers, pattern="^" + str(third_test) + "$"),
            CallbackQueryHandler(start_over, pattern='^' + str(back) + '$')
        ],
        astral_tests: [
            CallbackQueryHandler(main_handler_for_tests_with_zodiac_sign,
                                 pattern='^' + str(first_test) + '$'),
            CallbackQueryHandler(main_handler_for_place_prediction,
                                 pattern='^' + str(second_test) + '$'),
            CallbackQueryHandler(main_handler_for_tests_with_zodiac_sign,
                                 pattern='^' + str(third_test) + '$'),
            CallbackQueryHandler(start_over, pattern='^' + str(back) + '$')
        ],
        user_answer_for_tests_with_correct_answers: [
            MessageHandler(Filters.text & ~Filters.command, func_user_answer_for_tests_with_correct_answers,
                           pass_user_data=True)
        ],
        next_question_for_tests_with_correct_answers: [
            CallbackQueryHandler(main_handler_for_tests_with_correct_answers, pattern="^" + str(next_question) + "$"),
        ],
        end_of_test_with_correct_answers: [
            CallbackQueryHandler(end_of_test_with_correct_answers, pattern="^" + str(next_question) + "$")
        ],
        next_test: [
            CallbackQueryHandler(start_over, pattern="^" + str(back) + "$")
        ],
        user_choose_zz: [],
        continue_coord_test: [
            CallbackQueryHandler(question_of_coord_test, pattern='^' + '1' + '$'),
            CallbackQueryHandler(question_of_coord_test, pattern='^' + '2' + '$'),
            CallbackQueryHandler(question_of_coord_test, pattern='^' + '3' + '$'),
            CallbackQueryHandler(question_of_coord_test, pattern='^' + '4' + '$')
        ],
        results_of_coord_test: [
            CallbackQueryHandler(result_of_coord_test, pattern='^' + '1' + '$'),
            CallbackQueryHandler(result_of_coord_test, pattern='^' + '2' + '$'),
            CallbackQueryHandler(result_of_coord_test, pattern='^' + '3' + '$'),
            CallbackQueryHandler(result_of_coord_test, pattern='^' + '4' + '$')
        ],
        end_of_test: [
            CallbackQueryHandler(start_over, pattern='^' + str(back) + '$')
        ],
        start_coord_question: [
            CallbackQueryHandler(question_of_coord_test, pattern='^' + 'test_started' + '$'),
            CallbackQueryHandler(start_over, pattern='^' + str(back) + '$')
        ],
        place_prediction: [
            MessageHandler(Filters.text & ~Filters.command, answer_for_place_prediction, pass_user_data=True)
        ]
    }
    # Добавляем по обработчику для каждого зз, который может быть выбран юзером
    for i in range(12):
        states[user_choose_zz].append(CallbackQueryHandler(answer_for_tests_with_zodiac_sign,
                                                           pattern="^" + str(i) + "$"))
    # Добавляем в диспечер обработчики для списка функций в начале
    lt = []
    for i in coord_tests:
        lt.append(CallbackQueryHandler(dict_of_func_to_coord_tests[i[0]], pattern='^' + i[0] + '$'))
    lt.append(CallbackQueryHandler(start_over, pattern='^' + str(back) + '$'))
    states[tests_with_selection_of_answers] = lt

    conv_handler = ConversationHandler(entry_points=[CommandHandler('start', start)],
                                       states=states, fallbacks=[CommandHandler('stop', start)])
    dispatcher.add_handler(CommandHandler('help', help))
    # Добавляем `ConversationHandler` в диспетчер, который будет использоваться для обработки обновлений
    dispatcher.add_handler(conv_handler)
    # Запускаем бота
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()