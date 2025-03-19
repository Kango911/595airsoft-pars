import logging
import asyncio
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
import requests
from bs4 import BeautifulSoup
from key import TOKENN

# Ваши данные для Telegram-бота
TOKEN = TOKENN

# Настройка логирования
logging.basicConfig(level=logging.INFO)


def load_urls(filename):
    """Загрузка URL-адресов из файла."""
    with open(filename, 'r') as file:
        urls = [line.strip() for line in file if line.strip()]  # Чтение строк и удаление пустых
    return urls


# Загрузка URL-адресов из файлов
urls1 = load_urls('urls.txt')
urls2 = load_urls('urls2.txt')
urls3 = load_urls('urls3.txt')


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка команды /start"""
    keyboard = [
        [
            InlineKeyboardButton("Получить данные из strikeplanet", callback_data='get_data1'),
            InlineKeyboardButton("Получить данные из apostol", callback_data='get_data2'),
            InlineKeyboardButton("Получить данные из airsoft-rus", callback_data='get_data3'),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await context.bot.send_message(chat_id=update.effective_chat.id, text='Выберите источник данных:',
                                   reply_markup=reply_markup)


async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка нажатия кнопки"""
    query = update.callback_query
    await query.answer()

    messages = []
    if query.data == 'get_data1':
        urls = urls1
        parser = "strikeplanet"
    elif query.data == 'get_data2':
        urls = urls2
        parser = "apostol"
    elif query.data == 'get_data3':
        urls = urls3
        parser = "airsoft-rus"

    for url in urls:
        product_data = get_product_data_generic(url, parser)

        if product_data:
            message = f"Название: {product_data['name']}\nЦена: {product_data['price']}\nВ наличии: {product_data['availability']}"
            messages.append(message)
        else:
            messages.append(f"Не удалось получить данные о товаре с URL: {url}")

    # Отправляем все сообщения
    await context.bot.send_message(chat_id=update.effective_chat.id, text="\n\n".join(messages))


def get_product_data_generic(url, parser):
    """Извлекает данные с помощью указанного парсера."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 403:
            logging.error(f"403 Forbidden: Доступ запрещён для URL: {url}")
            return None

        response.raise_for_status()  # Проверяем на наличие ошибок при запросе
        soup = BeautifulSoup(response.content, 'html.parser')

        if parser == "strikeplanet":
            return extract_strikeplanet_data(soup)
        elif parser == "apostol":
            return extract_apostol_data(soup)
        elif parser == "airsoft-rus":
            return extract_airsoft_rus_data(soup)

        return None

    except requests.exceptions.RequestException as e:
        logging.error(f"Ошибка при запросе страницы: {e}")
        return None
    except AttributeError as e:
        logging.error(f"Ошибка при анализе HTML: {e}")
        return None


def extract_strikeplanet_data(soup):
    """Извлекает данные из страницы strikeplanet."""
    name_element = soup.find('div', class_='title-block__title')
    name = name_element.find('h1').text.strip() if name_element and name_element.find('h1') else "Название не указано"

    price_element = soup.find('div', class_='price')
    price = price_element.text.strip() if price_element else "Цена не указана"

    availability = "Не указано"
    store_item_e = soup.find('div', class_='product-inner__list')
    if store_item_e:
        store_item_el = store_item_e.find('div', class_='product-inner__item')
        if store_item_el:
            text_element = store_item_el.find('div', class_='product-inner__text')
            if text_element:
                availability = text_element.text.strip() if text_element else "Не в наличии"

    return {'name': name, 'price': price, 'availability': availability}


def extract_apostol_data(soup):
    """Извлекает данные из страницы apostol."""
    name_element = soup.find('div', class_='t-store__prod-popup__title-wrapper')
    name = name_element.find('h1',
                             class_='js-store-prod-name js-product-name t-store__prod-popup__name t-name t-name_xl').text.strip() if name_element and name_element.find(
        'h1') else "Название не указано"

    price_element = soup.find('div', class_='js-product-price js-store-prod-price-val t-store__prod-popup__price-value')
    price = price_element.text.strip() if price_element else "Цена не указана"

    availability = "Не указано"
    store_item_e = soup.find('div', class_='product-inner__list')
    if store_item_e:
        store_item_el = store_item_e.find('div', class_='product-inner__item')
        if store_item_el:
            text_element = store_item_el.find('div', class_='product-inner__text')
            if text_element:
                availability_text = text_element.text.strip().lower()
                availability = "В наличии" if "есть" in availability_text else "Нет в наличии" if "нет" in availability_text else "Статус наличия не определен"

    return {'name': name, 'price': price, 'availability': availability}


def extract_airsoft_rus_data(soup):
    """Извлекает данные из страницы airsoft-rus."""
    name_element = soup.find('div', id='content')
    name = name_element.find('h1').text.strip() if name_element and name_element.find('h1') else "Название не указано"

    price_element = soup.find('mark', class_='price')
    price = price_element.text.strip() if price_element else "Цена не указана"

    store_item_e = soup.find('p', class_='in_stock')
    availability = store_item_e.text.strip() if store_item_e else "Не в наличии"

    return {'name': name, 'price': price, 'availability': availability}


def main():
    """Главная функция для запуска бота."""
    application = ApplicationBuilder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(button_click))

    asyncio.run(application.run_polling())  # Запускаем цикл событий


if __name__ == '__main__':
    main()  # Запускаем основную функцию


