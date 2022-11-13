import os
import time
from dotenv import load_dotenv
import telegram
import requests
import logging
import sys
from logging import StreamHandler
from exceptions import APIStatusNotOk, TokenOrDateError, EnviromentVarError
from http import HTTPStatus

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    filename='bot_logging.log',
                    format='%(asctime)s, %(levelname)s, %(message)s',
                    filemode='w')


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 10
ENDPOINT = 'https://practicum.yandex.ru/api/user_api/homework_statuses/'
HEADERS = {'Authorization': f'OAuth {PRACTICUM_TOKEN}'}


HOMEWORK_STATUSES = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

API_STATUS_NOT_OK = 'API enpoint status not OK.'
TOKEN_OR_DATE_ERROR = 'Token or date problem.'
HOMEWORK_STATUS_ERROR = 'Unexpected homework status.'
ENVIROMENT_VARIABLE_ERROR = 'Enviroment variable missing.'


def send_message(bot, message):
    """Отправка ботом сообщения в Телеграмм."""
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
    except Exception as error:
        logging.error(f'Message not sent {error}.')
    logging.info(f'Message {message} succesfuly sent.')


def get_api_answer(current_timestamp):
    """Получение ответа от эндпоинта API."""
    timestamp = current_timestamp or int(time.time())
    params = {'from_date': timestamp}
    url = ENDPOINT
    try:
        response = requests.get(url, headers=HEADERS, params=params)
        response_status = response.status_code
        if response_status != HTTPStatus.OK:
            logging.error(API_STATUS_NOT_OK)
            raise APIStatusNotOk(API_STATUS_NOT_OK)
    except requests.RequestException as error:
        logging.error(f'Endpoint {ENDPOINT} trouble, {error}.')
    return response.json()


def check_response(response):
    """Проверка содержимого ответа API."""
    if 'code' not in response:
        if type(response['homeworks']) == list:
            try:
                response = response['homeworks']
                return response
            except Exception as error:
                logging.error(f'Incorrect key in API answer {error}.')
        raise TypeError
    logging.critical(TOKEN_OR_DATE_ERROR)
    raise TokenOrDateError(TOKEN_OR_DATE_ERROR)


def parse_status(homework):
    """Проверка статуса сданной работы."""
    homework_name = homework['homework_name']
    homework_status = homework['status']
    if homework_status not in HOMEWORK_STATUSES:
        logging.error(HOMEWORK_STATUS_ERROR)
        raise KeyError(HOMEWORK_STATUS_ERROR)
    verdict = HOMEWORK_STATUSES[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных аутентификации."""
    for key in (TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN):
        if key is None or not key:
            logging.critical(ENVIROMENT_VARIABLE_ERROR)
            return False
    return True


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        raise EnviromentVarError(ENVIROMENT_VARIABLE_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = 1666535727
    previous_error = ''
    while True:
        try:
            response = get_api_answer(current_timestamp)
            homework = check_response(response)
            message = parse_status(homework[0])
            send_message(bot, message)
            current_timestamp = response.get('current_time')
            time.sleep(RETRY_TIME)
        except IndexError:
            logging.debug('No status changes.')
            time.sleep(RETRY_TIME)
        except Exception as error:
            message = f'Сбой в работе программы: {error}.'
            logging.error(error)
            if message != previous_error:
                send_message(bot, message)
            previous_error = message
            time.sleep(RETRY_TIME)


if __name__ == '__main__':
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    handler = StreamHandler(sys.stdout)
    logger.addHandler(handler)
    main()
