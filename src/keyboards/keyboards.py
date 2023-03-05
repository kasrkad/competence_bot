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
show_change_log = types.InlineKeyboardButton(
    text="Показать последние изменения", callback_data="show_change_log")

main_menu_keyboard.row_width = 1
main_menu_keyboard.add(load_test_jira_button, load_main_jira_button, show_change_log,
                       get_custom_data, get_month_data,
                       clear_templates_test, user_control_button)

# Клавиатура для управления пользователями
user_access_menu = types.InlineKeyboardMarkup()
get_all_user = types.InlineKeyboardButton(
    text="Показать всех пользователей", callback_data="show_all_users")
delete_user = types.InlineKeyboardButton(
    text="Удалить пользователя", callback_data="delete_user")
add_user = types.InlineKeyboardButton(
    text="Добавить нового пользователя", callback_data="add_user")
return_main_menu = types.InlineKeyboardButton(
    text="Главное меню", callback_data="main_menu")


user_access_menu.row_width = 1
user_access_menu.add(add_user, delete_user, get_all_user, return_main_menu)
