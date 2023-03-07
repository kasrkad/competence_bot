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
    result_competences = []
    scanner_logger.info("Начинаем формировать компетенции пользователей")
    assignee = {}
    for issue in issues:
        try:
            assignee_name = issue["fields"]["assignee"]["displayName"]
            assignee_email = issue["fields"]["assignee"]["emailAddress"]
        except TypeError:
            continue
        
        if assignee_name and (assignee_name not in assignee):
            assignee[assignee_name] = dict()
            assignee[assignee_name]["user_name"] = assignee_name
            assignee[assignee_name]["email"] = assignee_email
            assignee[assignee_name]["checked"] = []
            assignee[assignee_name]["unchecked"] = []  

        for competence in issue["fields"]["customfield_15950"]:
            if competence:
                competence_code = competence_codes.get(competence["name"],None)
                if competence["checked"]== True and competence_code is not None:
                    assignee[assignee_name]["checked"] += [competence_code]
                elif competence["checked"]== False and competence_code is not None:
                    assignee[assignee_name]["unchecked"] += [competence_code]
                else:
                    scanner_logger.warn(f"не найден код для {competence['name']}, пользователя {assignee_name} задача {issue['key']}")  
        result_competences = [value for key,value in assignee.items()]
    return result_competences