import json
from logger_config.logger import create_logger
import os.path

operator_logger = create_logger(__name__)


def load_1c_data_from_file(filename: str) -> dict:
    """Грузим данные с файла выгрузки из 1с

    Args:
        filename (str): имя файла

    Returns:
        dict: возвращает словарь выгруженный из файла
    """
    operator_logger.info(f'Загружаем данные из файла выгрузки 1с {filename}')
    try:
        if not os.path.exists(filename):
            raise FileNotFoundError(
                "Файл с выгрузкой компетенций из 1с не обнаружен")
        with open(filename, 'r', encoding='utf-8-sig') as json_file:
            data_1c = json.load(json_file)
    except Exception:
        operator_logger.error(f"Ошибка при загрузке файла {filename}",
                              exc_info=True)
        raise
    return data_1c


def jira_id_for_1c(data_1c: dict, data_jira: dict) -> dict:
    """Сопоставляем проекты с 1с с id проектов в jira

    Args:
        data_1c (dict): данные выгрузки из 1с
        data_jira (dict): данные с проектами из jira

    Returns:
        dict: _description_
    """
    result_pairs = {}
    for elem in data_1c:
        result_pairs[elem["name"]] = data_jira.get(elem["name"], None)
    return result_pairs


def get_competence_codes(data_1c: dict) -> dict:
    """Получаем 1сные коды компетенций

    Args:
        data_1c(dict): входные данные из файла 1с
    Returns:
        dict: словарь где ключ это название компетенции, а значение ее id
    """
    competence_codes = {}
    for project in data_1c:
        for profiles in project["profiles"]:
            for competence in profiles["competences"]:
                if competence["id"] not in competence_codes:
                    competence_codes[competence["name"]] = competence["id"]
    return competence_codes


def competence_converting(project_profiles: list) -> list:
    """Преобразовываем компетенции в строку для загрузки в jira

    Args:
        project_profiles(list): поле из 1c json с профилями компетенций на проекте
    Returns:
        list: список компетенций {имя_списка_компетенций:строка из json } 
        готовый к подстановке в 'itemsJson' запроса для загрузки в jira

    """
    project_competences = []
    for profile in project_profiles:
        template_name = f"{profile['functionalDirection']}|{profile['name']}"
        result_competences = [{"id": "-1", "name": template_name,
                               "isHeader": True, "mandatory": False}]
        for competence in profile["competences"]:
            if competence["name"]:
                competence["mandatory"] = False
                result_competences.append(competence)
        project_competences.append({"template_name": template_name,
                                    "competences": str(json.dumps(result_competences,
                                                                  ensure_ascii=False))})
    return project_competences


def data_from_1c_compare(data_1c: dict, jira_id: dict,
                         fieldConfigId: int = 17761, customFieldId: int = 15950) -> dict:
    """Сопоставляем данные проектов из 1c с корректными id взятыми из jira
    формируем словарь с ключом имя_проекта:имя_шаблона и значением json 
    готовым к загрузке в jira
    Args:
        data_1(dict): выгруженные данные из файла 1с
        jira_id(dict): данные взятый из jira с именами проектов и из id
    Returns:
        dict: словарь с конкатенацией имени проекта и шаблона, и значением готовым к загрузке json
    """
    data_for_compare = {}
    for project in data_1c:
        jira_project_id = jira_id.get(project["name"], None)
        if not jira_project_id:
            operator_logger.error(f"for {project['name']}\
                    id is {jira_project_id}, must be not None")
            return
        project_name = project["name"]
        project_competences = competence_converting(project["profiles"])
        for template_data in project_competences:
            base_json = {"fieldConfigId": fieldConfigId,
                         "items": None, "importable": True,
                         "customFiledId": customFieldId}
            base_json["project"] = jira_project_id
            base_json["name"] = template_data["template_name"]
            base_json["itemsJson"] = template_data["competences"]

            data_for_compare[f"{project_name}:{template_data['template_name']}"] = base_json
    return data_for_compare


def data_from_jira_compare(data_jira: dict) -> dict:
    """Формируем данные для сравнения уже загруженных шаблонов
    Args:
        data_jira(dict): данные со списком всех шаблонов чеклистов уже загруженных в jira
    Returns:
        dict:словарь с ключем конкатенации имени проекта и имени шаблона и значением id шаблона в jira"""
    data_for_compare = {}
    for templates in data_jira["templates"]:
        data_for_compare[f"{templates['projectName']}:{templates['name']}"] = templates["id"]
    return data_for_compare
