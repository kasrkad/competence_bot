import telebot
from os.path import splitext
from os import environ
from logger_config.logger import create_logger
from sqlite_module.sql_lib import create_tables, load_admin_from_json, check_admin_permissions
from keyboards.keyboards import main_menu_keyboard
from template_worker.worker import checklist_delete, checklist_updater,\
    jira_get_all_projects, jira_get_all_templates, checklist_loader
from json_operator.operator import load_1c_data_from_file, get_competence_codes,\
    jira_id_for_1c, data_from_1c_compare, data_from_jira_compare


JIRA_TEST_ADDR = environ["JIRA_TEST_ADDR"]
JIRA_TEST_TOKEN = environ["JIRA_TEST_TOKEN"]

JIRA_MAIN_ADDR = environ["JIRA_MAIN_ADDR"]
JIRA_MAIN_TOKEN = environ["JIRA_MAIN_TOKEN"]


competence_bot_logger = create_logger(__name__)


class Competence_bot:
    def __init__(self, bot_token):
        self.bot = telebot.TeleBot(bot_token, parse_mode="MARKDOWN")
        self.main_menu_call_data = [
            keyboard[0].callback_data for keyboard in main_menu_keyboard.keyboard]

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

    def bot_commands(self):
        @self.permissions_decorator
        @self.bot.message_handler(commands=['start'])
        def start_command(message):
            self.bot.reply_to(
                message, "Привет я работаю!Я буду загружать и выгружать компетенции", reply_markup=main_menu_keyboard)

        @self.bot.message_handler(content_types=["document"])
        @self.permissions_decorator
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
                if call.data == "main_load":
                    self.bot.send_message(
                        call.from_user.id, "Производим загрузку в основную Jira")
                if call.data == "access_control":
                    self.bot.send_message(
                        call.from_user.id, "Открываем управление доступом к боту")
                if call.data == "get_month_data":
                    self.bot.send_message(
                        call.from_user.id, "Запрашиваем выгрузку компетенций с начала месяца")
                if call.data == "get_period_data":
                    self.bot.send_message(
                        call.from_user.id, "Запрашиваем выгрузку компетенций с по указанному периоду")
                if call.data == "delete_templates_test":
                    self.bot.send_message(
                        call.from_user.id, "Очищаем шаблоны в тестовой Jira")
                    self.delete_templates(tg_id=call.from_user.id,
                                          jira_host=JIRA_TEST_ADDR,
                                          jira_token=JIRA_TEST_TOKEN)
            except Exception:
                competence_bot_logger.error(
                    'Во время операции произошла ошибка', exc_info=True)
                self.bot.send_message(
                    call.from_user.id, 'Во время операции произошла ошибка', reply_markup=main_menu_keyboard)

    def run(self):
        competence_bot_logger.info(
            "Проверяем базу, проверяем пользователей, создаем если отсуствует")
        create_tables()
        load_admin_from_json()
        competence_bot_logger.info("Запускаем бота")
        self.bot_commands()
        self.bot.polling(none_stop=True, interval=0, timeout=200)
