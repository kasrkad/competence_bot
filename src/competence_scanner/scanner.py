from jira_requests.issue.issue_request import ISSUE_REQUEST
import requests
from logger_config.logger import create_logger

scanner_logger = create_logger(__name__)

def get_issues_data(jira_token:str, jira_host:str,
                    startAt:int = 0,        
                    jql:str="'Competences Checklist' is not null AND statusCategory = Done AND resolutiondate > startOfMonth() ORDER BY updated DESC"
                    ) -> list:
    """Забираем все тикеты зарезовленные тикеты c начала месяца
    или по указанным границам даты
    Args:
        startAt (int, optional): порядковый номер, с которого начать . Defaults to 0.

    Returns:
        list: список тикетов по запросу
    """
    issues_result = []
    start_at = startAt
    headers = {"Authorization": "Bearer {token}".format(
            token=jira_token), "Accept": "application/json"}
    
    query = {
    'jql': jql,
    'maxResults': 1000,
    'startAt':startAt, 
    'fields':'assignee,customfield_15950'
    }
    try:
        scanner_logger.info(f"Запрашиваем талоны с параметром startAt={startAt}")
        with requests.Session() as request:
            response = request.get(ISSUE_REQUEST.format(
                    jira_host=jira_host), headers=headers,params=query)
            if not response.ok:
                raise (ValueError(f'Проверьте параметры запроса для поиска ответ от = {response.text}'))

            if (len(response.json()["issues"])) == 1000:
                issues_result += get_issues_data(startAt=start_at+1000)
            
            issues_result += response.json()["issues"]
    except Exception:
        scanner_logger.error(f"Произошла ошибка при запросе талонов", exc_info=True)
        raise

    return issues_result 

def users_with_competences(competence_codes:dict, issues:dict) -> dict:
    """Выдергиваем из списка талонов пользователей
    и проставленные компетенции

    Returns:
        dict: ключ пользователи, значение список их компетенций
    """
    scanner_logger.info("Начинаем формировать компетенции пользователей")
    assignee = {}
    for issue in issues:
        try:
            assignee_name = issue["fields"]["assignee"]["displayName"]
            assignee_email = issue["fields"]["assignee"]["emailAddress"]
            issue_key = issue["key"]
            field = issue["fields"]["customfield_15950"]
        except TypeError:
            continue
        except KeyError:
            scanner_logger.error(f"В заявке {issue_key} не найдено поле с компетенциями customfield_15950, пропускаем")
            continue

        if assignee_email and (assignee_email not in assignee):
            assignee[assignee_email] = dict()
            assignee[assignee_email]["user_name"] = assignee_name
            assignee[assignee_email]["tasks"] = []
        user_task = []
        profiles_data = []
        jira_tasks = {}
        jira_tasks["profiles"] = []
        issue_competences = []
        header_code_old = None
        
        for competence in issue["fields"]["customfield_15950"]:

            if competence['isHeader']:
                if header_code_old is None:
                    header_code_old = competence_codes.get(competence['name'], None)
                if issue_competences and header_code_old is not None:
                    profiles_data.append({"profile_id":header_code_old,"competences":issue_competences})
                else:
                    scanner_logger.info(f"В талоне {issue_key} проблема с профилем, вероятно невозможно определить код профиля")
                issue_competences = []
                header_code_old = competence_codes.get(competence['name'], None)
                continue
            issue_competences.append({"id":competence_codes.get(competence["name"]),"checked":competence["checked"]})
        
        if issue_competences and header_code_old:
            profiles_data.append({"profile_id":header_code_old,"competences":issue_competences})
        if profiles_data:
            user_task.append({"jira_task":issue_key,"profiles": profiles_data})
        if user_task:
            assignee[assignee_email]["tasks"].append(*user_task)
        else:
            del assignee[assignee_email]
            scanner_logger.info(f"У пользователя {assignee_email} не найдены задачи с указанными компетенциями")
    return assignee