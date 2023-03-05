import sqlite3
import time
import traceback
from logger_config.logger import create_logger


# logger create
sqlite_logger = create_logger(__name__)


class SQLite:
    def __init__(self, file='./bot_db/botbase.db'):
        """Открываем соединение до базы данных sqlite3
        Args:
            file (str, optional): пусть до базы, если ее там не будет, создастся новая. Defaults to './bot_db/botbase.db'.
        """
        self.file = file

    def __enter__(self):
        self.conn = sqlite3.connect(self.file)
        sqlite_logger.info("Соединение с бд установлено")
        return self.conn.cursor()

    def __exit__(self, type, value, traceback):
        self.conn.commit()
        self.conn.close()
        time.sleep(0.03)
        sqlite_logger.info("Соединение с бд закрыто")


def insert_admin(tg_id: str, fio: str) -> None:
    """Добавляет нового админа к в БД
    Args:
        tg_id (str): телеграм id пользователя
        fio (str): Фамилия Имя Отчество
    """
    try:
        sqlite_logger.info(f'Добавляем админа  {tg_id}-{fio}')
        with SQLite() as cursor:
            cursor.execute(
                f"""INSERT INTO ACCESS_TABLE(tg_id,fio) VALUES ('{tg_id}','{fio}')""")
        sqlite_logger.info(f'Администратор {tg_id}-{fio} добавлен.')
    except Exception:
        sqlite_logger.error(
            f'Произошла ошибка при добавлении администратора {tg_id}-{fio}', exc_info=True)


def load_admin_from_json(path_to_admin_file: str = "./settings/admins.json") -> None:
    """Загружаем администраторов из файла
    Args:
        path_to_admin_file (str): путь к файлу json с администраторами 
    """
    import json
    sqlite_logger.info(
        f'Загружаем администраторов из файла {path_to_admin_file}')
    try:
        if path_to_admin_file:
            with open(path_to_admin_file) as json_file:
                json_data = json.load(json_file)
            for admin in json_data['admins']:
                insert_admin(**admin)
            sqlite_logger.info('Администраторы успешно загружены.')
            return
        sqlite_logger.info('Не указан файл путь к файлу с администраторами')
    except Exception:
        sqlite_logger.error(
            f'Произошла ошибка при загрузке администраторов из {path_to_admin_file}', exc_info=True)


def chengelog_insert(tg_id: str, change_type: str):
    try:
        with SQLite() as cursor:
            sqlite_logger.info("Записываем внесенные изменения в CHANGELOG")
            user_name = return_fio(tg_id)
            cursor.execute(
                f"""INSERT INTO CHANGELOG(CHANGER_FIO, CHANGE_TYPE) VALUES('{user_name}','{change_type}')""")
            sqlite_logger.info(
                f"Изменения типа {change_type} от {tg_id} успешно внесены")
    except Exception:
        sqlite_logger.error(
            f'Ошибка при внесении изменений {tg_id} {change_type}')


def return_fio(tg_id: str) -> str:
    try:
        with SQLite() as cursor:
            sqlite_logger.info(f"Запрашиваем фио пользователя {tg_id}")
            user_name = cursor.execute(
                f"SELECT fio FROM ACCESS_TABLE WHERE tg_id='{tg_id}'").fetchone()
            sqlite_logger.info(
                f"Пользователь {tg_id} определен {user_name[0]}")
            return user_name[0]
    except Exception:
        sqlite_logger.error(
            f"Ошибка при определении фио пользователя {tg_id}", exc_info=True)


def create_tables() -> None:
    """Создаем таблицы в пустой базе
    """
    try:
        with SQLite() as cursor:
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS ACCESS_TABLE (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
tg_id INT NOT NULL UNIQUE, fio TEXT NOT NULL)""")
            cursor.execute(
                """CREATE TABLE IF NOT EXISTS CHANGELOG (id INTEGER PRIMARY KEY AUTOINCREMENT NOT NULL,
TIMESTAMP DATETIME DEFAULT CURRENT_TIMESTAMP,
CHANGER_FIO TEXT NOT NULL, CHANGE_TYPE TEXT NOT NULL)""")
            sqlite_logger.info("База данных успешно создана ")
    except Exception as exc:
        print(exc)
        sqlite_logger.error(
            "Произошла ошибка при создании таблиц", exc_info=True)


def show_all_admin_db() -> dict:
    try:
        with SQLite() as cursor:
            sqlite_logger.info("Запрошены все доступные администраторы")
            query_result = cursor.execute("Select tg_id,fio from ACCESS_TABLE")
            res = {num: f"{tg_id}:{fio}" for num,
                   (tg_id, fio) in enumerate(dict(query_result).items())}
            sqlite_logger.info("Администраторы отданы из бд")
            return res
    except Exception:
        sqlite_logger.error(
            "Произошла ошибка при запросе администраторов", exc_info=True)
        return {}


def show_change_log() -> str:
    try:
        with SQLite() as cursor:
            sqlite_logger.info("Запрошена статистика изменений")
            query_result = cursor.execute(
                "SELECT TIMESTAMP,CHANGER_FIO,CHANGE_TYPE FROM CHANGELOG order by TIMESTAMP DESC").fetchall()
            result = ""
            for row in query_result:
                result += ",".join(elem for elem in row) + "\n"
            return result
    except Exception:
        sqlite_logger.error(
            "Произошла ошибка при запросе статистики изменений")
        raise


def delete_admin_user_db(admin_id, tg_id_for_delete) -> bool:
    try:
        with SQLite() as cursor:
            sqlite_logger.info(
                f"Запрошено удаление пользователя {tg_id_for_delete} от администратора {admin_id}")
            cursor.execute(
                f"DELETE FROM ACCESS_TABLE where tg_id = {tg_id_for_delete}")
            sqlite_logger.info(
                f"Пользователь {tg_id_for_delete} успешно удален")
            return True
    except Exception:
        sqlite_logger.error(
            "Произошла ошибка при удалении администраторов", exc_info=True)
        return False


def check_admin_permissions(tg_id_for_check) -> bool:
    try:
        with SQLite() as cursor:
            sqlite_logger.info(
                f"Проверка пользователя {tg_id_for_check} на наличие прав администратора")
            cursor.execute(
                f"select * from ACCESS_TABLE where tg_id = {tg_id_for_check}")
            if cursor.fetchall():
                return True
            else:
                sqlite_logger.info(
                    f"У пользователя {tg_id_for_check} не найдены права администратора")
                return False
    except Exception:
        sqlite_logger.error(
            f"При проверке прав доступа пользователя произошла ошибка {tg_id_for_check}", exc_info=True)
        return False
