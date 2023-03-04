from telebot import types

# Клавиатура для основного меню
main_menu_keyboard = types.InlineKeyboardMarkup()
load_test_jira_button = types.InlineKeyboardButton(
    text="Загружаем компетенции в тестовую JIRA", callback_data="test_load")
load_main_jira_button = types.InlineKeyboardButton(
    text="Загрузка компетенций в основную JIRA", callback_data="main_load")
user_control_button = types.InlineKeyboardButton(
    text="Управление доступами", callback_data="access_control")
get_month_data = types.InlineKeyboardButton(
    text="Выгрузка компетенций за текущий месяц", callback_data="get_month_data")
get_custom_data = types.InlineKeyboardButton(
    text="Выгрузка компетенций за указанный период", callback_data="get_period_data")
clear_templates_test = types.InlineKeyboardButton(
    text="Очищаем шаблоны в тестовой JIRA", callback_data="delete_templates_test")


main_menu_keyboard.row_width = 1
main_menu_keyboard.add(load_test_jira_button, load_main_jira_button,
                       get_month_data, get_custom_data, get_month_data,
                       clear_templates_test, user_control_button)
