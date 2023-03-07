import telebot
from os.path import splitext
import json
from os import environ,remove
from json2xml import json2xml
from datetime import datetime
from json2xml.utils import readfromstring
from logger_config.logger import create_logger
from sqlite_module.sql_lib import create_tables, load_admin_from_json,\
    check_admin_permissions, chengelog_insert, show_all_admin_db, insert_admin,\
    delete_admin_user_db, show_change_log
from keyboards.keyboards import main_menu_keyboard, user_access_menu
from template_worker.worker import checklist_delete, checklist_updater,\
    jira_get_all_projects, jira_get_all_templates, checklist_loader
from json_operator.operator import load_1c_data_from_file, get_competence_codes,\
    jira_id_for_1c, data_from_1c_compare, data_from_jira_compare
from competence_scanner.scanner import users_with_competences,get_issues_data



JIRA_TEST_ADDR = environ["JIRA_TEST_ADDR"]
JIRA_TEST_TOKEN = environ["JIRA_TEST_TOKEN"]

JIRA_MAIN_ADDR = environ["JIRA_MAIN_ADDR"]
JIRA_MAIN_TOKEN = environ["JIRA_MAIN_TOKEN"]


competence_bot_logger = create_logger(__name__)


class Competence_bot:

    def __init__(self, bot_token):
        self.bot = telebot.TeleBot(bot_token, parse_mode="MARKDOWN")
        self.main_menu_call_data = [
            keyboard.callback_data for sublist in main_menu_keyboard.keyboard for keyboard in sublist]
        self.user_menu_call_data = [
            keyboard.callback_data for sublist in user_access_menu.keyboard for keyboard in sublist]

    def permissions_decorator(self, func_for_decorate):
        """Проверка аккаунта вызывающего команду, на наличие доступа к ней.
        Args:
            func_for_decorate (_type_): Функция
        """
        def wrapper(message):
            if check_admin_permissions(message.from_user.id):
                func_for_decorate(message)
            else:
                self.bot.send_message(
                    message.from_user.id, 'В доступе отказано.')
                competence_bot_logger.error(
                    f'У пользователя с id {message.from_user.id} нет прав доступа.')
        return wrapper


    def get_competences_from_jira(self,message,jql_search:str = None) :
        try:
            competence_codes = get_competence_codes(load_1c_data_from_file("./1c/1c.json"))
            if jql_search:
                competence_bot_logger.info(f"Запрошена выгрузка компетенций за период")
                issues = get_issues_data(jira_token=JIRA_MAIN_TOKEN,jira_host=JIRA_MAIN_ADDR,jql=jql_search)
            else:
                competence_bot_logger.info(f"Запрошена выгрузка компетенций с начала месяца")
                issues = get_issues_data(jira_token=JIRA_MAIN_TOKEN,jira_host=JIRA_MAIN_ADDR)
            now = datetime.now()
            date_time = now.strftime("%Y.%m.%d")
            users_competences = users_with_competences(competence_codes=competence_codes,issues=issues)
            data = json.dumps({"date":date_time, "competence_block":users_competences},ensure_ascii=False)
            xml_data = readfromstring(data)
            with open("result_xml.xml", 'w',encoding="utf-8") as outfile:
                outfile.write(json2xml.Json2xml(xml_data, wrapper="all", pretty=True).to_xml())
            doc_for_send = open("result_xml.xml")
            self.bot.send_document(message.from_user.id,doc_for_send)
            doc_for_send.close()
            remove("result_xml.xml")
        except FileNotFoundError:
            self.bot.send_message(message.from_user.id,"Файл 1c.json не найден, загрузите файл и попробуйте еще раз")
            competence_bot_logger.error(f"Ошибка при работе с выгрузкой компетенций не найден файл 1с.json")
            return
        except Exception:
            self.bot.send_message(message.from_user.id,"Во время запроса компетенций произошла ошибка")
            competence_bot_logger.error(f"Ошибка при работе с выгрузкой компетенций строка поиска = {jql_search}", exc_info=True)
            return


    def get_jira_competence_period_dialogue(self, message):
        competence_bot_logger.info("Запрашиваем поиск компетенций по датам")
        user_response = self.bot.send_message(message.from_user.id, "Введите период для выгрузки через пробел,формат DD-MM-YYYY. Пример:\n01-01-2023 01-03-2023")
        self.bot.register_next_step_handler(user_response, self.get_jira_competence_period)


    def get_jira_competence_period(self, message):
        try:
            start_period, end_period = message.text.strip().split(" ")
            start_day,start_month,start_year = start_period.split("-")
            end_day,end_month,end_year = end_period.split("-")
        except Exception:
            self.bot.send_message(message.from_user.id,"Ошибка в указанных датах, проверьте их и повторите попытку.")
            return
        jql_search = f"'Competences Checklist' is not null AND statusCategory = Done AND resolutiondate >= '{start_year}/{start_month}/{start_day}' \
AND resolutiondate <='{end_year}/{end_month}/{end_day}' ORDER BY updated DESC"
        print(jql_search)
        self.get_competences_from_jira(message=message,jql_search=jql_search)


    def load_to_jira(self, tg_id, jira_host, jira_token):
        try:
            competence_bot_logger.info("getting all jira templates")
            self.bot.send_message(tg_id, f"Запрашиваем шаблоны из {jira_host}")
            all_templates = jira_get_all_templates(
                jira_host=jira_host, jira_token=jira_token)
            competence_bot_logger.info("getting all jira projects")
            self.bot.send_message(
                tg_id, f"Запрашиваем ID проектов из {jira_host}")
            projects = jira_get_all_projects(
                jira_host=jira_host, jira_token=jira_token)
            competence_bot_logger.info("load data from 1c.json")
            self.bot.send_message(
                tg_id, "Читаем файл с выгрузками компетенций из 1с")
            data_from_1c = load_1c_data_from_file("./1c/1c.json")
            competence_bot_logger.info("create jira projects with ids list")
            self.bot.send_message(tg_id, "Сравниваем проекты из jira и из 1с")
            project_jira_id = jira_id_for_1c(
                data_1c=data_from_1c, data_jira=projects)
            competence_bot_logger.info(
                "creating list with templates from 1c file")
            self.bot.send_message(tg_id, "Формируем список шаблонов")
            comparing_1c = data_from_1c_compare(
                data_1c=data_from_1c, jira_id=project_jira_id,
                fieldConfigId=17262,
                customFieldId=15553)
            competence_bot_logger.info(
                "creating list with templates from jira")
            comparing_jira = data_from_jira_compare(all_templates)
            need_create = 0
            need_update = 0
            errors = 0
            competence_bot_logger.info(
                "checking templates for create and update")
            self.bot.send_message(
                tg_id, f"Загружаем или обновляем шаблоны в {jira_host}, это займет пару минут")
            for project_template_name, project_data in comparing_1c.items():
                try:
                    if project_template_name not in comparing_jira:
                        checklist_loader(
                            checklist_data=project_data, jira_host=jira_host, jira_token=jira_token)
                        need_create += 1
                    else:
                        checklist_updater(jira_host=jira_host, jira_token=jira_token,
                                          checklist_id=comparing_jira[project_template_name],
                                          update_data=project_data["itemsJson"])
                        need_update += 1
                except Exception as exc:
                    errors += 1
                    competence_bot_logger.error(str(exc))
                    continue
            competence_bot_logger.info(
                f"Created {need_create}, updated {need_update}, errors {errors}")
            self.bot.send_message(
                tg_id, f"Создано {need_create}, обновлено {need_update}, Ошибок {errors}")
        except FileExistsError:
            self.bot.send_message(
                tg_id, "Файл с выгрузкой компетенций из 1с не обнаружен.")
            return
        except Exception:
            self.bot.send_message(
                tg_id, f"Произошла ошибка при загрузке шаблонов в {jira_host}")
            competence_bot_logger.critical(
                "В основном потоке произошла ошибка", exc_info=True)

    def delete_user_dialogue(self, message):
        competence_bot_logger.info(
            f"Запрошено удаление пользователя от {message.from_user.id}")
        try:
            user_reply = self.bot.send_message(
                message.from_user.id, "Введите Телеграмid пользователя из списка ниже для удаление")
            self.show_all_admins(message)
            self.bot.register_next_step_handler(user_reply, self.delete_user)
        except Exception:
            competence_bot_logger.error(
                "Произошла ошибка в диалоге при удалении пользователя", exc_info=True)
            self.bot.send_message(message.from_user.id,
                                  "Произошла ошибка при удалении пользователя")

    def delete_user(self, message):
        try:
            id_for_delete = message.text.strip()
            delete_admin_user_db(admin_id=message.from_user.id,
                                 tg_id_for_delete=id_for_delete)
            self.bot.send_message(
                message.from_user.id, f"Удаление пользователя {id_for_delete} успешно произведено.")
        except Exception:
            competence_bot_logger.error(
                f"Произошла ошибка при удалении пользователя {id_for_delete} БД")
            self.bot.send_message(
                message.from_user.id, "Произошла ошибка при удалении пользователя из БД")

    def delete_templates(self, tg_id, jira_host, jira_token):
        competence_bot_logger.info(f"Запрошено удаление от {tg_id}")
        try:
            competence_bot_logger.info("getting all jira templates")
            self.bot.send_message(
                tg_id, f"Запрашиваем список шаблонов из {jira_host}")
            all_templates = jira_get_all_templates(
                jira_host=jira_host, jira_token=jira_token)
            competence_bot_logger.info(f"starting delete from {jira_host}")
            self.bot.send_message(
                tg_id, f"Начинаем удаление шаблонов из {jira_host}, кол-во шаблонов - {len(all_templates['templates'])}, это займет пару минут")
            for template in all_templates["templates"]:
                checklist_delete(
                    template["id"], jira_token=jira_token, jira_host=jira_host)
            competence_bot_logger.info("Deleting templates competed")
            self.bot.send_message(
                tg_id, "Удаление шаблонов в тестовой jira завершено")

        except Exception:
            self.bot.send_message(
                tg_id, "Произошла ошибка при удалении шаблона")
            competence_bot_logger.critical(
                "В основном потоке произошла ошибка", exc_info=True)

    def show_all_admins(self, message):
        competence_bot_logger.info(
            f'Запрос на отображение админов от {message.from_user.id} ')
        try:
            admins_for_show = show_all_admin_db()
            self.bot.send_message(message.from_user.id, "\n".join(
                admin for admin in admins_for_show.values()))
        except Exception:
            competence_bot_logger.error(
                f'Произошла ошибка при запросе админов от {message.from_user.id}', exc_info=True)

    def add_new_user(self, message):
        try:
            competence_bot_logger.info(
                f"Запрошено добавление нового пользователя от  {message.from_user.id}")
            user_reply = self.bot.send_message(
                message.from_user.id, "Введите телеграм id и имя фамилию нового пользователя. Пример:\n 34213131:Иванов Сергей")
            self.bot.register_next_step_handler(
                user_reply, self.insert_new_user)
        except Exception:
            competence_bot_logger.error(
                f"Ошибка при установке пользователя {user_reply.text}", exc_info=True)

    def insert_new_user(self, message):
        try:
            competence_bot_logger.info(
                f"Добавляем пользователя {message.text} в базу.")
            tg_id, user_fio = message.text.strip().split(":")
            insert_admin(tg_id=tg_id, fio=user_fio)
            self.bot.send_message(
                message.from_user.id, "Пользователь успешно добавлен")
        except Exception:
            competence_bot_logger.error(
                f"Произошла ошибка при добавлении пользователя {message.text}")
            self.bot.send_message(
                message.from_user.id, "Произошла ошибка при добавлении пользователя")
            return

    def bot_commands(self):

        @self.bot.message_handler(commands=['start'])
        @self.permissions_decorator
        def start_command(message):
            self.bot.reply_to(
                message, "Привет я работаю!Я буду загружать и выгружать компетенции", reply_markup=main_menu_keyboard)

        @self.permissions_decorator
        def show_user_access_menu(call):
            self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                                       text="Меню управления доступом", reply_markup=user_access_menu)

        @self.permissions_decorator
        def show_main_menu(call):
            self.bot.edit_message_text(chat_id=call.message.chat.id, message_id=call.message.id,
                                       text="Главное меню", reply_markup=main_menu_keyboard)

        @ self.bot.message_handler(content_types=["document"])
        @ self.permissions_decorator
        def get_document(message):
            suffix = splitext(message.document.file_name)
            try:
                if suffix[1] == ".json":
                    self.bot.reply_to(
                        message, "Файл с компетенциями сохраняется.")
                    file_info = self.bot.get_file(message.document.file_id)
                    get_file = self.bot.download_file(file_info.file_path)
                    with open("1c/1c.json", "wb") as out_file:
                        out_file.write(get_file)
                    self.bot.reply_to(
                        message, "Файл с компетенциями успешно сохранен.")
                    chengelog_insert(tg_id=message.from_user.id,
                                     change_type="new 1c.json")
                else:
                    self.bot.reply_to(message, "Файл не json!Не надо так.")
            except Exception:
                competence_bot_logger.warn(
                    f"Ошибка при сохранении файла компетенций {message.document.file_name}")
                self.bot.reply_to(
                    message, "Ошибка при работе с файлом компетений, проверьте расширение файла")

        @self.bot.callback_query_handler(func=lambda call: call.data in self.main_menu_call_data)
        def callback_inline(call):
            try:
                if call.data == "test_load":
                    self.bot.send_message(
                        call.from_user.id, "Производим загрузку в Тестовую Jira")
                    self.load_to_jira(
                        tg_id=call.from_user.id,
                        jira_host=JIRA_TEST_ADDR,
                        jira_token=JIRA_TEST_TOKEN)
                    chengelog_insert(tg_id=call.from_user.id,
                                     change_type="Load to test jira")
                if call.data == "main_load":
                    self.bot.send_message(
                        call.from_user.id, "Производим загрузку в основную Jira")
                    chengelog_insert(tg_id=call.from_user.id,
                                     change_type="Load to main jira")
                if call.data == "access_control":
                    show_user_access_menu(call)
                if call.data == "get_month_data":
                    self.bot.send_message(
                        call.from_user.id, "Запрашиваем выгрузку компетенций с начала текущего месяца,может занять какое-то время")
                    self.get_competences_from_jira(message=call)
                if call.data == "get_period_data":
                    self.bot.send_message(
                        call.from_user.id, "Запрашиваем выгрузку компетенций с по периоду")
                    self.get_jira_competence_period_dialogue(message=call)
                if call.data == "delete_templates_test":
                    self.bot.send_message(
                        call.from_user.id, "Очищаем шаблоны в тестовой Jira")
                    self.delete_templates(tg_id=call.from_user.id,
                                          jira_host=JIRA_TEST_ADDR,
                                          jira_token=JIRA_TEST_TOKEN)
                if call.data == "show_change_log":
                    competence_bot_logger.info(
                        f"Пользователем {call.from_user.id} запрошена статистика изменений.")
                    msg = show_change_log()
                    self.bot.send_message(call.from_user.id, msg)
            except Exception:
                competence_bot_logger.error(
                    'Во время операции произошла ошибка', exc_info=True)
                self.bot.send_message(
                    call.from_user.id, 'Во время операции произошла ошибка', reply_markup=main_menu_keyboard)

        @self.bot.callback_query_handler(func=lambda call: call.data in self.user_menu_call_data)
        def callback_inline(call):
            if call.data == "show_all_users":
                self.show_all_admins(call)
            if call.data == "delete_user":
                self.delete_user_dialogue(call)
            if call.data == "add_user":
                self.add_new_user(call)
            if call.data == "main_menu":
                competence_bot_logger.info("Вызвано основное меню")
                show_main_menu(call)

    def run(self):
        competence_bot_logger.info(
            "Проверяем базу, проверяем пользователей, создаем если отсуствует")
        create_tables()
        load_admin_from_json()
        competence_bot_logger.info("Запускаем бота")
        self.bot_commands()
        self.bot.polling(none_stop=True, interval=0, timeout=200)
