import os
import time
from dotenv import load_dotenv
import telegram
import requests
import logging
import sys
from logging import StreamHandler
from exceptions import APIStatusNotOk, TokenOrDateError
from http import HTTPStatus

load_dotenv()

logging.basicConfig(level=logging.DEBUG,
                    filename='bot_logging.log',
                    format='%(asctime)s, %(levelname)s, %(message)s',
                    filemode='w')


PRACTICUM_TOKEN = os.getenv('PRACTICUM_TOKEN')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')


RETRY_TIME = 600


HOMEWORK_VERDICTS = {
    'approved': 'Работа проверена: ревьюеру всё понравилось. Ура!',
    'reviewing': 'Работа взята на проверку ревьюером.',
    'rejected': 'Работа проверена: у ревьюера есть замечания.'
}

API_STATUS_NOT_OK = 'API enpoint status not OK.'
TOKEN_OR_DATE_ERROR = 'Token or date problem.'
HOMEWORK_STATUS_ERROR = 'Unexpected homework status.'
ENVIROMENT_VARIABLE_ERROR = 'Enviroment variable missing.'
UNEXPECTED_TYPE_IN_RESPONSE = 'unexpected type in response'
NO_HOMEWORKS_IN_RESPONSE = 'No homeworks in response'
NO_HOMEWORK_NAME_IN_HOMEWORK = 'No homework_name in homeworks'
NO_STATUS_IN_HOMEWORK = 'No status in homework'
UNEXPEXTED_VALYE_TYPE_IN_HOMEWORKS = 'unexpected value type in homeworks'


def send_message(bot, message):
    """Отправка ботом сообщения в Телеграмм."""
    logging.info(f'Try send message {message}.')
    try:
        bot.send_message(TELEGRAM_CHAT_ID, message)
        logging.info('Message succesfuly sent.')
    except telegram.error.TelegramError:
        logging.error(f'Message not sent {message}.')


def get_api_answer(current_timestamp):
    """Получение ответа от эндпоинта API."""
    request_params = {
        'url': 'https://practicum.yandex.ru/api/user_api/homework_statuses/',
        'headers': {'Authorization': f'OAuth {PRACTICUM_TOKEN}'},
        'params': {'from_date': current_timestamp},
    }
    try:
        response = requests.get(**request_params)
        response_status = response.status_code
        if response_status != HTTPStatus.OK:
            logging.error(API_STATUS_NOT_OK)
            raise APIStatusNotOk(API_STATUS_NOT_OK)
    except requests.RequestException as error:
        logging.error(f'Endpoint trouble, {error}.')
    return response.json()


def check_response(response):
    """Проверка содержимого ответа API."""
    if 'code' in response:
        logging.critical(TOKEN_OR_DATE_ERROR)
        raise TokenOrDateError(TOKEN_OR_DATE_ERROR)
    if not isinstance(response, dict):
        logging.error(UNEXPECTED_TYPE_IN_RESPONSE)
        raise TypeError(UNEXPECTED_TYPE_IN_RESPONSE)
    if 'homeworks' not in response:
        logging.error(NO_HOMEWORKS_IN_RESPONSE)
        raise KeyError(NO_HOMEWORKS_IN_RESPONSE)
    if not isinstance(response['homeworks'], list):
        logging.error(UNEXPEXTED_VALYE_TYPE_IN_HOMEWORKS)
        raise TypeError(UNEXPEXTED_VALYE_TYPE_IN_HOMEWORKS)
    response = response['homeworks']
    return response


def parse_status(homework):
    """Проверка статуса сданной работы."""
    if 'homework_name' not in homework:
        logging.error(NO_HOMEWORKS_IN_RESPONSE)
        raise KeyError(NO_HOMEWORKS_IN_RESPONSE)
    homework_name = homework['homework_name']
    if 'status' not in homework:
        logging.error(NO_STATUS_IN_HOMEWORK)
        raise KeyError(NO_STATUS_IN_HOMEWORK)
    homework_status = homework['status']
    if homework_status not in HOMEWORK_VERDICTS:
        logging.error(HOMEWORK_STATUS_ERROR)
        raise KeyError(HOMEWORK_STATUS_ERROR)
    verdict = HOMEWORK_VERDICTS[homework_status]
    return f'Изменился статус проверки работы "{homework_name}". {verdict}'


def check_tokens():
    """Проверка переменных аутентификации."""
    if all([TELEGRAM_CHAT_ID, TELEGRAM_TOKEN, PRACTICUM_TOKEN]):
        return True
    logging.critical(ENVIROMENT_VARIABLE_ERROR)
    return False


def main():
    """Основная логика работы бота."""
    if not check_tokens():
        sys.exit(ENVIROMENT_VARIABLE_ERROR)
    bot = telegram.Bot(token=TELEGRAM_TOKEN)
    current_timestamp = int(time.time())
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
